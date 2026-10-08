import unittest

from gfl2logger.proxy.capture import default_capture_mode


class DefaultCaptureModeTests(unittest.TestCase):
    def test_windows_client(self) -> None:
        self.assertEqual(default_capture_mode("Windows"), "local:GF2_Exilium")

    def test_macos_client(self) -> None:
        self.assertEqual(default_capture_mode("Darwin"), "local:SnqxExilium")

    def test_unsupported_platform(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Unsupported platform"):
            default_capture_mode("Plan9")


if __name__ == "__main__":
    unittest.main()
