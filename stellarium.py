#!/usr/bin/env python3
"""Operate a local, password-authenticated Stellarium 24.4 session."""
import argparse
import base64
import configparser
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
    for kind in ("telescope", "ocular"):
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
        raise RuntimeError("The application's user directory is not linked to the shared config. Run link.py first.")
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


def view(telescope, eyepiece, target, hide_landscape=False):
    items = equipment()
    ti = next(i for i, t in items["telescope"].items()
              if t["name"].startswith("Sky-Watcher") and float(t["diameter"]) == telescope)
    oi = next(i for i, o in items["ocular"].items()
              if o["name"].startswith("Sky-Watcher") and float(o["efl"]) == eyepiece)
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
                        ("selectedLensIndex", -1), ("enableOcular", "true")):
        request("stelproperty/set", {"id": "Oculars." + name, "value": value})
    time.sleep(0.5)
    props = request("stelproperty/list")
    expected = {"selectedTelescopeIndex": int(ti), "selectedOcularIndex": int(oi),
                "selectedLensIndex": -1, "enableOcular": True}
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
    return {"telescope": items["telescope"][ti], "eyepiece": items["ocular"][oi],
            "live": {"Oculars." + k: props["Oculars." + k]["value"] for k in expected},
            "camera": camera,
            "target": {"name": target, "above_horizon": info.get("above-horizon"),
                       "altitude_deg": info.get("altitude")},
            "view": request("main/status")["view"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("start", "status", "equipment", "quit"):
        commands.add_parser(name)
    show = commands.add_parser("view")
    show.add_argument("--telescope", type=int, choices=(102, 127), required=True)
    show.add_argument("--eyepiece", type=int, choices=(25, 10), required=True)
    show.add_argument("--object", default="Moon")
    show.add_argument("--hide-landscape", action="store_true",
                      help="Hide landscape and fog for optical comparison; preserve location and time")
    args = parser.parse_args()
    try:
        if args.command == "start":
            result = start()
        elif args.command == "status":
            result = request("main/status")
        elif args.command == "equipment":
            result = equipment()
        elif args.command == "view":
            result = view(args.telescope, args.eyepiece, args.object, args.hide_landscape)
        else:
            result = request("scripts/direct", {"code": 'RemoteControl.setFlagAutoStart(false); RemoteControl.setPassword(""); RemoteControl.setFlagUsePassword(false); RemoteControl.saveSettings(); core.quitStellarium();'})
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, RuntimeError, KeyError, StopIteration, urllib.error.URLError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
