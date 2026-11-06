#!/usr/bin/env python3
"""Capture a local, reproducible stock-optics atlas from the running Stellarium."""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import zlib

import stellarium as st

ROOT = Path(__file__).resolve().parent
TARGETS = json.loads((ROOT / "atlas_targets.json").read_text())
INSTRUMENTS = [
    {"id":"vortex","name":"Vortex 8×42","kind":"Binocular","aperture":42},
    {"id":"power70","name":"PowerSeeker 70EQ","kind":"Refractor","aperture":70,"telescope":70,"mount":"Equatorial mount"},
    {"id":"mak102","name":"MAK 102","kind":"Maksutov","aperture":102,"telescope":102,"mount":"AZ Pronto + tripod","shortlist":True},
    {"id":"mak127","name":"MAK 127","kind":"Maksutov","aperture":127,"telescope":127,"mount":"AZ5 + tripod","shortlist":True},
    {"id":"explorer130","name":"Explorer 130PS","kind":"Newtonian","aperture":130,"telescope":"explorer130","mount":"AZ5 + tripod","shortlist":True},
    {"id":"startravel102","name":"Startravel 102","kind":"Achromat","aperture":102,"telescope":"startravel102","mount":"AZ Pronto + tripod","shortlist":True},
    {"id":"heritage130","name":"Heritage 130P","kind":"Dobsonian","aperture":130,"telescope":130,"mount":"Tabletop Dobsonian"},
    {"id":"heritage150","name":"Heritage 150P","kind":"Dobsonian","aperture":150,"telescope":150,"mount":"Tabletop Dobsonian"},
]
PLANNER = json.loads((ROOT / "eyepieces.json").read_text())
UPGRADES = {"upgrade_"+p["id"]:p for p in PLANNER["eyepieces"]}

REDUCERS = {"reducer063": .63, "reducer050": .5}


def cohorts_for(instrument, object_id=None):
    if instrument["id"] == "vortex":
        return ("fixed",)
    base = ("wide", "second", *REDUCERS) if instrument["id"] in ("mak102", "mak127") else ("wide", "second")
    return (*base, *UPGRADES) if instrument["id"] == "mak102" and object_id in PLANNER["capture_objects"] else base


RENDER_PROFILE = "clean-circle-v2"
PROPERTIES = {
    "LandscapeMgr.flagUseLightPollutionFromDatabase":False,
    "LandscapeMgr.atmosphereDisplayed":True,
    "LandscapeMgr.landscapeDisplayed":True,
    "LandscapeMgr.fogDisplayed":False,
    "StelCore.currentTimeZone":"Europe/Warsaw",
    "Oculars.flagScaleImageCircle":False,
    "Oculars.flagGuiPanelEnabled":True,
    "Oculars.enableCrosshairs":False,
    "StelGui.visible":False,
    "StarMgr.flagLabelsDisplayed":False,
    "StelSkyDrawer.flagStarTwinkle":False,
    "StelObjectMgr.objectPointerVisibility":False,
    "SolarSystem.flagPointer":False,
    "SolarSystem.labelsDisplayed":False,
    "SolarSystem.flagMoonScale":False,
    "SolarSystem.flagPlanetScale":False,
    "SolarSystem.flagSunScale":False,
    "NebulaMgr.flagHintDisplayed":False,
    "NebulaMgr.flagDesignationLabels":False,
}


def set_property(name, value):
    st.request("stelproperty/set", {"id":name,"value":str(value).lower() if isinstance(value,bool) else value})


def info(name):
    return st.request("objects/info?" + st.urllib.parse.urlencode({"name":name,"format":"json"}))


def environment(output):
    properties = st.request("stelproperty/list")
    missing = set(PROPERTIES) - properties.keys()
    if missing:
        raise RuntimeError(f"Missing renderer properties: {sorted(missing)}")
    original = {key:properties[key]["value"] for key in PROPERTIES}
    original["_minimum_fps"]=native_state()["minimum_fps"]
    (output / "session-before.json").write_text(json.dumps({"properties":original,"status":st.request("main/status")},indent=2))
    st.request("location/setlocationfields", {"latitude":52.23,"longitude":21.01,"altitude":100,"name":"Warsaw","country":"Poland","planet":"Earth"})
    for key,value in PROPERTIES.items():
        set_property(key,value)
    st.request("main/window", {"w":768,"h":768})
    st.request("scripts/direct", {"code":'core.setSelectedObjectInfo("None"); core.setMinFps(30);'})
    time.sleep(1)
    status = st.request("main/status")
    assert abs(status["location"]["latitude"]-52.23)<0.001
    assert abs(status["location"]["longitude"]-21.01)<0.001
    return original


def native_state(code=""):
    state_file = st.CONFIG / "atlas-state.txt"
    before = state_file.stat().st_mtime_ns if state_file.exists() else 0
    code += 'core.output("ATLAS_STATE " + JSON.stringify({bortle:core.getBortleScaleIndex(),minimum_fps:core.getMinFps()})); core.saveOutputAs("atlas-state.txt");'
    st.request("scripts/direct", {"code":code})
    for _ in range(40):
        if state_file.exists() and state_file.stat().st_mtime_ns != before:
            lines=state_file.read_text().splitlines()
            markers=[line.split("ATLAS_STATE ",1)[1] for line in lines if "ATLAS_STATE " in line]
            if markers:
                value=json.loads(markers[-1])
                return value
        time.sleep(0.1)
    raise RuntimeError("Could not verify native renderer state")


def set_bortle(index):
    # Use the installed application's own conversion, not a hand-made sky tint.
    value=native_state(f'core.setBortleScaleIndex({index});')
    if value["bortle"]!=index:
        raise RuntimeError("Stellarium did not apply the requested Bortle class")
    return st.request("stelproperty/list")["StelSkyDrawer.lightPollutionLuminance"]["value"]


def altitude_is_current(obj, status):
    # The HTTP object service can briefly read a previous-frame transform after
    # a large date jump. Cross-check the geometric altitude against current JD.
    jd=status["time"]["jday"];t=(jd-2451545)/36525
    sidereal=(280.46061837+360.98564736629*(jd-2451545)+0.000387933*t*t-t*t*t/38710000+status["location"]["longitude"])%360
    latitude=math.radians(status["location"]["latitude"])
    dec=math.radians(obj["dec"]);hour_angle=math.radians(sidereal-obj["ra"])
    altitude=math.degrees(math.asin(math.sin(latitude)*math.sin(dec)+math.cos(latitude)*math.cos(dec)*math.cos(hour_angle)))
    return abs(altitude-obj["altitude-geometric"])<0.2


def scene(target):
    # macOS can throttle an occluded native OpenGL window between scenes.
    if sys.platform == "darwin":
        subprocess.run(["open", "-a", "Stellarium"], check=True)
        time.sleep(0.3)
    st.scene(target["at"])
    for attempt in range(50):
        obj, sun, moon = info(target["target"]),info("Sun"),info("Moon")
        status=st.request("main/status")
        if all(altitude_is_current(o,status) for o in (obj,sun,moon)):
            break
        if attempt==0:print("Waiting for the new-date coordinate transform",flush=True)
        time.sleep(0.3)
    else:
        raise RuntimeError("The date changed but the coordinate transform did not settle")
    if not obj.get("found") or obj["altitude"]<15:
        raise RuntimeError(f'{target["name"]} is too low in the planned scene: {obj.get("altitude")}')
    return {"at":target["at"],"target_altitude_deg":obj["altitude"],"sun_altitude_deg":sun["altitude"],
            "moon_altitude_deg":moon["altitude"],"moon_illumination_percent":moon.get("illumination"),
            "target_angular_diameter_deg":obj.get("size-dd"),"target_phase":obj.get("phase-name"),
            "target_magnitude":obj.get("vmag"),"target_illumination_percent":obj.get("illumination"),"utc":st.request("main/status")["time"]["utc"]}


def inspect_png(data):
    """Reject incomplete asynchronous PNG writes, even if file size paused."""
    if data[:8]!=b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG signature")
    offset=8;dimensions=None
    while offset+12<=len(data):
        size=struct.unpack(">I",data[offset:offset+4])[0]
        end=offset+12+size
        if end>len(data):raise ValueError("PNG write is incomplete")
        kind=data[offset+4:offset+8];payload=data[offset+8:offset+8+size]
        checksum=struct.unpack(">I",data[offset+8+size:end])[0]
        if zlib.crc32(kind+payload)&0xffffffff!=checksum:raise ValueError("PNG checksum mismatch")
        if kind==b"IHDR":dimensions=struct.unpack(">II",payload[:8])
        if kind==b"IEND":
            if end!=len(data) or dimensions is None:raise ValueError("Invalid PNG termination")
            return dimensions
        offset=end
    raise ValueError("PNG end marker has not been written")


def capture(prefix, destination):
    screenshot_dir = Path.home()/"Pictures/Stellarium"
    source = screenshot_dir/(prefix+".png")
    before = source.stat().st_mtime_ns if source.exists() else 0
    st.request("scripts/direct", {"code":f'core.screenshot({json.dumps(prefix)}, false, "", true, "png");'})
    previous_size = None
    for _ in range(100):
        if source.exists() and source.stat().st_mtime_ns != before:
            size=source.stat().st_size
            if size>100 and size==previous_size:
                data=source.read_bytes()
                try:width,height=inspect_png(data)
                except ValueError:
                    time.sleep(0.1)
                    continue
                if width!=height:
                    raise RuntimeError(f"Capture viewport is not square: {width}x{height}")
                shutil.move(str(source),str(destination))
                return {"width":width,"height":height,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
            previous_size=size
        time.sleep(0.1)
    raise RuntimeError(f"Screenshot did not finish: {source}")


def write_manifest(output, manifest):
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
    (output/"data.js").write_text("window.ATLAS_DATA = "+json.dumps(manifest,ensure_ascii=False)+";\n")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"gallery")
    parser.add_argument("--only",nargs="*",choices=[o["id"] for o in TARGETS])
    parser.add_argument("--bortle",nargs="+",type=int,choices=(4,5),default=[4,5])
    parser.add_argument("--plan-only",action="store_true")
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--settle",type=float,default=1.2)
    args=parser.parse_args()
    output=args.output.expanduser().resolve();output.mkdir(parents=True,exist_ok=True);(output/"images").mkdir(exist_ok=True)
    targets=[o for o in TARGETS if not args.only or o["id"] in args.only]
    previous=json.loads((output/"manifest.json").read_text()) if args.resume and (output/"manifest.json").exists() else None
    manifest=previous or {"title":"The eyepiece atlas","created_by":"Codex","created_at":datetime.now().astimezone().isoformat(),
        "location":{"name":"Warsaw, Poland","latitude":52.23,"longitude":21.01,"altitude_m":100,"note":"Representative city coordinates, not a measured observing-site address."},
        "version":"Stellarium 24.4.0","instruments":INSTRUMENTS,"objects":TARGETS,"captures":[],"scenes":{},
        "comparison":"Two stock-eyepiece cohorts, not equal magnifications. Barlow disabled. Fixed binocular reference.",
        "limitations":["Framing and angular scale, not a prediction of visual contrast, color, seeing or eyepiece aberrations.",
            "Bortle 4 and 5 are user-supplied observing scenarios, not measured Warsaw city-center conditions.",
            "Nebula and galaxy photo textures are illustrative; do not infer that the same structure will be visible by eye.",
            "PowerSeeker 70EQ identification and Vortex 8x42 size are provisional; PowerSeeker 4 mm apparent field is estimated at 30 degrees.",
            "Each object has its own disclosed date; all instruments and Bortle variants for that object share the same scene."]}
    manifest["instruments"]=[dict(instrument) for instrument in INSTRUMENTS]
    manifest["objects"]=TARGETS
    manifest["eyepiece_planner"]=PLANNER
    manifest["comparison"]="Two stock-eyepiece cohorts plus idealized MAK reducer rows; Barlow disabled. Fixed binocular reference."
    reducer_note="MAK 0.63x/0.5x reducer rows show nominal geometry only. Hardware compatibility, back focus, vignetting and field illumination are unverified. The Celestron SCT 0.63x reducer is not compatible with Maksutov tubes."
    photo_note="Startravel Photo 20/10 mm apparent fields are assumed at 50 degrees; exact field framing needs confirmation. Explorer 130PS and Heritage 130P share nominal 130/650 optics; mount ergonomics are not simulated."
    manifest["limitations"]=[note for note in manifest["limitations"] if not note.startswith(("MAK 0.63x/0.5x", "Startravel Photo"))]+[reducer_note,photo_note]
    equipment=st.equipment()
    for instrument in manifest["instruments"]:
        kind="ocular" if instrument["id"]=="vortex" else "telescope"
        name=st.BINOCULAR if kind=="ocular" else st.TELESCOPES[instrument["telescope"]]
        record=next(x for x in equipment[kind].values() if st.profile_name(x)==name)
        instrument["owned"]=record["name"].startswith("[Existing]")
    original=environment(output)
    try:
        for target in targets:
            print(f'Planning {target["name"]}',flush=True)
            metadata=scene(target);manifest["scenes"][target["id"]]=metadata
            print(json.dumps(metadata),flush=True)
            write_manifest(output,manifest)
            if args.plan_only:
                continue
            for bortle in args.bortle:
                luminance=set_bortle(bortle)
                for instrument in INSTRUMENTS:
                    cohorts=cohorts_for(instrument,target["id"])
                    for cohort in cohorts:
                        key=f'{target["id"]}-b{bortle}-{instrument["id"]}-{cohort}'
                        destination=output/"images"/(key+".png")
                        old=next((c for c in manifest["captures"] if c["id"]==key),None)
                        reducer=REDUCERS.get(cohort,1)
                        if args.resume and old and old.get("render_profile")==RENDER_PROFILE and old["scene"]["at"]==target["at"] and old.get("reducer",1)==reducer and destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest()==old["sha256"]:
                            continue
                        if instrument["id"]=="vortex":
                            state=st.binocular_view(target["target"],freeze_camera=True);eyepiece=None
                        else:
                            telescope=instrument["telescope"]
                            product=UPGRADES.get(cohort)
                            eyepiece=product["focal_mm"] if product else st.stock_eyepieces(telescope)[1 if cohort=="second" else 0]
                            state=st.view(telescope,eyepiece,target["target"],freeze_camera=True,reducer=reducer,upgrade=product["id"] if product else None)
                        # Oculars resets several settings when changing a preset.
                        set_property("StelObjectMgr.objectPointerVisibility",False)
                        time.sleep(args.settle)
                        current=st.request("stelproperty/list")
                        if not math.isclose(current["StelSkyDrawer.lightPollutionLuminance"]["value"],luminance,rel_tol=1e-5):
                            raise RuntimeError("Bortle luminance changed during capture")
                        for property_name,expected_value in state["live"].items():
                            if current[property_name]["value"]!=expected_value:
                                raise RuntimeError("An optical selection changed during capture")
                        live_status=st.request("main/status")
                        if live_status["time"]["utc"]!=metadata["utc"] or live_status["time"]["timerate"]!=0:
                            raise RuntimeError("The observing scene changed during capture")
                        live_fov=st.request("main/status")["view"]["fov"]
                        if not math.isclose(live_fov,state["field_of_view_deg"],rel_tol=1e-5):
                            raise RuntimeError("The capture circle is not normalized to the actual optical field")
                        camera=st.request("main/view")
                        vector=json.loads(camera["j2000"])
                        if len(vector)!=3 or not all(math.isfinite(x) for x in vector):
                            raise RuntimeError("The rendered camera became invalid before capture")
                        state["camera"]=camera
                        file_metadata=capture("atlas-"+key,destination)
                        if st.request("main/view")!=camera:
                            raise RuntimeError("The camera changed while rendering the screenshot")
                        record={"id":key,"object":target["id"],"bortle":bortle,"instrument":instrument["id"],"cohort":cohort,
                            "eyepiece_mm":eyepiece,"reducer":reducer,"magnification":state["magnification"],"field_of_view_deg":state["field_of_view_deg"],
                            "render_profile":RENDER_PROFILE,"light_pollution_cd_m2":luminance,"image":"images/"+destination.name,"live":state["live"],
                            "camera":state["camera"],"scene":metadata,**file_metadata}
                        if old:manifest["captures"].remove(old)
                        manifest["captures"].append(record);write_manifest(output,manifest)
                        print(f'Captured {key}: {state["magnification"]:g}x, {state["field_of_view_deg"]:.3f} deg ({len(manifest["captures"])} images)',flush=True)
        for path in (ROOT/"web").iterdir():
            if path.is_file():shutil.copy2(path,output/path.name)
        write_manifest(output,manifest)
    finally:
        # Leave the requested Warsaw/Bortle scenario but restore viewing controls.
        for key,value in original.items():
            if key not in ("StelCore.currentTimeZone","_minimum_fps"):set_property(key,value)
        st.request("scripts/direct", {"code":f'StelMovementMgr.setInhibitAllAutomoves(false); core.setMinFps({original["_minimum_fps"]});'})
        (st.CONFIG/"atlas-state.txt").unlink(missing_ok=True)
    print(("Plan verified" if args.plan_only else f'Atlas ready: {output/"index.html"}'),flush=True)


if __name__=="__main__":
    main()
