import unittest

from gfl2logger.gfl2 import data
from gfl2logger.gfl2.protobuf_wire import WireDecodeError, decode_message


class PlatoonDataTests(unittest.TestCase):
    def test_options_are_grouped_in_the_requested_order(self) -> None:
        options = list(data.get_options())

        self.assertEqual(
            [option["label"] for option in options],
            [
                "Platoon Profile",
                "Members",
                "Activity",
                "Updates",
                "Weapons",
                "Attachments",
                "Common Keys",
                "Formations",
            ],
        )
        self.assertEqual(
            [option["category"] for option in options],
            ["Platoon"] * 4 + ["Others"] * 4,
        )

    def test_platoon_payload_ids_are_registered(self) -> None:
        self.assertEqual(
            list(data.DATA_TYPES),
            [21905, 21917, 21935, 21960, 11021, 11061, 11138, 23201],
        )


class ProtobufWireTests(unittest.TestCase):
    def test_unknown_message_is_decoded_losslessly(self) -> None:
        payload = b"\x08\x96\x01\x12\x02hi\x1a\x02\x08\x07"

        decoded = decode_message(payload)

        self.assertEqual(decoded[0], {"field": 1, "wireType": "varint", "value": 150})
        self.assertEqual(decoded[1]["value"], {"hex": "6869", "text": "hi"})
        self.assertEqual(
            decoded[2]["value"]["message"],
            [{"field": 1, "wireType": "varint", "value": 7}],
        )

    def test_truncated_unknown_message_is_rejected(self) -> None:
        with self.assertRaises(WireDecodeError):
            decode_message(b"\x12\x04ab")


if __name__ == "__main__":
    unittest.main()
