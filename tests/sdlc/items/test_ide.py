from abc import ABC
from pathlib import Path
from typing import Callable, List, Optional
from urllib.parse import unquote, urlsplit

import pytest

from sdlc.algorithms.ide_command import IdeCommandHelper
from sdlc.controllers.cli import EXIT_ERROR, SdlcCliController
from sdlc.datasources.ide_launcher_source import IdeLauncherSource
from sdlc.models.errors import IdeError
from sdlc.wiring import AppWiring


class FakeIdeHelper(ABC):
    """Creates a real executable that records its arguments, in place of an IDE."""

    @staticmethod
    def create(directory: Path, exit_code: int = 0) -> Path:
        """Returns a script that appends its arguments to `<script>.args` and exits with the given code."""
        script = directory / "fake-ide"
        script.write_text(
            f'#!/bin/sh\nprintf "%s\\n" "$@" > "$0.argv"\necho "$@" >> "$0.args"\nexit {exit_code}\n',
            encoding="utf-8",
        )
        script.chmod(0o755)
        return script

    @staticmethod
    def recorded(script: Path) -> List[str]:
        """Returns the argument lines the script recorded, one per call."""
        record = Path(f"{script}.args")
        return record.read_text(encoding="utf-8").splitlines() if record.exists() else []

    @staticmethod
    def arguments(script: Path) -> List[str]:
        """Returns the arguments from the latest launch without merging arguments that contain spaces."""
        record = Path(f"{script}.argv")
        return record.read_text(encoding="utf-8").splitlines() if record.exists() else []


class IdeWiringHelper(ABC):
    """Builds the wiring of one host with a chosen default IDE."""

    @staticmethod
    def build(make_host: Callable[[str], AppWiring], default_ide: Optional[str]) -> AppWiring:
        """Returns a wiring over the host's checkout whose settings carry the default IDE."""
        host = make_host("alpha")
        return AppWiring(host.settings.model_copy(update={"ide": default_ide}))


class UnbuildableWiringHelper(ABC):
    """Stands in for a wiring factory that must never run."""

    @staticmethod
    def build() -> AppWiring:
        """Fails the test when the controller builds the wiring."""
        raise AssertionError("wiring must not be built")


class TestIdeCommandHelper:
    """Covers the pure command-line builder."""

    def test_appends_the_folder_after_the_ide_arguments(self, tmp_path: Path) -> None:
        """Keeps the IDE program and its own arguments, then adds the folder last."""
        assert IdeCommandHelper.build("cursor", tmp_path) == ["cursor", str(tmp_path)]
        assert IdeCommandHelper.build("code --new-window", tmp_path) == [
            "code", "--new-window", "--disable-workspace-trust", str(tmp_path)
        ]

    def test_keeps_quoted_arguments_whole(self, tmp_path: Path) -> None:
        """Splits the text like a shell, so a quoted path with spaces stays one argument."""
        assert IdeCommandHelper.build('"/opt/my ide/ide" -n', tmp_path) == ["/opt/my ide/ide", "-n", str(tmp_path)]

    @pytest.mark.parametrize("ide", ["cursor", "code"])
    @pytest.mark.parametrize("host", ["build-host", "alice@build-host"])
    def test_selects_the_ssh_remote_and_preserves_arguments(self, host: str, ide: str) -> None:
        """Keeps the SSH authority and folder together so a WSL launcher cannot select its own folder authority."""
        folder = Path("/srv/project files/scr/.codex/worktrees/ITM-0001/integration")
        assert IdeCommandHelper.build(f"{ide} --new-window", folder, host) == [
            ide, "--new-window", *( ["--disable-workspace-trust"] if ide == "code" else []), "--folder-uri",
            f"vscode-remote://ssh-remote+{host}/srv/project%20files/scr/.codex/worktrees/ITM-0001/integration",
        ]

    def test_encodes_remote_uri_characters_without_changing_the_target(self) -> None:
        """Escapes URI delimiters and literal percent signs in folder names while preserving path separators."""
        folder = Path("/srv/project #1? 100%/café/scr/.codex/worktrees/ITM-0001/integration")
        assert IdeCommandHelper.build("cursor", folder, "build#host") == [
            "cursor", "--folder-uri",
            "vscode-remote://ssh-remote+build%23host/srv/project%20%231%3F%20100%25/caf%C3%A9/"
            "scr/.codex/worktrees/ITM-0001/integration",
        ]

    @pytest.mark.parametrize("host", ["", " ", "bad host", "host\nother", "host\x00"])
    def test_rejects_invalid_remote_hosts(self, host: str, tmp_path: Path) -> None:
        """Rejects an empty host or control characters before an IDE can start."""
        with pytest.raises(IdeError, match="--host must name an SSH host"):
            IdeCommandHelper.build("code", tmp_path, host)

    @pytest.mark.parametrize("ide", ["", "   ", "vim 'unclosed"])
    def test_rejects_blank_and_unreadable_text(self, ide: str, tmp_path: Path) -> None:
        """Refuses blank text and text with an unclosed quote."""
        with pytest.raises(IdeError):
            IdeCommandHelper.build(ide, tmp_path)


class TestIdeLauncherSource:
    """Covers starting a real process."""

    def test_returns_the_exit_code_of_the_process(self, tmp_path: Path) -> None:
        """Runs the program with its arguments and passes its exit code back."""
        script = FakeIdeHelper.create(tmp_path, exit_code=3)
        assert IdeLauncherSource().launch([str(script), "folder"]) == 3
        assert FakeIdeHelper.recorded(script) == ["folder"]

    def test_rejects_a_program_that_is_not_installed(self) -> None:
        """Names the missing program instead of raising a raw OSError."""
        with pytest.raises(IdeError, match="not found"):
            IdeLauncherSource().launch(["no-such-ide-program", "folder"])


class TestIdeUsecases:
    """Covers opening the integration worktree through the wiring."""

    def test_opens_the_integration_worktree_with_the_default_ide(self, make_host: Callable[[str], AppWiring],
                                                                 tmp_path: Path) -> None:
        """Uses the project default IDE when no explicit one is given."""
        script = FakeIdeHelper.create(tmp_path)
        wiring = IdeWiringHelper.build(make_host, str(script))
        info = wiring.worktree_usecases.add("ITM-0001", "integration", None)
        opening = wiring.ide_usecases.open_integration("ITM-0001-LEDGER", None)
        assert opening.folder == info.path and opening.ide == str(script) and opening.exit_code == 0
        assert FakeIdeHelper.recorded(script) == [str(info.path)]

    def test_explicit_ide_overrides_the_default(self, make_host: Callable[[str], AppWiring], tmp_path: Path) -> None:
        """Runs the program from --ide, with its own arguments, instead of the default."""
        default_directory = tmp_path / "default"
        override_directory = tmp_path / "override"
        default_directory.mkdir()
        override_directory.mkdir()
        default_script = FakeIdeHelper.create(default_directory)
        override_script = FakeIdeHelper.create(override_directory)
        wiring = IdeWiringHelper.build(make_host, str(default_script))
        info = wiring.worktree_usecases.add("ITM-0001", "integration", None)
        wiring.ide_usecases.open_integration("ITM-0001", f"{override_script} --wait")
        assert FakeIdeHelper.recorded(override_script) == [f"--wait {info.path}"]
        assert FakeIdeHelper.recorded(default_script) == []

    def test_reports_a_missing_worktree(self, make_host: Callable[[str], AppWiring], tmp_path: Path) -> None:
        """Refuses an item that has no integration worktree, before it starts any IDE."""
        script = FakeIdeHelper.create(tmp_path)
        wiring = IdeWiringHelper.build(make_host, str(script))
        with pytest.raises(IdeError, match="no integration worktree for ITM-0001"):
            wiring.ide_usecases.open_integration("ITM-0001", None)
        assert FakeIdeHelper.recorded(script) == []

    def test_reports_a_missing_ide_setting(self, make_host: Callable[[str], AppWiring]) -> None:
        """Asks for --ide or the proj.conf variable when neither names an IDE."""
        wiring = IdeWiringHelper.build(make_host, None)
        wiring.worktree_usecases.add("ITM-0001", "integration", None)
        with pytest.raises(IdeError, match="SCR_SDLC_IDE"):
            wiring.ide_usecases.open_integration("ITM-0001", None)

    def test_opens_a_remote_worktree_without_a_local_copy(self, make_host: Callable[[str], AppWiring],
                                                         tmp_path: Path) -> None:
        """Uses the supplied remote root without resolving it through the local filesystem or creating a worktree."""
        script = FakeIdeHelper.create(tmp_path)
        wiring = IdeWiringHelper.build(make_host, str(script))
        remote_root = tmp_path / "remote" / ".codex"
        remote_root.parent.mkdir()
        remote_root.symlink_to(tmp_path / "missing-local-directory")

        opening = wiring.ide_usecases.open_integration("itm-0001-LEDGER", None, "build-host", str(remote_root))

        expected = remote_root / "worktrees" / "ITM-0001" / "integration"
        assert opening.folder == expected and opening.host == "build-host" and opening.exit_code == 0
        assert FakeIdeHelper.arguments(script) == ["--folder-uri", f"vscode-remote://ssh-remote+build-host{expected}"]
        assert wiring.worktree_usecases.list_paths("ITM-0001") == []

    @pytest.mark.parametrize("host, remote_path", [
        ("build-host", None),
        (None, "/srv/scr/.codex"),
        ("build-host", "relative/.codex"),
        ("build-host", "/srv/scr"),
        ("build-host", ""),
    ])
    def test_rejects_incomplete_or_invalid_remote_paths(self, make_host: Callable[[str], AppWiring],
                                                       tmp_path: Path, host: Optional[str],
                                                       remote_path: Optional[str]) -> None:
        """Reports invalid remote options before launching an IDE or creating a local worktree."""
        script = FakeIdeHelper.create(tmp_path)
        wiring = IdeWiringHelper.build(make_host, str(script))
        with pytest.raises(IdeError, match="--host and --path|--path must be an absolute path"):
            wiring.ide_usecases.open_integration("ITM-0001", None, host, remote_path)
        assert FakeIdeHelper.recorded(script) == []


class TestIdeCli:
    """Covers the `ide` command line."""

    def test_opens_through_the_cli_and_passes_the_exit_code(self, make_host: Callable[[str], AppWiring],
                                                            tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Prints the IDE and folder and returns the IDE exit code."""
        script = FakeIdeHelper.create(tmp_path, exit_code=4)
        wiring = IdeWiringHelper.build(make_host, str(script))
        info = wiring.worktree_usecases.add("ITM-0001", "integration", None)
        cli = SdlcCliController(lambda: wiring)
        assert cli.run(["ide", "ITM-0001"]) == 4
        assert capsys.readouterr().out.strip() == f"{script} {info.path}"

    def test_reports_failures_as_errors(self, make_host: Callable[[str], AppWiring],
                                        capsys: pytest.CaptureFixture) -> None:
        """Returns the error code and a one-line message for a missing worktree."""
        cli = SdlcCliController(lambda: IdeWiringHelper.build(make_host, "cursor"))
        assert cli.run(["ide", "ITM-0001"]) == EXIT_ERROR
        assert "no integration worktree" in capsys.readouterr().err

    def test_requires_the_item_argument(self) -> None:
        """Fails argument validation without building any repository wiring."""
        assert SdlcCliController(UnbuildableWiringHelper.build).run(["ide"]) != 0

    def test_opens_remote_integration_through_the_cli(self, make_host: Callable[[str], AppWiring],
                                                     tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Forwards both remote options and the IDE override, preserving argument boundaries and the exit code."""
        script = FakeIdeHelper.create(tmp_path, exit_code=4)
        wiring = IdeWiringHelper.build(make_host, "no-such-default-ide")
        cli = SdlcCliController(lambda: wiring)
        remote_root = "/srv/project files/scr/.codex/"

        assert cli.run([
            "ide", "itm-0001-LEDGER", "--ide", f"{script} --new-window",
            "--host", "alice@build-host", "--path", remote_root,
        ]) == 4

        uri = "vscode-remote://ssh-remote+alice@build-host/srv/project%20files/scr/.codex/worktrees/ITM-0001/integration"
        assert FakeIdeHelper.arguments(script) == ["--new-window", "--folder-uri", uri]
        assert capsys.readouterr().out.strip() == f"{script} --new-window --folder-uri {uri}"

    def test_keeps_the_ssh_folder_when_a_launcher_adds_a_wsl_authority(self, make_host: Callable[[str], AppWiring],
                                                                     tmp_path: Path) -> None:
        """Preserves the SSH folder URI through a real wrapper that adds its own --remote option."""

        # Simulates the WSL wrapper that forwards arguments with a default remote authority
        script = FakeIdeHelper.create(tmp_path)
        wrapper = tmp_path / "wsl-ide"
        wrapper.write_text(
            '#!/bin/sh\nrecording_ide="$(dirname "$0")/fake-ide"\n'
            'exec "$recording_ide" --remote wsl+Ubuntu "$@"\n',
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        wiring = IdeWiringHelper.build(make_host, str(wrapper))
        cli = SdlcCliController(lambda: wiring)

        # Opens an SSH folder whose URI must remain independent of the wrapper's default
        root = "/srv/project #1? 100%/scr/.codex"
        assert cli.run(["ide", "ITM-0001", "--host", "otg2", "--path", root]) == 0
        arguments = FakeIdeHelper.arguments(script)
        assert arguments.count("--remote") == 1
        uri = urlsplit(arguments[arguments.index("--folder-uri") + 1])
        assert uri.scheme == "vscode-remote" and uri.netloc == "ssh-remote+otg2"
        assert unquote(uri.path) == f"{root}/worktrees/ITM-0001/integration"
        assert not uri.query and not uri.fragment

    @pytest.mark.parametrize("options", [["--host", "build-host"], ["--path", "/srv/scr/.codex"]])
    def test_reports_unpaired_remote_options(self, make_host: Callable[[str], AppWiring], options: List[str],
                                            tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Reports a remote option pair error without launching the IDE."""
        script = FakeIdeHelper.create(tmp_path)
        wiring = IdeWiringHelper.build(make_host, str(script))
        cli = SdlcCliController(lambda: wiring)
        assert cli.run(["ide", "ITM-0001", *options]) == EXIT_ERROR
        assert "--host and --path must be supplied together" in capsys.readouterr().err
        assert FakeIdeHelper.recorded(script) == []
