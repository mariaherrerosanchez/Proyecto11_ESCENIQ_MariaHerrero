"""Comprobación de arranque: la aplicación debe poder importarse en un intérprete nuevo."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AppStartupTests(unittest.TestCase):
    def test_app_imports_in_a_fresh_python_process(self):
        completed = subprocess.run(
            [sys.executable, "-c", "import app"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
