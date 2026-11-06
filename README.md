# Stellarium Lab

A personal **Agent Workflow** for controlling Stellarium and comparing simulated
views through Sky-Watcher Maksutov telescopes and their existing stock eyepieces.
VS Code Project Manager lists this repository as **Space · Stellarium Lab**.

The shared application configuration belongs to the separate `RoTorEx/config`
repository at `Development/config/dotfiles/stellarium/`. This project owns the
workflow and API helper, not a second copy of the application state.

For the meaning of Telescope/Ocular/Lens, the Vortex binocular, grouped device
lists, and Moon/Pleiades/planet comparisons, read the [optical guide](docs/optics.md).
`view` selects a complete stock combination; `tour --object Moon` displays all
six wide-field presets in turn. **Alt/Option+O** opens Stellarium's native
selection menu. Owned `[Existing]` instruments form the first block,
`[Compare]` candidates follow as one block, then `[Legacy]` and `[Built-in]`.

## Setup and operation

Keep this checkout at `Development/personal/projects/space/stellarium-lab` beside
the existing Development/config checkout. Install Stellarium, quit it, and
install the configuration link with the system Bash. Linking needs no Python or
virtual environment. The API commands below require Python 3's standard library:

```sh
bash ../../../../config/dotfiles/stellarium/link.sh
python3 stellarium.py equipment
python3 stellarium.py start
python3 stellarium.py view --telescope 102 --eyepiece 25 --object Moon
python3 stellarium.py view --telescope 127 --eyepiece 10 --object Moon
python3 stellarium.py status
python3 stellarium.py quit
```

`start` launches the macOS app and establishes a password-authenticated session
at `http://127.0.0.1:8090`. The password and temporary startup script remain in
ignored `.local/` with restricted permissions. It refuses to launch over an
existing Stellarium process. HTTP commands use only Python's standard library.
No MCP server or paid API is required. Automatic launch was implemented for
macOS; other operating systems need their own equivalent app-launch command.

Stellarium 24.4's server listens on network interfaces, and uses HTTP Basic auth
without TLS. Use it on a trusted local machine/network; do not forward port 8090
to the internet. The shared config keeps server autostart disabled. `quit` clears
the session password in Stellarium's settings before quitting. If you use the
app's Save Settings button during a session, use this command before committing
configuration and verify the password is empty. Never commit `.local/`.

The `view` command preserves the observer location, time, ground and atmosphere
settings. It uses an immediate camera direction rather than overlapping animated
focus and ocular transitions, then verifies the applied equipment and camera.
An object below the horizon can be invisible. Choose an object above the horizon
or explicitly ask the agent to set a different observing date/time. The workflow
does not silently change observing conditions to make a target visible.
For an optical comparison obscured by landscape scenery, use `--hide-landscape`
to hide ground and fog explicitly. This changes only those display layers;
restore them with Stellarium's G/F controls or restart without saving settings.

## Equipment

The two MAK profiles and Super 25/10 mm eyepieces were preserved from the
original configuration. The Heritage profiles and PowerSeeker stock eyepieces
were added without replacing existing instruments, including the Bresser Dobson.
The PowerSeeker identification is provisional until its model label is checked.

| Telescope | Aperture / focal length | Stock eyepieces | Magnification |
| --- | --- | --- | --- |
| PowerSeeker 70EQ (unconfirmed model) | 70 / 700 mm | 20 mm, 4 mm | 35×, 175× |
| Sky-Watcher MAK 102 | 102 / 1300 mm | 25 mm, 10 mm | 52×, 130× |
| Sky-Watcher MAK 127 | 127 / 1500 mm | 25 mm, 10 mm | 60×, 150× |
| Sky-Watcher Heritage 130P | 130 / 650 mm | 25 mm, 10 mm | 26×, 65× |
| Sky-Watcher Heritage 150P | 150 / 750 mm | 25 mm, 10 mm | 30×, 75× |

Manufacturer references: [PowerSeeker 70EQ](https://www.celestron.com/products/powerseeker-70eq-telescope/),
[Heritage 130P](https://www.skywatcher.com/product/heritage-p130/),
[Heritage 150P](https://www.skywatcherusa.com/products/heritage-150-tabletop-dobsonian),
and the [Sky-Watcher Dobsonian catalog](https://www.skywatcher.com.tw/upload_attach/1686918808.pdf).
PowerSeeker includes a 3× Barlow: use `--barlow 3` for 105× or 525× framing.
Those are mathematical magnifications, not a claim of useful image quality.
The existing generic 3× lens entry supplies that multiplier without duplication.

PowerSeeker 20 mm uses a nominal 50° apparent field, consistent with the
[series manual](https://s3.amazonaws.com/celestron-site-support-files/support_files/1245780194_powerseekerinst.pdf).
The 4 mm apparent field is not specified there: **30° is an explicit placeholder**,
visible in its Oculars name. Its field framing is approximate until measured or
confirmed. No field stops are invented for the added eyepieces. The PowerSeeker
uses an equatorial mount and erect-image diagonal; Heritage uses an alt-az mount
and a conventional 180° inverted Newtonian view. Actual eyepiece orientation can
vary with focuser and observer position.

The existing Super 25 mm profile uses 50° apparent field and a 22 mm field stop;
Super 10 mm uses 52° and 9 mm. These field-stop values are preserved user data,
not newly measured specifications. The
[Sky-Watcher distributor catalog](https://www.opticalvision.co.uk/user/Optical-Vision-Catalogue-2020.pdf)
lists Super-MA apparent fields of 50° (25 mm) and 52° (10 mm). Regional telescope
bundles vary; the [manufacturer's MAK127 listing](https://skywatcher.com/product/bk-mak127-eq3/)
also shows a 28 mm bundle. This workflow uses the existing Super 25/10 mm pair,
not a claim that every current kit contains those eyepieces.

Use the real eyepiece markings or the exact kit listing before substituting a
different bundle. The inherited alt-az and image-orientation settings remain
unchanged. Stellarium simulates framing and magnification; seeing, contrast,
eyepiece aberrations and a physical mount connection are outside this workflow.

## Compare the Pleiades

Use a single paused observing time so the target stays in the same scene. The
example is 2026-11-06 at 21:00 Warsaw (CET, UTC+01:00). It preserves the existing
observer location; Stellarium can display a different local clock for that place.
`scene` verifies the resulting Julian date and paused timerate through the API.

```sh
python3 stellarium.py start
python3 stellarium.py scene --at 2026-11-06T21:00:00+01:00
python3 stellarium.py view --telescope 70 --object M45
python3 stellarium.py view --telescope 102 --object M45
python3 stellarium.py view --telescope 127 --object M45
python3 stellarium.py view --telescope 130 --object M45
python3 stellarium.py view --telescope 150 --object M45
python3 stellarium.py view --telescope 70 --eyepiece 4 --barlow 3 --object M45
```

Omitting `--eyepiece` selects the widest stock eyepiece: 20 mm for PowerSeeker,
25 mm for the Sky-Watcher models. Choose the other stock eyepiece explicitly.
The telescope selector uses aperture identifiers, with an exact model-name
lookup so Heritage 150P cannot accidentally select the existing Bresser 150/750.
These examples are sequential alternatives; leave the desired view selected.

## Verified on this Mac

- Stellarium **24.4.0** reads its user directory through the installed symlink.
- All 58 original files were copied and SHA-256 compared before configuration
  edits. Logs/output stay local; all other imported user files are tracked.
- Both stock eyepieces for all five telescopes and both PowerSeeker 3× Barlow
  combinations were exercised on M45: 12 combinations, with equipment indices,
  camera direction, and the target above the horizon checked through the API.
  The earlier MAK setup was also exercised on the Moon, Saturn and Polaris.
- Telescope and eyepiece selections persisted through a clean quit/restart.
- Grouped profiles were reindexed with all old optical fields and current
  selections preserved by identity. Five telescope presets, 12 stock telescope
  combinations and the Vortex 8x42 binocular were exercised after migration.
- The binocular's field remained unchanged when the hidden telescope changed.
- `quit` now waits for the macOS process to finish writing configuration before
  returning, preventing a later exit write from overwriting offline edits.
- Authenticated reads worked; unauthenticated requests received HTTP 401.
- The installer was checked for backup preservation, repeat invocation, and
  refusal to replace an unrelated link. The config repository's required
  `make check` passed (19 tests) outside the macOS sandbox.

Only this Mac and this installed version have been exercised. Another computer
still requires cloning both repositories and running the link installer.

API reference: [Stellarium 24.4 RemoteControl API](https://stellarium.org/doc/24.0/remoteControlApi.html).
