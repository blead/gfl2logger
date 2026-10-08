import unittest

from gfl2logger.gfl2.data import DATA_TYPES, get_options
from gfl2logger.proxy.capture import PROCESS_NAMES

# Payload type -> (option name, group shown in the window, export format).
EXPECTED = {
    21905: ("gfl2_platoonprofile", "Platoon", "json"),
    21917: ("gfl2_guildmembers", "Platoon", "csv"),
    21935: ("gfl2_platoonactivity", "Platoon", "json"),
    21960: ("gfl2_platoonupdates", "Platoon", "json"),
    11021: ("gfl2_weapons", "Others", "csv"),
    11061: ("gfl2_attachments", "Others", "csv"),
    11138: ("gfl2_commonkeys", "Others", "csv"),
    23201: ("gfl2_formations", "Others", "json"),
}


class PayloadCoverageTests(unittest.TestCase):
    """The same payloads, options and groups must exist on every platform."""

    def test_every_supported_payload_is_registered(self) -> None:
        self.assertEqual(set(DATA_TYPES), set(EXPECTED))

    def test_each_payload_has_its_option_and_group(self) -> None:
        for payload_type, (name, category, _format) in EXPECTED.items():
            with self.subTest(payload_type=payload_type):
                (option,) = DATA_TYPES[payload_type].OPTIONS
                self.assertEqual(option["name"], name)
                self.assertEqual(option["category"], category)
                self.assertIs(option["default"], True)

    def test_each_payload_exports_in_its_documented_format(self) -> None:
        for payload_type, (_name, _category, export_format) in EXPECTED.items():
            with self.subTest(payload_type=payload_type):
                self.assertTrue(
                    callable(getattr(DATA_TYPES[payload_type], f"to_{export_format}"))
                )

    def test_window_lists_platoon_options_before_the_others(self) -> None:
        categories = [option["category"] for option in get_options()]
        self.assertEqual(categories, ["Platoon"] * 4 + ["Others"] * 4)

    def test_capture_is_scoped_to_the_game_process_on_both_platforms(self) -> None:
        self.assertEqual(
            PROCESS_NAMES, {"Windows": "GF2_Exilium", "Darwin": "SnqxExilium"}
        )


if __name__ == "__main__":
    unittest.main()
