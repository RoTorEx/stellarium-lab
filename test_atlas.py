"""Regression checks for incomplete native screenshots and stale coordinates."""
import math
import struct
import unittest
import zlib

from capture_atlas import altitude_is_current, inspect_png


def chunk(kind, payload):
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind+payload))


class CaptureChecks(unittest.TestCase):
    def setUp(self):
        self.png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1,1,8,2,0,0,0)) + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00")) + chunk(b"IEND", b"")

    def test_complete_png(self):
        self.assertEqual(inspect_png(self.png), (1,1))

    def test_partial_async_write_is_rejected(self):
        for length in (8,25,len(self.png)-1,len(self.png)-12):
            with self.subTest(length=length), self.assertRaises(ValueError):
                inspect_png(self.png[:length])

    def test_corrupt_chunk_is_rejected(self):
        corrupt = bytearray(self.png)
        corrupt[20] ^= 1
        with self.assertRaises(ValueError):
            inspect_png(corrupt)

    def test_old_date_transform_is_rejected(self):
        status = {"time":{"jday":2451545}, "location":{"longitude":0,"latitude":0}}
        current = {"ra":280.46061837,"dec":30,"altitude-geometric":60}
        self.assertTrue(altitude_is_current(current,status))
        current["altitude-geometric"] = -20
        self.assertFalse(altitude_is_current(current,status))


if __name__ == "__main__":
    unittest.main()
