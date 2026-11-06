"""Regression checks for incomplete native screenshots and stale coordinates."""
import math
import struct
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zlib

from capture_atlas import altitude_is_current, inspect_png
import stellarium as st
from verify_atlas import check_repeated_images


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

    def test_reducer_selects_the_explicit_scenario_not_the_builtin(self):
        equipment = {
            "telescope":{"1":{"name":"[Compare] Sky-Watcher. MAK 102/1300","focalLength":"1300"}},
            "ocular":{"3":{"name":"[Compare] Sky-Watcher. Super 25mm","efl":"25","afov":"50","fieldStop":"22"}},
            "lens":{"1":{"name":"[Built-in] F/6.3 Reducer","multipler":"0.63"},
                    "4":{"name":"[Compare] Nominal reducer 0.63x (idealized; compatibility unverified)","multipler":"0.63"}}
        }
        with patch.object(st,"equipment",return_value=equipment), patch.object(st,"apply_view",return_value={}) as apply:
            result=st.view(102,25,"M45",reducer=.63)
        self.assertEqual(apply.call_args.args[:3],("1","3","4"))
        self.assertAlmostEqual(result["magnification"],32.76)
        self.assertAlmostEqual(result["field_of_view_deg"],22/(1300*.63)*57.3)

    def test_equal_apertures_do_not_select_the_wrong_optical_design(self):
        equipment = {
            "telescope":{"1":{"name":"[Compare] Sky-Watcher. MAK 102/1300","focalLength":"1300"},
                         "6":{"name":"[Compare] Sky-Watcher Startravel 102/500","focalLength":"500"}},
            "ocular":{"3":{"name":"[Compare] Sky-Watcher. Super 10mm","efl":"10","afov":"52","fieldStop":"9"},
                      "8":{"name":"[Compare] Sky-Watcher Photo 10mm (AFOV estimate 50deg)","efl":"10","afov":"50","fieldStop":"0"}},
            "lens":{}
        }
        with patch.object(st,"equipment",return_value=equipment), patch.object(st,"apply_view",return_value={}) as apply:
            result=st.view("startravel102",10,"M45")
        self.assertEqual(apply.call_args.args[:3],("6","8",-1))
        self.assertEqual(result["magnification"],50)
        self.assertEqual(result["field_of_view_deg"],1)

    def test_reducer_is_not_silently_applied_to_other_kits(self):
        with patch.object(st,"equipment") as equipment:
            with self.assertRaisesRegex(RuntimeError,"MAK"):
                st.view("explorer130",25,"M45",reducer=.5)
            equipment.assert_not_called()

    def test_optional_same_focal_length_selects_product_identity(self):
        equipment={"telescope":{"1":{"name":"[Compare] Sky-Watcher. MAK 102/1300","focalLength":"1300"}},
                   "ocular":{"7":{"name":"[Compare] Sky-Watcher SWA-58 8mm","efl":"8","afov":"58","fieldStop":"0"},
                             "8":{"name":"[Compare] TS-Optics N-ED 8mm","efl":"8","afov":"60","fieldStop":"0"}},"lens":{}}
        with patch.object(st,"equipment",return_value=equipment),patch.object(st,"apply_view",return_value={}) as apply:
            first=st.view(102,None,"Jupiter",upgrade="swa8")
            first_index=apply.call_args.args[1]
            second=st.view(102,None,"Jupiter",upgrade="ned8")
            second_index=apply.call_args.args[1]
        self.assertNotEqual(first_index,second_index)
        self.assertEqual(first["magnification"],second["magnification"])
        self.assertLess(first["field_of_view_deg"],second["field_of_view_deg"])

    def test_identical_optics_can_render_identically_but_different_scenes_cannot(self):
        first={"sha256":"same","instrument":"heritage130","object":"ring","bortle":5,"cohort":"wide","magnification":26,"field_of_view_deg":1.939,"scene":{"at":"2027-05-06T01:30:00+02:00"}}
        second=dict(first,instrument="explorer130")
        check_repeated_images([first,second])
        second["object"]="andromeda"
        with self.assertRaisesRegex(AssertionError,"scenes"):
            check_repeated_images([first,second])
        second.update(object="ring",instrument="mak127")
        with self.assertRaisesRegex(AssertionError,"Unexpected"):
            check_repeated_images([first,second])

    def test_qsettings_lexical_serialization_keeps_numeric_array_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"modules/Oculars").mkdir(parents=True)
            (root/"modules/Oculars/ocular.ini").write_text(
                "[telescope]\n0\\name=First\n1\\name=Second\n10\\name=Eleventh\n2\\name=Third\n[ocular]\n[lens]\n")
            with patch.object(st,"CONFIG",root):
                records=st.equipment()["telescope"]
        self.assertEqual(list(records),["0","1","2","10"])


if __name__ == "__main__":
    unittest.main()
