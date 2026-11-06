#!/usr/bin/env python3
"""Check the complete local atlas at its final delivery location."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

from capture_atlas import INSTRUMENTS, TARGETS, REDUCERS, cohorts_for, inspect_png


def check_repeated_images(captures):
    by_hash=defaultdict(list)
    for capture in captures:
        by_hash[capture["sha256"]].append(capture)
    for group in by_hash.values():
        if len(group)==1:
            continue
        # These two profiles intentionally have identical optical parameters,
        # flips and eyepieces; their mounts do not change the native render.
        assert len(group)==2 and {c["instrument"] for c in group}=={"explorer130","heritage130"}, "Unexpected identical images: inspect for a stalled camera"
        signatures={(c["object"],c["bortle"],c["cohort"],c["magnification"],c["field_of_view_deg"],c["scene"]["at"]) for c in group}
        assert len(signatures)==1, "Identical images cross observing scenes or optical selections"


def verify(output):
    manifest = json.loads((output / "manifest.json").read_text())
    captures = manifest["captures"]
    expected = {
        f'{obj["id"]}-b{bortle}-{instrument["id"]}-{cohort}'
        for obj in TARGETS for bortle in (4, 5) for instrument in INSTRUMENTS
        for cohort in cohorts_for(instrument)
    }
    actual = [c["id"] for c in captures]
    assert len(actual) == len(set(actual)), "Duplicate capture identities"
    assert set(actual) == expected, f"Missing: {sorted(expected-set(actual))}; unexpected: {sorted(set(actual)-expected)}"
    assert manifest["objects"] == TARGETS
    assert [i["id"] for i in manifest["instruments"]] == [i["id"] for i in INSTRUMENTS]
    assert sum(bool(i.get("shortlist")) for i in manifest["instruments"]) == 4
    dates = {obj["id"]: obj["at"] for obj in TARGETS}
    for capture in captures:
        path = output / capture["image"]
        assert path.resolve().is_relative_to(output.resolve()), "Image escapes the gallery"
        data = path.read_bytes()
        assert inspect_png(data) == (capture["width"], capture["height"])
        assert capture["width"] == capture["height"] == 1536
        assert len(data) == capture["bytes"]
        assert hashlib.sha256(data).hexdigest() == capture["sha256"]
        assert capture["scene"]["at"] == dates[capture["object"]]
        assert capture["scene"]["target_altitude_deg"] > 15
        reduction = REDUCERS.get(capture["cohort"], 1)
        assert capture.get("reducer",1) == reduction
        assert (capture["live"]["Oculars.selectedLensIndex"] >= 0) == (reduction != 1)
        assert capture["live"]["Oculars.enableOcular"] is True
        vector = json.loads(capture["camera"]["j2000"])
        assert len(vector) == 3 and all(math.isfinite(x) for x in vector)
        assert math.isclose(sum(x*x for x in vector), 1, abs_tol=0.00001)
        if capture["instrument"] == "vortex":
            assert capture["magnification"] == 8 and capture["field_of_view_deg"] == 7.5
        else:
            telescope = next(i["telescope"] for i in INSTRUMENTS if i["id"] == capture["instrument"])
            focal = {70:700,102:1300,127:1500,130:650,150:750,"explorer130":650,"startravel102":500}[telescope]
            ocular = (4 if telescope == 70 else 10) if capture["cohort"] == "second" else (20 if telescope in (70,"startravel102") else 25)
            assert capture["eyepiece_mm"] == ocular
            assert math.isclose(capture["magnification"], focal / ocular * reduction, rel_tol=1e-10)
            if telescope == 70:
                fov = (50 if ocular == 20 else 30) / (focal / ocular)
            elif telescope == "startravel102":
                fov = 50 / (focal / ocular)
            else:
                fov = (22 if ocular == 25 else 9) / (focal * reduction) * 57.3
            assert math.isclose(capture["field_of_view_deg"], fov, rel_tol=1e-10)
    luminances = {b: {c["light_pollution_cd_m2"] for c in captures if c["bortle"] == b} for b in (4,5)}
    assert all(len(values) == 1 for values in luminances.values())
    assert next(iter(luminances[4])) < next(iter(luminances[5]))
    check_repeated_images(captures)
    script = (output / "data.js").read_text()
    assert json.loads(script.removeprefix("window.ATLAS_DATA = ").strip().removesuffix(";")) == manifest
    for name in ("index.html", "style.css", "app.js"):
        assert (output / name).is_file()
    print(f"Verified {len(captures)} complete PNGs, 11 objects, 8 instruments, stock cohorts, four MAK reducer scenarios and Bortle 4/5.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=Path("gallery"))
    verify(parser.parse_args().output)
