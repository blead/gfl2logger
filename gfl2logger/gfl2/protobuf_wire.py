import struct
from typing import Any


class WireDecodeError(ValueError):
    pass


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    for shift in range(0, 70, 7):
        if offset >= len(data):
            raise WireDecodeError("truncated varint")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
    raise WireDecodeError("varint is too long")


def decode_message(data: bytes, *, _depth: int = 0) -> list[dict[str, Any]]:
    """Losslessly describe an unknown protobuf message using wire field numbers."""
    if _depth > 8:
        raise WireDecodeError("maximum nesting depth exceeded")

    fields: list[dict[str, Any]] = []
    offset = 0
    while offset < len(data):
        key, offset = _read_varint(data, offset)
        field_number = key >> 3
        wire_type = key & 0x07
        if field_number == 0:
            raise WireDecodeError("invalid field number 0")

        field: dict[str, Any] = {"field": field_number}
        if wire_type == 0:
            value, offset = _read_varint(data, offset)
            field.update(wireType="varint", value=value)
        elif wire_type == 1:
            end = offset + 8
            if end > len(data):
                raise WireDecodeError("truncated fixed64")
            field.update(
                wireType="fixed64",
                value=struct.unpack("<Q", data[offset:end])[0],
            )
            offset = end
        elif wire_type == 2:
            length, offset = _read_varint(data, offset)
            end = offset + length
            if end > len(data):
                raise WireDecodeError("truncated length-delimited field")
            value_bytes = data[offset:end]
            offset = end
            value: dict[str, Any] = {"hex": value_bytes.hex()}

            try:
                text = value_bytes.decode("utf-8")
                if text.isprintable() or "\n" in text:
                    value["text"] = text
            except UnicodeDecodeError:
                pass

            if value_bytes and "text" not in value and _depth < 8:
                try:
                    nested = decode_message(value_bytes, _depth=_depth + 1)
                except WireDecodeError:
                    nested = []
                if nested:
                    value["message"] = nested

            field.update(wireType="length-delimited", value=value)
        elif wire_type == 5:
            end = offset + 4
            if end > len(data):
                raise WireDecodeError("truncated fixed32")
            field.update(
                wireType="fixed32",
                value=struct.unpack("<I", data[offset:end])[0],
            )
            offset = end
        else:
            raise WireDecodeError(f"unsupported wire type {wire_type}")

        fields.append(field)

    return fields
