import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "drawio-skill" / "scripts" / "prdiff.py"
SPEC = importlib.util.spec_from_file_location("prdiff", SCRIPT)
PRDIFF = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRDIFF)


class PrDiffCliTest(unittest.TestCase):
    def test_executable_resolution(self):
        for command, explicit, executable in (
            ("D:/Test Folder/draw.io.exe", True, "D:/Test Folder/draw.io.exe"),
            ("drawio", False, "/tools/drawio"),
            ("draw.io", False, "/tools/draw.io"),
        ):
            with self.subTest(command=command), TemporaryDirectory() as directory:
                args = [str(SCRIPT), "--base", "base-sha", "--out-dir", directory]
                if explicit:
                    args.extend(["--drawio", command])
                changed = [("architecture.drawio", "modified")]
                with (
                    patch.object(sys, "argv", args),
                    patch.object(PRDIFF.shutil, "which", side_effect={command: executable}.get),
                    patch.object(PRDIFF, "changed_drawios", return_value=changed),
                    patch.object(PRDIFF, "build_entry", return_value={"path": "architecture.drawio", "status": "modified"}) as build,
                    redirect_stdout(io.StringIO()),
                ):
                    PRDIFF.main()
                build.assert_called_once_with(".", "base-sha", "HEAD", *changed[0], directory, executable)

    def test_explicit_missing_executable_is_an_error(self):
        args = [str(SCRIPT), "--base", "base-sha", "--drawio", "missing.exe"]
        output = io.StringIO()
        with (
            patch.object(sys, "argv", args),
            patch.object(PRDIFF.shutil, "which", return_value=None),
            patch.object(PRDIFF, "changed_drawios") as changed,
            redirect_stderr(output),
            self.assertRaises(SystemExit) as error,
        ):
            PRDIFF.main()
        self.assertEqual(error.exception.code, 2)
        self.assertIn("找不到 --drawio 指定的可执行文件", output.getvalue())
        changed.assert_not_called()


if __name__ == "__main__":
    unittest.main()
