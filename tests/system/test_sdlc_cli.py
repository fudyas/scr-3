import json
import os
import shutil
import subprocess
from abc import ABC
from pathlib import Path
from typing import Any, Dict, List

import pytest


class SdlcCommandHelper(ABC):
    """Runs public LETS commands against isolated repositories and local remotes."""

    @staticmethod
    def create(tmp_path: Path) -> Path:
        """Creates a disposable checkout with managed interpreter access and no source images.

        Args:
            tmp_path: the directory that owns all disposable test state.

        Returns:
            The isolated project root.
        """
        project = Path(__file__).resolve().parents[2]
        checkout = tmp_path / "checkout"
        checkout.mkdir()
        subprocess.run(["git", "--no-pager", "init", "-q", "-b", "main", str(checkout)], check=True)
        for key, value in [("user.name", "SDLC Test"), ("user.email", "test@example.invalid")]:
            subprocess.run(["git", "--no-pager", "-C", str(checkout), "config", key, value], check=True)

        # Reuses read-only tooling while keeping runtime state outside the real repository
        for entry in ["tools", "bin", "lets"]:
            (checkout / entry).symlink_to(project / entry, target_is_directory=True)
        (checkout / "etc").mkdir()
        shutil.copy2(project / "etc/proj.conf", checkout / "etc/proj.conf")
        shutil.copy2(project / "etc/sdlc.conf", checkout / "etc/sdlc.conf")
        (checkout / ".lets").mkdir()
        (checkout / ".lets/pyenv").symlink_to(project / ".lets/pyenv", target_is_directory=True)
        (checkout / ".gitignore").write_text(".lets\n.codex/\n", encoding="utf-8")
        (checkout / "README.md").write_text("Disposable SDLC test\n", encoding="utf-8")
        subprocess.run(["git", "--no-pager", "-C", str(checkout), "add", "README.md", ".gitignore"], check=True)
        subprocess.run(["git", "--no-pager", "-C", str(checkout), "commit", "-qm", "Seed"], check=True)
        remote = tmp_path / "remote.git"
        subprocess.run(["git", "--no-pager", "clone", "--bare", "-q", str(checkout), str(remote)], check=True)
        subprocess.run(["git", "--no-pager", "-C", str(checkout), "remote", "add", "origin", str(remote)], check=True)
        return checkout

    @staticmethod
    def run(checkout: Path, arguments: List[str]) -> subprocess.CompletedProcess:
        """Returns the public command result with all ledger writes confined to its local remote."""
        environment = {**os.environ, "SDLC_LEDGER_REMOTE": str(checkout.parent / "remote.git"), "SDLC_HOST": "test"}
        return subprocess.run([str(checkout / "bin/lets"), "sdlc", *arguments], cwd=checkout,
                              env=environment, capture_output=True, text=True, timeout=30)

    @staticmethod
    def document(checkout: Path, arguments: List[str]) -> Dict[str, Any]:
        """Returns successful public command JSON after the LETS diagnostic preamble."""
        result = SdlcCommandHelper.run(checkout, [*arguments, '--json'])
        assert result.returncode == 0, result.stderr + result.stdout
        return json.loads(result.stdout[result.stdout.index('{'):])

    @staticmethod
    def fresh_clone(checkout: Path) -> Path:
        """Creates another checkout with shared tooling but independent artifact storage."""
        project = Path(__file__).resolve().parents[2]
        fresh = checkout.parent / 'fresh'
        subprocess.run(['git', '--no-pager', 'clone', '-q', str(checkout.parent / 'remote.git'), str(fresh)],
                       check=True)

        # Reuses interpreter and tools without copying host-local SDLC state
        for entry in ['tools', 'bin', 'lets']:
            (fresh / entry).symlink_to(project / entry, target_is_directory=True)
        (fresh / 'etc').mkdir()
        for name in ['proj.conf', 'sdlc.conf']:
            shutil.copy2(project / 'etc' / name, fresh / 'etc' / name)
        (fresh / '.lets').mkdir()
        (fresh / '.lets/pyenv').symlink_to(project / '.lets/pyenv', target_is_directory=True)
        return fresh


class TestSdlcPublicCommands:
    """Verifies public item intake, protected image authority, and lease refusal."""

    def test_retained_safety_help_and_models_dispatch_without_image_effects(self, tmp_path: Path) -> None:
        """Checks public safety wrappers and nine model rows in an isolated checkout.

        Args:
            tmp_path: Supplies a disposable checkout and local ledger remote.
        """
        # Exercises real wrapper parsing without images or package installation
        checkout = SdlcCommandHelper.create(tmp_path)
        for command in ["package-init", "test-package", "verify-package", "lock-run"]:
            result = SdlcCommandHelper.run(checkout, [command, "--help"])
            assert result.returncode == 1, result.stderr + result.stdout
            assert f"Usage: ./bin/lets sdlc {command}" in result.stdout

        # Preserves exact configured role order and visible model and effort values
        models = SdlcCommandHelper.run(checkout, ["models"])
        assert models.returncode == 0, models.stderr + models.stdout
        rows = [line for line in models.stdout.splitlines() if "\t" in line]
        assert rows == [
            "coordinator\tgpt-6.2-sol\txhigh", "requirements\tgpt-6.2-astra\txhigh",
            "image_analysis\tgpt-6.1-terra\thigh", "planner\tgpt-6.2-astra\txhigh",
            "implementation\tgpt-6.2-astra\txhigh", "validation\tgpt-6.2-astra\txhigh",
            "integration\tgpt-6.2-astra\txhigh", "qa\tgpt-6.2-astra\txhigh",
            "follow_up\tgpt-6.1-sol\thigh",
        ]
        assert not (checkout / "var").exists()
        assert not (checkout / "packages").exists()
        assert not (checkout / ".lets/sdlc").exists()

    def test_lock_run_dispatches_documented_separator_and_exact_child_arguments(self, tmp_path: Path) -> None:
        """Runs an ordinary recorder through the public lock wrapper without image access.

        Args:
            tmp_path: Supplies a disposable checkout and executable recorder.
        """
        # Creates an ordinary recorder with a path that requires exact argument boundaries
        checkout = SdlcCommandHelper.create(tmp_path)
        recorder = tmp_path / "child recorder"
        recorder.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@" > "$0.argv"\n', encoding="utf-8")
        recorder.chmod(0o755)
        image = tmp_path / "nonexistent synthetic image"
        result = SdlcCommandHelper.run(checkout, ["lock-run", "--image", str(image), "--",
                                                 str(recorder), "--flag", "two words", "--"])
        assert result.returncode == 0, result.stderr + result.stdout
        assert Path(f"{recorder}.argv").read_text(encoding="utf-8").splitlines() == ["--flag", "two words", "--"]
        assert not image.exists()
        assert not (checkout / "var").exists()
        assert not (checkout / "packages").exists()

    def test_artifact_commands_preserve_bytes_and_bind_review(self, tmp_path: Path) -> None:
        """Recovers binary and hidden evidence on another host and rejects changed reviewed inputs."""
        checkout = SdlcCommandHelper.create(tmp_path)
        for command in [
            ['items', 'new', '--kind', 'fix', '--desc', 'DURABLE-ARTIFACT-FIX', '--idea', 'Retain evidence',
             '--description', 'Preserve exact stage artifact bytes.'],
            ['worktree', 'add', 'ITM-0001', 'integration'],
        ]:
            result = SdlcCommandHelper.run(checkout, command)
            assert result.returncode == 0, result.stderr + result.stdout

        # Publishes explicit regular files, including bytes that text serialization cannot preserve
        integration = checkout / '.codex/worktrees/ITM-0001/integration'
        originals = {'evidence/report.bin': bytes(range(256)), 'contracts/.capture': b'\x00hidden\xff\r\n'}
        entries = []
        for index, (name, payload) in enumerate(originals.items()):
            source = integration / name
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(payload)
            source.chmod(0o640 + index)
            entries.append({'source_path': str(source), 'original_path': name,
                            'managed_path': f'items/ITM-0001/implementation/{name}'})
        manifest = tmp_path / 'input.json'
        manifest.write_text(json.dumps({'schema_version': 1, 'purpose': 'INPUT', 'entries': entries}),
                            encoding='utf-8')
        published = SdlcCommandHelper.document(checkout, ['artifacts', 'publish', 'ITM-0001', '--stage',
                                                        'implementation', '--manifest', str(manifest)])
        digest = published['digest']
        assert published['purpose'] == 'INPUT'
        assert published['ledger_path'] == f'artifacts/bundles/{digest}.json'
        repeated = SdlcCommandHelper.document(checkout, ['artifacts', 'publish', 'ITM-0001', '--stage',
                                                       'implementation', '--manifest', str(manifest)])
        assert repeated['digest'] == digest
        listed = SdlcCommandHelper.run(checkout, ['artifacts', 'list', 'ITM-0001', '--json'])
        assert listed.returncode == 0, listed.stderr + listed.stdout
        retained = json.loads(listed.stdout[listed.stdout.index('[\n'):])
        assert [binding['digest'] for binding in retained] == [digest]

        # Restores from ledger after complete loss of local materializations and in a fresh clone
        shutil.rmtree(checkout / '.codex/sdlc/artifacts')
        missing = SdlcCommandHelper.run(checkout, ['artifacts', 'verify', '--bundle', digest])
        assert missing.returncode != 0
        fresh = SdlcCommandHelper.fresh_clone(checkout)
        for destination in [checkout, fresh]:
            restored = SdlcCommandHelper.document(destination, ['artifacts', 'restore', '--bundle', digest])
            repeated = SdlcCommandHelper.document(destination, ['artifacts', 'restore', '--bundle', digest])
            verified = SdlcCommandHelper.document(destination, ['artifacts', 'verify', '--bundle', digest])
            assert verified['digest'] == restored['digest'] == repeated['digest'] == digest
            for index, (name, payload) in enumerate(originals.items()):
                managed = destination / '.codex/sdlc/artifacts/items/ITM-0001/implementation' / name
                assert managed.read_bytes() == payload
                assert managed.stat().st_mode & 0o777 == 0o640 + index
        rendered = SdlcCommandHelper.run(fresh, ['artifacts', 'verify', '--bundle', digest])
        assert rendered.returncode == 0, rendered.stderr + rendered.stdout
        assert f'INPUT {digest}' in rendered.stdout
        assert 'source tree None' in rendered.stdout
        assert 'RESULT None' in rendered.stdout

        # Removes only synthetic preserved import files so the source snapshot contains product files alone
        for name in originals:
            (integration / name).unlink()

        # Captures source and INPUT independently, then publishes a RESULT for that exact pair
        presented = SdlcCommandHelper.run(checkout, ['worktree', 'present', 'ITM-0001'])
        assert presented.returncode == 0, presented.stderr + presented.stdout
        snapshot = SdlcCommandHelper.document(checkout, ['worktree', 'snapshot', 'ITM-0001'])
        tree = snapshot['snapshot_tree']
        input_digest = snapshot['snapshot_artifacts']['digest']
        assert not (Path(snapshot['verification_worktree']) / 'evidence').exists()
        assert not (Path(snapshot['verification_worktree']) / 'contracts').exists()
        refused_flag = SdlcCommandHelper.run(checkout, ['worktree', 'context', 'ITM-0001',
                                                       '--expected-artifacts', input_digest])
        assert refused_flag.returncode != 0
        assert '--expected-artifacts does not apply to worktree context' in refused_flag.stderr
        report = checkout / '.codex/sdlc/artifacts/items/ITM-0001/qa/result.json'
        report.parent.mkdir(parents=True)
        report.write_text(json.dumps({'source_tree': tree, 'input_digest': input_digest, 'observed': 'synthetic'}),
                          encoding='utf-8')
        manifest.write_text(json.dumps({'schema_version': 1, 'purpose': 'RESULT', 'source_tree': tree,
                                       'input_digest': input_digest, 'entries': [
                                           {'source_path': str(report), 'original_path': 'qa/result.json',
                                            'managed_path': 'items/ITM-0001/qa/result.json'}]}), encoding='utf-8')
        result_binding = SdlcCommandHelper.document(checkout, ['artifacts', 'publish', 'ITM-0001', '--stage',
                                                             'qa', '--manifest', str(manifest)])
        verified = SdlcCommandHelper.document(checkout, ['worktree', 'verified', 'ITM-0001', '--expected-tree',
                                                        tree, '--expected-artifacts', input_digest])
        assert verified['qa_artifacts']['digest'] == result_binding['digest']

        # Refuses approval after ignored managed bytes change while the source Git tree stays fixed
        selected = checkout / '.codex/sdlc/artifacts/items/ITM-0001/implementation/evidence/report.bin'
        selected.write_bytes(b'changed input')
        fingerprint = SdlcCommandHelper.run(checkout, ['worktree', 'fingerprint', 'ITM-0001'])
        assert fingerprint.returncode == 0, fingerprint.stderr + fingerprint.stdout
        assert fingerprint.stdout.splitlines()[-1] == tree
        refused = SdlcCommandHelper.run(checkout, ['worktree', 'approve', 'ITM-0001', '--expected-tree', tree,
                                                  '--expected-artifacts', input_digest])
        assert refused.returncode != 0
        context = SdlcCommandHelper.document(checkout, ['worktree', 'context', 'ITM-0001'])
        assert context['approved_tree'] is None
        assert context['verified_tree'] is None

    def test_item_and_chain_use_one_ledger(self, tmp_path: Path) -> None:
        """Mints an item and chain through LETS without creating image links or legacy records."""
        checkout = SdlcCommandHelper.create(tmp_path)
        legacy = checkout / "docs/requirements/REQ-0001-EXISTING.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("Existing hardware evidence stays intact.\n", encoding="utf-8")
        for arguments in [["add", "docs"], ["commit", "-qm", "Preserve prior requirement"],
                          ["push", "-q", "origin", "HEAD:refs/heads/sdlc"]]:
            subprocess.run(["git", "--no-pager", "-C", str(checkout), *arguments], check=True)
        minted = SdlcCommandHelper.run(checkout, ["items", "new", "--kind", "fix", "--desc", "SAFE-IMAGE-FIX",
                                                "--idea", "Keep original", "--description", "Preserve original image."])
        assert minted.returncode == 0, minted.stderr + minted.stdout
        required = SdlcCommandHelper.run(checkout, ["hardware", "require", "ITM-0001"])
        assert required.returncode == 0, required.stderr
        shown = SdlcCommandHelper.run(checkout, ["items", "show", "ITM-0001", "--json"])
        document = json.loads(shown.stdout[shown.stdout.index("{"):])
        assert document["hardware"]["required"] is True
        chain = SdlcCommandHelper.run(checkout, ["chains", "new", "--desc", "SAFE-IMAGE-CHAIN",
                                               "--description", "Complete image fix.", "--item", "ITM-0001"])
        assert chain.returncode == 0, chain.stderr
        assert not (checkout / "var").exists()
        retained = subprocess.run(["git", "--no-pager", "--git-dir", str(tmp_path / "remote.git"),
                                   "show", "sdlc:docs/requirements/REQ-0001-EXISTING.md"],
                                  capture_output=True, text=True, check=True)
        assert retained.stdout == legacy.read_text(encoding="utf-8")

    def test_ide_uses_project_vscode_default_and_explicit_override(self, tmp_path: Path,
                                                                 monkeypatch: pytest.MonkeyPatch) -> None:
        """Opens the exact integration folder with the configured default or explicit IDE.

        Args:
            tmp_path: the directory that owns disposable checkout and recorder state.
            monkeypatch: the fixture that restores the executable search path after the test.
        """

        # Excludes inherited defaults so only the copied project configuration selects VS Code
        monkeypatch.delenv("SCR_SDLC_IDE", raising=False)

        # Creates real item and integration state through the public command surface
        checkout = SdlcCommandHelper.create(tmp_path)
        for command in [
            ["items", "new", "--kind", "fix", "--desc", "IDE-DEFAULT-FIX", "--idea", "Open review",
             "--description", "Open the integration folder with the project IDE."],
            ["worktree", "add", "ITM-0001", "integration"],
        ]:
            result = SdlcCommandHelper.run(checkout, command)
            assert result.returncode == 0, result.stderr + result.stdout

        # Records argument boundaries without launching a desktop or requiring an installed IDE
        fake_bin = tmp_path / "fake bin"
        fake_bin.mkdir()
        for name in ["code", "review-ide"]:
            script = fake_bin / name
            script.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@" >> "$0.argv"\n', encoding="utf-8")
            script.chmod(0o755)
        monkeypatch.setenv("PATH", str(fake_bin), prepend=os.pathsep)

        # Resolves the default from the copied project configuration through the LETS wrapper
        integration = checkout / ".codex/worktrees/ITM-0001/integration"
        opened = SdlcCommandHelper.run(checkout, ["ide", "ITM-0001"])
        assert opened.returncode == 0, opened.stderr + opened.stdout
        default_record = fake_bin / "code.argv"
        expected_default = ["--disable-workspace-trust", str(integration)]
        assert default_record.read_text(encoding="utf-8").splitlines() == expected_default

        # Preserves explicit override arguments and proves the default program does not run again
        overridden = SdlcCommandHelper.run(checkout, ["ide", "ITM-0001", "--ide", "review-ide --wait"])
        assert overridden.returncode == 0, overridden.stderr + overridden.stdout
        assert (fake_bin / "review-ide.argv").read_text(encoding="utf-8").splitlines() == ["--wait", str(integration)]
        assert default_record.read_text(encoding="utf-8").splitlines() == expected_default

    def test_approved_item_scaffolds_package_only_in_its_worktree(self, tmp_path: Path) -> None:
        """Reuses SCR restoration scripts through item approval without legacy ledger writes."""
        checkout = SdlcCommandHelper.create(tmp_path)
        for command in [
            ["items", "new", "--kind", "fix", "--desc", "SAFE-IMAGE-FIX", "--idea", "Keep original",
             "--description", "Preserve original image."],
            ["hardware", "require", "ITM-0001"],
            ["items", "plan", "edit", "ITM-0001"],
        ]:
            result = SdlcCommandHelper.run(checkout, command)
            assert result.returncode == 0, result.stderr

        # Exercises numbered plan metadata through the public approval command
        draft = checkout / ".lets/sdlc/drafts/ITM-0001/PLAN.md"
        draft.write_text("""# ITM-0001-SAFE-IMAGE-FIX — Plan

## Goal
Preserve image baseline.
## Context
Disposable test only.
## Design
Reuse reversible package scripts.
## Out of scope
Real hardware access.
## BLK-0001 — Image package
### TSK-0001 — ADD SAFE PACKAGE
| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | default |
**To do**
1. Create reversible payload.
**Done when**
1. Removal restores baseline.
""", encoding="utf-8")
        for command in [
            ["items", "plan", "approve", "ITM-0001"],
            ["items", "schedule", "ITM-0001"],
            ["items", "status", "set", "ITM-0001", "IN_PROGRESS"],
            ["worktree", "add", "ITM-0001", "BLK-0001"],
        ]:
            result = SdlcCommandHelper.run(checkout, command)
            assert result.returncode == 0, result.stderr
        arguments = ["package-init", "ITM-0001", "--operation", "replace:/etc/example.conf"]
        refused = SdlcCommandHelper.run(checkout, arguments)
        assert refused.returncode != 0
        worktree = checkout / ".codex/worktrees/ITM-0001/BLK-0001"
        result = SdlcCommandHelper.run(checkout, [*arguments, "--output", str(worktree)])
        assert result.returncode == 0, result.stderr
        assert (worktree / "packages/ITM-0001-round-1/debian/postrm").exists()
        assert not (worktree / "var").exists()
        assert not (checkout / "packages").exists()

    @pytest.mark.parametrize("command", [["hardware", "pass", "ITM-0001"],
                                          ["gate", "system", "--holder", "another-item"]])
    def test_missing_confirmation_or_lease_fails(self, tmp_path: Path, command: List[str]) -> None:
        """Refuses success without evidence and shared system operations without lease ownership."""
        checkout = SdlcCommandHelper.create(tmp_path)
        result = SdlcCommandHelper.run(checkout, command)
        assert result.returncode != 0
