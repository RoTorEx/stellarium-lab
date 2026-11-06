#!/usr/bin/env python3
"""Check the complete local atlas at its final delivery location."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from capture_atlas import INSTRUMENTS, TARGETS, inspect_png


def verify(output):
    manifest = json.loads((output / "manifest.json").read_text())
    captures = manifest["captures"]
    expected = {
        f'{obj["id"]}-b{bortle}-{instrument["id"]}-{cohort}'
        for obj in TARGETS for bortle in (4, 5) for instrument in INSTRUMENTS
        for cohort in (("fixed",) if instrument["id"] == "vortex" else ("wide", "second"))
    }
    actual = [c["id"] for c in captures]
    assert len(actual) == len(set(actual)), "Duplicate capture identities"
    assert set(actual) == expected, f"Missing: {sorted(expected-set(actual))}; unexpected: {sorted(set(actual)-expected)}"
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
        assert capture["live"]["Oculars.selectedLensIndex"] == -1
        assert capture["live"]["Oculars.enableOcular"] is True
        vector = json.loads(capture["camera"]["j2000"])
        assert len(vector) == 3 and all(math.isfinite(x) for x in vector)
        assert math.isclose(sum(x*x for x in vector), 1, abs_tol=0.00001)
        if capture["instrument"] == "vortex":
            assert capture["magnification"] == 8 and capture["field_of_view_deg"] == 7.5
        else:
            telescope = next(i["telescope"] for i in INSTRUMENTS if i["id"] == capture["instrument"])
            focal = {70:700,102:1300,127:1500,130:650,150:750}[telescope]
            ocular = (20 if telescope == 70 else 25) if capture["cohort"] == "wide" else (4 if telescope == 70 else 10)
            assert capture["eyepiece_mm"] == ocular
            assert capture["magnification"] == focal / ocular
            fov = (50 if ocular == 20 else 30) / (focal / ocular) if telescope == 70 else (22 if ocular == 25 else 9) / focal * 57.3
            assert math.isclose(capture["field_of_view_deg"], fov, rel_tol=1e-10)
    luminances = {b: {c["light_pollution_cd_m2"] for c in captures if c["bortle"] == b} for b in (4,5)}
    assert all(len(values) == 1 for values in luminances.values())
    assert next(iter(luminances[4])) < next(iter(luminances[5]))
    repeated = {h:n for h,n in Counter(c["sha256"] for c in captures).items() if n > 1}
    assert not repeated, "Identical images: inspect for a stalled camera"
    script = (output / "data.js").read_text()
    assert json.loads(script.removeprefix("window.ATLAS_DATA = ").strip().removesuffix(";")) == manifest
    for name in ("index.html", "style.css", "app.js"):
        assert (output / name).is_file()
    print(f"Verified {len(captures)} complete PNGs, 11 objects, 6 instruments, both stock cohorts and Bortle 4/5.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=Path("gallery"))
    verify(parser.parse_args().output)
