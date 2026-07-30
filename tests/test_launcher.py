import os
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_launcher_mounts_project_config_and_forwards_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary_dir = Path(directory)
            captured_arguments = temporary_dir / "docker-arguments"
            fake_docker = temporary_dir / "docker"
            fake_docker.write_text(
                '#!/bin/sh\nprintf "%s\\n" "$@" > "$CAPTURED_ARGUMENTS"\n',
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            environment = {
                **os.environ,
                "CAPTURED_ARGUMENTS": str(captured_arguments),
                "PATH": f"{temporary_dir}:{os.environ['PATH']}",
            }

            subprocess.run(
                [str(PROJECT_ROOT / "run.sh"), "AAPL", "-t", "1m"],
                cwd=temporary_dir,
                env=environment,
                check=True,
            )

            arguments = captured_arguments.read_text(encoding="utf-8").splitlines()
            self.assertIn(
                f"{PROJECT_ROOT / 'config/config.json'}:/app/config/config.json",
                arguments,
            )
            self.assertEqual(arguments[-4:], ["stocktracker", "AAPL", "-t", "1m"])


if __name__ == "__main__":
    unittest.main()
