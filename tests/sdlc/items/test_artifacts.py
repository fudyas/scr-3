import hashlib
import json
import os
import stat
from abc import ABC
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest

from sdlc.datasources.git_command import GitCommandRunner
from sdlc.datasources.git_ledger_source import GitLedgerSource
from sdlc.models.artifact import ArtifactBinding, ArtifactBundle
from sdlc.models.errors import ItemClaimError, LedgerUnreachableError, SdlcError
from sdlc.models.git import PushOutcome
from sdlc.models.item import ItemKind
from sdlc.models.ledger import LedgerChange
from sdlc.repositories.ledger_repository import LedgerRepository
from sdlc.wiring import AppWiring


class ArtifactFixtureHelper(ABC):
    """Builds synthetic files and real temporary-ledger publication fixtures."""

    @staticmethod
    def mint(host: AppWiring) -> str:
        """Returns the identity of a newly minted artifact owner."""
        return host.item_usecases.mint(ItemKind.TASK, "ARTIFACT-TEST", "idea", "text", [], []).short_id

    @staticmethod
    def ledger(host: AppWiring) -> LedgerRepository:
        """Returns a second ledger connection to the fixture's real local remote."""
        return LedgerRepository(GitLedgerSource(GitCommandRunner(host.settings.main_root), "origin", "sdlc", 60), 5)

    @staticmethod
    def entry(host: AppWiring, item_id: str, relative: str, payload: bytes = b"input\n", mode: int = 0o644,
              managed_path: Optional[str] = None) -> Dict[str, str]:
        """Creates one explicit synthetic source and returns its manifest entry."""
        source = host.settings.worktrees_dir / item_id / "integration" / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(payload)
        source.chmod(mode)
        return {"source_path": str(source), "original_path": relative,
                "managed_path": managed_path or f"items/{item_id}/implementation/{Path(relative).name}"}

    @staticmethod
    def manifest(host: AppWiring, entries: List[Dict[str, str]], purpose: str = "INPUT", stage: str = "implementation",
                 source_tree: Optional[str] = None, input_digest: Optional[str] = None) -> Path:
        """Writes an explicit publication manifest outside the source payload roots."""
        document: Dict[str, Any] = {"schema_version": 1, "purpose": purpose, "stage": stage, "entries": entries}
        if source_tree is not None:
            document["source_tree"] = source_tree
        if input_digest is not None:
            document["input_digest"] = input_digest
        path = host.settings.main_root / "manifest.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    @staticmethod
    def publish_input(host: AppWiring, item_id: str) -> ArtifactBinding:
        """Publishes an explicit input file and returns its binding."""
        entry = ArtifactFixtureHelper.entry(host, item_id, "evidence/input.md")
        return host.artifact_usecases.publish(item_id, ArtifactFixtureHelper.manifest(host, [entry]), "implementation")

    @staticmethod
    def result(host: AppWiring, item_id: str, binding: ArtifactBinding, suffix: str = "qa") -> ArtifactBinding:
        """Publishes one QA result that names the exact source and input digest."""
        entry = ArtifactFixtureHelper.entry(host, item_id, f"evidence/{suffix}.md", suffix.encode("utf-8"),
                                            managed_path=f"items/{item_id}/qa/{suffix}.md")
        manifest = ArtifactFixtureHelper.manifest(host, [entry], "RESULT", "qa", binding.source_tree, binding.digest)
        return host.artifact_usecases.publish(item_id, manifest, "qa")


class TestArtifactPersistence:
    """Covers remote durability, multi-host recovery, fidelity, and idempotence."""

    def test_cross_host_binary_hidden_and_executable_round_trip(self, make_host: Callable[[str], AppWiring]) -> None:
        """Restores exact bytes and permissions on another host without original sources."""
        alpha = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(alpha)
        entries = [ArtifactFixtureHelper.entry(alpha, item_id, "contracts/schema.json", b'{"x":"\\r\\n"}\r\n'),
                   ArtifactFixtureHelper.entry(alpha, item_id, "evidence/retired/.codex/.hidden", b"\xff\x00\x80\r\n", 0o751,
                                                "legacy/scr-pre-item/evidence/retired/.codex/.hidden")]
        manifest = ArtifactFixtureHelper.manifest(alpha, entries, stage="qa")
        published = alpha.artifact_usecases.publish(item_id, manifest, "qa")
        ledger = ArtifactFixtureHelper.ledger(alpha)
        durable = ledger.snapshot().read_text(published.ledger_path)
        assert durable is not None
        assert hashlib.sha256(durable.encode("utf-8")).hexdigest() == published.digest
        assert json.dumps(json.loads(durable), ensure_ascii=False, sort_keys=True, separators=(",", ":")) == durable
        first_tip = ledger.snapshot().commit
        assert alpha.artifact_usecases.publish(item_id, manifest, "qa") == published
        assert ledger.snapshot().commit == first_tip
        assert len(alpha.artifact_usecases.list(item_id)) == 1
        assert published.purpose == "INPUT" and published.stage == "qa"
        originals = {entry["managed_path"]: Path(entry["source_path"]).read_bytes() for entry in entries}
        for entry in entries:
            Path(entry["source_path"]).unlink()
        beta = make_host("beta")
        restored = beta.artifact_usecases.restore(published.digest)
        assert restored.digest == published.digest and restored.snapshot_path != published.snapshot_path
        for entry in entries:
            managed = beta.settings.artifacts_dir / entry["managed_path"]
            snapshot = restored.snapshot_path / entry["managed_path"]
            expected_mode = 0o751 if entry["managed_path"].endswith(".hidden") else 0o644
            assert managed.read_bytes() == snapshot.read_bytes() == originals[entry["managed_path"]]
            assert stat.S_IMODE(managed.stat().st_mode) == stat.S_IMODE(snapshot.stat().st_mode) == expected_mode
            assert managed.stat().st_ino != snapshot.stat().st_ino
        assert beta.artifact_usecases.restore(published.digest) == restored
        assert beta.artifact_usecases.verify(published.digest) == restored
        assert beta.artifact_usecases.list(item_id) == [restored]

    def test_remote_failure_preserves_sources_without_materialization(
            self, make_host: Callable[[str], AppWiring], monkeypatch: pytest.MonkeyPatch) -> None:
        """Fails before managed writes when the remote rejects durable publication."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        entry = ArtifactFixtureHelper.entry(host, item_id, "evidence/payload.bin", b"\xff\x00data", 0o700)
        manifest = ArtifactFixtureHelper.manifest(host, [entry])

        def fail_push(source: GitLedgerSource, commit: str) -> PushOutcome:
            """Raises the actual persistence failure at the push boundary."""
            raise LedgerUnreachableError("synthetic remote unavailable")

        monkeypatch.setattr(GitLedgerSource, "push", fail_push)
        with pytest.raises(LedgerUnreachableError, match="synthetic remote unavailable"):
            host.artifact_usecases.publish(item_id, manifest, "implementation")
        assert Path(entry["source_path"]).read_bytes() == b"\xff\x00data"
        assert stat.S_IMODE(Path(entry["source_path"]).stat().st_mode) == 0o700
        assert not host.settings.artifacts_dir.exists()

    def test_compare_and_swap_retains_other_host_history(
            self, make_host: Callable[[str], AppWiring], monkeypatch: pytest.MonkeyPatch) -> None:
        """Retries a real losing push and preserves both hosts' immutable bundles."""
        alpha = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(alpha)
        beta = make_host("beta")
        alpha_entry = ArtifactFixtureHelper.entry(alpha, item_id, "evidence/alpha.md", b"alpha")
        beta_entry = ArtifactFixtureHelper.entry(beta, item_id, "evidence/beta.md", b"beta")
        alpha_manifest = ArtifactFixtureHelper.manifest(alpha, [alpha_entry])
        beta_manifest = ArtifactFixtureHelper.manifest(beta, [beta_entry])
        original_push = GitLedgerSource.push
        raced: List[str] = []

        def race_push(source: GitLedgerSource, commit: str) -> PushOutcome:
            """Lets another host publish between the initial read and first push."""
            if source._runner.repo_dir == alpha.settings.main_root and not raced:
                raced.append(commit)
                beta.artifact_usecases.publish(item_id, beta_manifest, "implementation")
            return original_push(source, commit)

        monkeypatch.setattr(GitLedgerSource, "push", race_push)
        published = alpha.artifact_usecases.publish(item_id, alpha_manifest, "implementation")
        retained = alpha.artifact_usecases.list(item_id)
        assert len(raced) == 1 and len(retained) == 2 and retained[-1] == published
        assert beta.artifact_usecases.list(item_id)[-1].digest == published.digest

    def test_retries_local_materialization_after_remote_success(
            self, make_host: Callable[[str], AppWiring], monkeypatch: pytest.MonkeyPatch) -> None:
        """Recovers a durable publication after the host interrupts local copying."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        entry = ArtifactFixtureHelper.entry(host, item_id, "evidence/input.md")
        manifest = ArtifactFixtureHelper.manifest(host, [entry])
        original = host.artifact_usecases._source.materialize

        def interrupt_copy(bundle: ArtifactBundle) -> ArtifactBinding:
            """Simulates interruption after the remote transaction succeeds."""
            raise SdlcError("synthetic interrupted materialization")

        monkeypatch.setattr(host.artifact_usecases._source, "materialize", interrupt_copy)
        with pytest.raises(SdlcError, match="interrupted materialization"):
            host.artifact_usecases.publish(item_id, manifest, "implementation")
        retained = host.artifact_usecases.list(item_id)
        assert len(retained) == 1 and Path(entry["source_path"]).exists()
        monkeypatch.setattr(host.artifact_usecases._source, "materialize", original)
        assert host.artifact_usecases.restore(retained[0].digest) == retained[0]
        assert host.artifact_usecases.publish(item_id, manifest, "implementation") == retained[0]

    def test_fresh_cas_retry_refuses_another_hosts_new_claim(
            self, make_host: Callable[[str], AppWiring], monkeypatch: pytest.MonkeyPatch) -> None:
        """Rechecks ownership after another host wins a real ledger race."""
        alpha = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(alpha)
        beta = make_host("beta")
        entry = ArtifactFixtureHelper.entry(alpha, item_id, "evidence/input.md")
        manifest = ArtifactFixtureHelper.manifest(alpha, [entry])
        original_push = GitLedgerSource.push
        raced: List[str] = []

        def claim_before_push(source: GitLedgerSource, commit: str) -> PushOutcome:
            """Claims the temporary item remotely before the first publication push."""
            if source._runner.repo_dir == alpha.settings.main_root and not raced:
                raced.append(commit)
                beta.items.modify(item_id, lambda item, others: item.model_copy(update={"host": "beta"}), "fixture claim")
            return original_push(source, commit)

        monkeypatch.setattr(GitLedgerSource, "push", claim_before_push)
        with pytest.raises(ItemClaimError, match="claimed by host beta"):
            alpha.artifact_usecases.publish(item_id, manifest, "implementation")
        assert len(raced) == 1
        assert not alpha.settings.artifacts_dir.exists()
        assert Path(entry["source_path"]).read_bytes() == b"input\n"

    def test_durable_bundle_corruption_fails_before_local_restore(self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses corrupted ledger bytes even when the local snapshot remains intact."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        binding = ArtifactFixtureHelper.publish_input(host, item_id)
        ledger = ArtifactFixtureHelper.ledger(host)
        payload = ledger.snapshot().read_text(binding.ledger_path)
        assert payload is not None
        document = json.loads(payload)
        document["entries"][0]["payload_base64"] = "Y29ycnVwdGVk"
        ledger.transact(lambda view: LedgerChange(changes={binding.ledger_path: json.dumps(document)},
                                                  message="synthetic durable corruption"))
        with pytest.raises(SdlcError, match="durable artifact digest mismatch"):
            host.artifact_usecases.restore(binding.digest)
        assert (binding.snapshot_path / f"items/{item_id}/implementation/input.md").read_bytes() == b"input\n"


class TestArtifactBoundaries:
    """Covers explicit allowlists, no-follow file access, and conflict refusal."""

    @pytest.mark.parametrize("destination", ["../outside", "/tmp/outside", "items/ITM-0001/qa/../outside",
                                             "image/clone", "recovery/journal", "quarantine/marker", "var/source",
                                             ".lets/locks/x", "items/ITM-0002/implementation/x", "legacy//x",
                                             "legacy/./x", "legacy/a/../../x"])
    def test_rejects_unsafe_destinations_without_managed_writes(
            self, make_host: Callable[[str], AppWiring], destination: str) -> None:
        """Rejects traversal, protected roots, and another item's managed namespace."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        entry = ArtifactFixtureHelper.entry(host, item_id, "evidence/input.md", managed_path=destination)
        with pytest.raises(SdlcError):
            host.artifact_usecases.publish(item_id, ArtifactFixtureHelper.manifest(host, [entry]), "implementation")
        assert not host.settings.artifacts_dir.exists()
        assert Path(entry["source_path"]).read_bytes() == b"input\n"

    @pytest.mark.parametrize("relative", ["var/image", ".lets/locks/x", ".codex/sdlc/quarantine", "README.md"])
    def test_rejects_sources_outside_allowlist(
            self, make_host: Callable[[str], AppWiring], relative: str) -> None:
        """Rejects explicit product and protected-runtime sources without reading them."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        entry = ArtifactFixtureHelper.entry(host, item_id, relative)
        with pytest.raises(SdlcError, match="outside import scope"):
            host.artifact_usecases.publish(item_id, ArtifactFixtureHelper.manifest(host, [entry]), "implementation")
        assert not host.settings.artifacts_dir.exists()

    def test_invalid_source_path_reports_expected_sdlc_error(self, make_host: Callable[[str], AppWiring]) -> None:
        """Rejects embedded NUL bytes before a filesystem call can escape error handling."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        entry = ArtifactFixtureHelper.entry(host, item_id, "evidence/input.md")
        entry["source_path"] += "\x00"
        with pytest.raises(SdlcError, match="invalid or duplicate artifact source"):
            host.artifact_usecases.publish(item_id, ArtifactFixtureHelper.manifest(host, [entry]), "implementation")
        assert not host.settings.artifacts_dir.exists()

    @pytest.mark.parametrize("kind", ["source-link", "source-ancestor", "destination-link", "destination-ancestor", "fifo"])
    def test_rejects_links_and_special_files_without_outside_writes(
            self, make_host: Callable[[str], AppWiring], tmp_path: Path, kind: str) -> None:
        """Refuses source and destination links, ancestor links, and FIFO payloads."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        entry = ArtifactFixtureHelper.entry(host, item_id, "evidence/nested/input.md")
        outside = tmp_path / "outside"
        outside.mkdir()
        protected = outside / "input.md"
        protected.write_bytes(b"outside unchanged")
        source = Path(entry["source_path"])
        if kind in ("source-link", "fifo"):
            source.unlink()
            if kind == "fifo":
                os.mkfifo(source)
            else:
                source.symlink_to(protected)
        elif kind == "source-ancestor":
            source.unlink()
            source.parent.rmdir()
            source.parent.symlink_to(outside, target_is_directory=True)
        elif kind == "destination-link":
            destination = host.settings.artifacts_dir / entry["managed_path"]
            destination.parent.mkdir(parents=True)
            destination.symlink_to(protected)
        else:
            host.settings.artifacts_dir.parent.mkdir(parents=True)
            host.settings.artifacts_dir.symlink_to(outside, target_is_directory=True)
        with pytest.raises(SdlcError):
            host.artifact_usecases.publish(item_id, ArtifactFixtureHelper.manifest(host, [entry]), "implementation")
        assert protected.read_bytes() == b"outside unchanged"
        assert sorted(path.name for path in outside.iterdir()) == ["input.md"]

    def test_duplicate_and_ancestor_destinations_fail_before_publication(self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses aliases and file/directory collisions before durable writes."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        first = ArtifactFixtureHelper.entry(host, item_id, "evidence/first.md")
        second = ArtifactFixtureHelper.entry(host, item_id, "evidence/second.md")
        for destination in (first["managed_path"], f'{first["managed_path"]}/child'):
            second["managed_path"] = destination
            with pytest.raises(SdlcError, match="duplicate|ancestor"):
                host.artifact_usecases.publish(item_id, ArtifactFixtureHelper.manifest(host, [first, second]), "implementation")
        assert host.artifact_usecases.list(item_id) == []

    def test_restore_preflight_preserves_conflicts_and_missing_files(self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses the entire restore before filling another missing destination."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        entries = [ArtifactFixtureHelper.entry(host, item_id, f"evidence/{name}.md") for name in ("a", "z")]
        binding = host.artifact_usecases.publish(item_id, ArtifactFixtureHelper.manifest(host, entries), "implementation")
        missing = host.settings.artifacts_dir / entries[0]["managed_path"]
        conflict = host.settings.artifacts_dir / entries[1]["managed_path"]
        missing.unlink()
        conflict.write_bytes(b"manual edit")
        with pytest.raises(SdlcError, match="restore conflict"):
            host.artifact_usecases.restore(binding.digest)
        assert not missing.exists() and conflict.read_bytes() == b"manual edit"


class TestArtifactReviewBindings:
    """Covers complete input selections, ignored-file mutations, and separate QA results."""

    def test_artifact_free_unminted_item_retains_source_only_compatibility(self, make_host: Callable[[str], AppWiring]) -> None:
        """Proves absence of durable artifacts before accepting a source-only context."""
        host = make_host("alpha")
        assert host.artifact_usecases.capture_review("ITM-0001", "tree") is None
        host.artifact_usecases.verify_review("ITM-0001", "tree", None)

    def test_missing_snapshot_provides_restore_guidance(self, make_host: Callable[[str], AppWiring]) -> None:
        """Explains durable recovery when the independent local snapshot is absent."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        binding = ArtifactFixtureHelper.publish_input(host, item_id)
        payload = binding.snapshot_path / f"items/{item_id}/implementation/input.md"
        payload.unlink()
        for directory in (payload.parent, payload.parent.parent, payload.parent.parent.parent, binding.snapshot_path):
            directory.rmdir()
        with pytest.raises(SdlcError, match=f"artifacts restore --bundle {binding.digest}"):
            host.artifact_usecases.verify(binding.digest)
        assert host.artifact_usecases.restore(binding.digest) == binding

    def test_missing_index_cannot_downgrade_durable_item(self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses source-only review when retained bundles lost their index."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        ArtifactFixtureHelper.publish_input(host, item_id)
        ArtifactFixtureHelper.ledger(host).transact(lambda view: LedgerChange(
            changes={f"artifacts/items/{item_id}/index.json": None}, message="synthetic missing index"))
        for action in (lambda: host.artifact_usecases.capture_review(item_id, "tree"),
                       lambda: host.artifact_usecases.verify_review(item_id, "tree", None),
                       lambda: host.artifact_usecases.list(item_id)):
            with pytest.raises(SdlcError, match="missing artifact index"):
                action()

    @pytest.mark.parametrize("mutation", ["live-bytes", "live-mode", "live-missing", "snapshot-bytes", "snapshot-mode",
                                         "snapshot-missing", "snapshot-extra", "binding-tree", "binding-path", "missing-binding"])
    def test_review_rejects_every_changed_input_component(
            self, make_host: Callable[[str], AppWiring], mutation: str) -> None:
        """Rejects ignored-file and immutable-copy changes despite a constant source tree."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        ArtifactFixtureHelper.publish_input(host, item_id)
        binding = host.artifact_usecases.capture_review(item_id, "tree")
        assert binding is not None
        host.artifact_usecases.verify_review(item_id, "tree", binding)
        relative = f"items/{item_id}/implementation/input.md"
        target = (host.settings.artifacts_dir if mutation.startswith("live") else binding.snapshot_path) / relative
        if mutation.endswith("bytes"):
            target.write_bytes(b"mutated ignored bytes")
        elif mutation.endswith("mode"):
            target.chmod(0o700)
        elif mutation.endswith("missing"):
            target.unlink()
        elif mutation == "snapshot-extra":
            (binding.snapshot_path / "extra").write_text("unexpected")
        elif mutation == "binding-tree":
            binding = binding.model_copy(update={"source_tree": "other-tree"})
        elif mutation == "binding-path":
            binding = binding.model_copy(update={"snapshot_path": host.settings.main_root})
        else:
            binding = None
        with pytest.raises(SdlcError):
            host.artifact_usecases.verify_review(item_id, "tree", binding)

    def test_capture_updates_whole_selection_and_retains_previous_input(self, make_host: Callable[[str], AppWiring]) -> None:
        """Recaptures selected paths only and invalidates the superseded binding."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        first = ArtifactFixtureHelper.publish_input(host, item_id)
        selected = host.settings.artifacts_dir / f"items/{item_id}/implementation/input.md"
        selected.write_bytes(b"new content")
        unselected = selected.parent / "unselected.md"
        unselected.write_bytes(b"never selected")
        current = host.artifact_usecases.capture_review(item_id, "tree")
        assert current is not None and current.digest != first.digest
        assert len(host.artifact_usecases.list(item_id)) == 2
        assert not (current.snapshot_path / f"items/{item_id}/implementation/unselected.md").exists()
        assert (first.snapshot_path / f"items/{item_id}/implementation/input.md").read_bytes() == b"input\n"
        host.artifact_usecases.verify_review(item_id, "tree", current)
        with pytest.raises(SdlcError, match="selection changed"):
            host.artifact_usecases.verify_review(item_id, "tree", first)

    def test_result_selection_requires_exact_pair_and_verified_latest_copy(self, make_host: Callable[[str], AppWiring]) -> None:
        """Keeps QA results separate from inputs and refuses changed result snapshots."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        ArtifactFixtureHelper.publish_input(host, item_id)
        binding = host.artifact_usecases.capture_review(item_id, "tree")
        assert binding is not None
        first = ArtifactFixtureHelper.result(host, item_id, binding, "first")
        latest = ArtifactFixtureHelper.result(host, item_id, binding, "latest")
        assert first.digest != latest.digest
        assert host.artifact_usecases.result_for(item_id, "tree", binding.digest) == latest
        host.artifact_usecases.verify_review(item_id, "tree", binding)
        for tree, digest in (("wrong-tree", binding.digest), ("tree", first.digest)):
            with pytest.raises(SdlcError):
                host.artifact_usecases.result_for(item_id, tree, digest)
        (latest.snapshot_path / f"items/{item_id}/qa/latest.md").write_bytes(b"changed result")
        with pytest.raises(SdlcError, match="snapshot changed"):
            host.artifact_usecases.result_for(item_id, "tree", binding.digest)

    def test_result_rejects_wrong_binding_and_input_overlap(self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses wrong source provenance and QA reports that recursively alter inputs."""
        host = make_host("alpha")
        item_id = ArtifactFixtureHelper.mint(host)
        ArtifactFixtureHelper.publish_input(host, item_id)
        binding = host.artifact_usecases.capture_review(item_id, "tree")
        assert binding is not None
        entry = ArtifactFixtureHelper.entry(host, item_id, "evidence/qa.md", managed_path=f"items/{item_id}/qa/report.md")
        manifest = ArtifactFixtureHelper.manifest(host, [entry], "RESULT", "qa", "wrong", binding.digest)
        with pytest.raises(SdlcError, match="source/input pair"):
            host.artifact_usecases.publish(item_id, manifest, "qa")
        entry["managed_path"] = f"items/{item_id}/implementation/input.md"
        manifest = ArtifactFixtureHelper.manifest(host, [entry], "RESULT", "qa", "tree", binding.digest)
        with pytest.raises(SdlcError, match="overlap selected INPUT"):
            host.artifact_usecases.publish(item_id, manifest, "qa")
        with pytest.raises(SdlcError, match="missing QA RESULT"):
            host.artifact_usecases.result_for(item_id, "tree", binding.digest)
