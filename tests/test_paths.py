import unittest
from pathlib import Path

from gfl2logger.utils.paths import default_data_dir


class DefaultDataDirTests(unittest.TestCase):
    def test_packaged_macos_app_uses_home_directory(self) -> None:
        self.assertEqual(
            default_data_dir(
                system="Darwin", frozen=True, home=Path("/Users/tester")
            ),
            Path("/Users/tester/gfl2logger"),
        )

    def test_macos_source_run_uses_current_directory(self) -> None:
        self.assertEqual(
            default_data_dir(
                system="Darwin", frozen=False, cwd=Path("/project/gfl2logger")
            ),
            Path("/project/gfl2logger"),
        )

    def test_windows_build_keeps_existing_behavior(self) -> None:
        self.assertEqual(
            default_data_dir(
                system="Windows", frozen=True, cwd=Path("C:/gfl2logger")
            ),
            Path("C:/gfl2logger"),
        )
