#!/usr/bin/env python3
"""Operate a local, password-authenticated Stellarium 24.4 session."""
import argparse
import base64
import configparser
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / ".local"
BASE = "http://127.0.0.1:8090/api/"
CONFIG = ROOT.parents[3] / "config/dotfiles/stellarium/user"
TELESCOPES = {
    70: "Celestron PowerSeeker 70EQ 70/700 (model unconfirmed)",
    102: "Sky-Watcher. MAK 102/1300",
    127: "Sky-Watcher. MAK 127/1500",
    130: "Sky-Watcher Heritage 130P 130/650",
    150: "Sky-Watcher Heritage 150P 150/750",
}
BINOCULAR = "Vortex Diamondback 8x42"


def profile_name(item):
    name = item["name"]
    for tag in ("[Compare] ", "[Built-in] ", "[Existing] ", "[Legacy] "):
        if name.startswith(tag):
            return name[len(tag):]
    return name


def request(path, data=None):
    password = (LOCAL / "password").read_text().strip()
    headers = {"Authorization": "Basic " + base64.b64encode((":" + password).encode()).decode()}
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as response:
        value = response.read().decode()
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def equipment():
    ini = configparser.ConfigParser(interpolation=None)
    ini.optionxform = str
    ini.read(CONFIG / "modules/Oculars/ocular.ini")
    result = {}
    for kind in ("telescope", "ocular", "lens"):
        result[kind] = {}
        for key, value in ini[kind].items():
            index, field = key.split("\\", 1)
            result[kind].setdefault(index, {})[field] = value
    return result


def start():
    if sys.platform != "darwin":
        raise RuntimeError("Automatic launch currently supports macOS; the HTTP commands are portable.")
    running = subprocess.run(["pgrep", "-x", "stellarium"], capture_output=True)
    if running.returncode == 0:
        raise RuntimeError("Stellarium is already running. Quit it before starting an authenticated session.")
    if running.returncode != 1:
        raise RuntimeError("Cannot inspect running applications; run from a local terminal.")
    if not (CONFIG / "config.ini").is_file():
        raise RuntimeError("Shared config is missing. Clone the config repository and install its directory link first.")
    active = Path.home() / "Library/Application Support/Stellarium"
    if not active.is_symlink() or active.resolve() != CONFIG.resolve():
        raise RuntimeError("The application's user directory is not linked to the shared config. Run link.sh first.")
    LOCAL.mkdir(mode=0o700, exist_ok=True)
    LOCAL.chmod(0o700)
    password = secrets.token_urlsafe(32)
    secret_file = LOCAL / "password"
    secret_file.touch(mode=0o600, exist_ok=True)
    secret_file.chmod(0o600)
    secret_file.write_text(password)
    script = LOCAL / "start.ssc"
    script.touch(mode=0o600, exist_ok=True)
    script.chmod(0o600)
    script.write_text("RemoteControl.setFlagEnabled(false);\n"
                      f"RemoteControl.setPassword({json.dumps(password)});\n"
                      "RemoteControl.setFlagUsePassword(true);\n"
                      "RemoteControl.setFlagAutoStart(false);\n"
                      "RemoteControl.setFlagEnabled(true);\n")
    subprocess.run(["open", "-a", "Stellarium", "--args", "--startup-script", str(script)], check=True)
    for _ in range(40):
        try:
            status = request("main/status")
            script.unlink()
            return status
        except (OSError, urllib.error.URLError):
            time.sleep(0.5)
    raise RuntimeError("Stellarium did not expose the authenticated API. Inspect its log.txt.")


def view(telescope, eyepiece, target, hide_landscape=False, barlow=1):
    stock_eyepieces = (20, 4) if telescope == 70 else (25, 10)
    if eyepiece is None:
        eyepiece = stock_eyepieces[0]
    if eyepiece not in stock_eyepieces:
        raise RuntimeError(f"Stock eyepieces for this telescope: {stock_eyepieces}")
    if barlow != 1 and telescope != 70:
        raise RuntimeError("The 3x Barlow is part of the PowerSeeker kit; other kits default to no Barlow.")
    items = equipment()
    ti = next(i for i, t in items["telescope"].items()
              if profile_name(t) == TELESCOPES[telescope])
    ocular_prefix = "Celestron PowerSeeker" if telescope == 70 else "Sky-Watcher."
    oi = next(i for i, o in items["ocular"].items()
              if profile_name(o).startswith(ocular_prefix) and float(o["efl"]) == eyepiece)
    li = next(i for i, lens in items["lens"].items() if float(lens["multipler"]) == barlow) if barlow != 1 else -1
    magnification = float(items["telescope"][ti]["focalLength"]) / eyepiece * barlow
    field_stop = float(items["ocular"][oi]["fieldStop"])
    fov = (field_stop / (float(items["telescope"][ti]["focalLength"]) * barlow) * 57.3
           if field_stop > 0 else float(items["ocular"][oi]["afov"]) / magnification)
    return {"telescope": items["telescope"][ti], "eyepiece": items["ocular"][oi],
            "barlow": barlow, "magnification": magnification, "field_of_view_deg": fov,
            **apply_view(ti, oi, li, target, hide_landscape)}


def binocular_view(target, hide_landscape=False):
    items = equipment()
    oi = next(i for i, o in items["ocular"].items() if profile_name(o) == BINOCULAR)
    # Oculars stores a complete binocular in its ocular list. Telescope and lens
    # parameters are ignored by the plugin in this mode.
    ti = request("stelproperty/list")["Oculars.selectedTelescopeIndex"]["value"]
    if ti < 0:
        ti = 0
    return {"binocular": items["ocular"][oi], "telescope": None, "barlow": 1,
            "magnification": float(items["ocular"][oi]["efl"]),
            "field_of_view_deg": float(items["ocular"][oi]["afov"]),
            **apply_view(ti, oi, -1, target, hide_landscape)}


def apply_view(ti, oi, li, target, hide_landscape=False):
    properties = request("stelproperty/list")
    if hide_landscape:
        for name in ("landscapeDisplayed", "fogDisplayed"):
            request("stelproperty/set", {"id": "LandscapeMgr." + name, "value": "false"})
    for name in ("selectedTelescopeIndex", "selectedOcularIndex", "selectedLensIndex", "enableOcular"):
        if "Oculars." + name not in properties:
            raise RuntimeError(f"Installed API does not expose Oculars.{name}")
    request("stelproperty/set", {"id": "Oculars.enableOcular", "value": "false"})
    request("main/focus", {"target": target, "mode": "mark"})
    info = request("objects/info?" + urllib.parse.urlencode({"name": target, "format": "json"}))
    if not info.get("found"):
        raise RuntimeError(f"Object was not found: {target}")
    ra, dec = math.radians(info["raJ2000"]), math.radians(info["decJ2000"])
    direction = [math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)]
    request("main/view", {"j2000": json.dumps(direction)})
    for name, value in (("selectedTelescopeIndex", ti), ("selectedOcularIndex", oi),
                        ("selectedLensIndex", li), ("enableOcular", "true")):
        request("stelproperty/set", {"id": "Oculars." + name, "value": value})
    time.sleep(0.5)
    props = request("stelproperty/list")
    expected = {"selectedTelescopeIndex": int(ti), "selectedOcularIndex": int(oi),
                "selectedLensIndex": int(li), "enableOcular": True}
    if any(props["Oculars." + k]["value"] != v for k, v in expected.items()):
        raise RuntimeError("Stellarium did not apply the requested optical combination.")
    camera = request("main/view")
    try:
        vector = json.loads(camera["j2000"])
        centered = all(math.isfinite(x) for x in vector) and sum(a*b for a,b in zip(vector, direction)) > 0.99999
    except (ValueError, TypeError):
        centered = False
    if not centered:
        raise RuntimeError("The camera is not centered on the target. Restart Stellarium before retrying.")
    return {"live": {"Oculars." + k: props["Oculars." + k]["value"] for k in expected},
            "camera": camera,
            "target": {"name": target, "above_horizon": info.get("above-horizon"),
                       "altitude_deg": info.get("altitude")},
            "view": request("main/status")["view"]}


def tour(target, seconds):
    if not math.isfinite(seconds) or seconds < 0:
        raise RuntimeError("--seconds must be a finite nonnegative number")
    results = []
    for telescope in (None, 70, 102, 127, 130, 150):
        result = binocular_view(target) if telescope is None else view(telescope, None, target)
        results.append(result)
        name = result.get("binocular", result.get("telescope"))["name"]
        print(f'{name}: {result["magnification"]:g}x, {result["field_of_view_deg"]:.2f} deg', file=sys.stderr, flush=True)
        time.sleep(seconds)
    return results


def scene(at):
    instant = datetime.fromisoformat(at)
    if instant.tzinfo is None:
        raise RuntimeError("--at requires an explicit UTC offset, e.g. 2026-11-06T21:00:00+01:00")
    utc = instant.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    request("scripts/direct", {"code": f'core.setDate({json.dumps(utc)}, "utc"); core.setTimeRate(0); core.setSelectedObjectInfo("ShortInfo");'})
    time.sleep(0.5)
    status = request("main/status")
    expected_jd = instant.timestamp() / 86400 + 2440587.5
    if abs(status["time"]["jday"] - expected_jd) > 1 / 86400 or status["time"]["timerate"] != 0:
        raise RuntimeError("Stellarium did not apply the requested frozen observing time.")
    return {"requested_at": instant.isoformat(), "time": status["time"], "location": status["location"]}


def quit_session():
    result = request("scripts/direct", {"code": 'RemoteControl.setFlagAutoStart(false); RemoteControl.setPassword(""); RemoteControl.setFlagUsePassword(false); RemoteControl.saveSettings(); core.quitStellarium();'})
    if sys.platform == "darwin":
        for _ in range(80):
            process = subprocess.run(["pgrep", "-x", "stellarium"], capture_output=True)
            if process.returncode == 1:
                return result
            if process.returncode != 0:
                raise RuntimeError("Could not verify Stellarium shutdown; check the process before editing configuration.")
            time.sleep(0.25)
        raise RuntimeError("Stellarium is still shutting down. Wait before editing configuration.")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("start", "status", "equipment", "quit", "menu"):
        commands.add_parser(name)
    show = commands.add_parser("view")
    instrument = show.add_mutually_exclusive_group(required=True)
    instrument.add_argument("--telescope", type=int, choices=tuple(TELESCOPES))
    instrument.add_argument("--binocular", choices=("vortex-8x42",))
    show.add_argument("--eyepiece", type=int, help="Stock focal length in mm; defaults to the widest stock eyepiece")
    show.add_argument("--barlow", type=int, choices=(1, 3), default=1)
    show.add_argument("--object", default="Moon")
    show.add_argument("--hide-landscape", action="store_true",
                      help="Hide landscape and fog for optical comparison; preserve location and time")
    prepare = commands.add_parser("scene", help="Set and freeze an observing time for repeatable comparisons")
    prepare.add_argument("--at", required=True, help="ISO 8601 date and time including its UTC offset")
    compare = commands.add_parser("tour", help="Show six complete wide-field presets without manual ocular selection")
    compare.add_argument("--object", default="Moon")
    compare.add_argument("--seconds", type=float, default=5)
    args = parser.parse_args()
    try:
        if args.command == "start":
            result = start()
        elif args.command == "status":
            result = request("main/status")
        elif args.command == "equipment":
            result = equipment()
        elif args.command == "view":
            if args.binocular:
                if args.eyepiece is not None or args.barlow != 1:
                    raise RuntimeError("Binoculars have fixed magnification; omit --eyepiece and --barlow.")
                result = binocular_view(args.object, args.hide_landscape)
            else:
                result = view(args.telescope, args.eyepiece, args.object, args.hide_landscape, args.barlow)
        elif args.command == "scene":
            result = scene(args.at)
        elif args.command == "tour":
            result = tour(args.object, args.seconds)
        elif args.command == "menu":
            result = request("stelaction/do", {"id": "actionShow_Ocular_Menu"})
        else:
            result = quit_session()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, RuntimeError, KeyError, ValueError, StopIteration, urllib.error.URLError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
