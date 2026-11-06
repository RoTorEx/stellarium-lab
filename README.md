# Stellarium Lab

A personal **Agent Workflow** for controlling Stellarium and comparing simulated
views through Sky-Watcher Maksutov telescopes and their existing stock eyepieces.
VS Code Project Manager lists this repository as **Space · Stellarium Lab**.

The shared application configuration belongs to the separate `RoTorEx/config`
repository at `Development/config/dotfiles/stellarium/`. This project owns the
workflow and API helper, not a second copy of the application state.

## Setup and operation

Keep this checkout at `Development/personal/projects/space/stellarium-lab` beside
the existing Development/config checkout. Install Python 3 and Stellarium, then
quit Stellarium and install the configuration link:

```sh
python3 ../../../../config/dotfiles/stellarium/link.py
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

These profiles already existed in the imported Oculars configuration. Both MAK
profiles and both eyepieces were retained without duplication. The nominal
combinations, without a Barlow or reducer, are:

| Telescope | Aperture / focal length | 25 mm | 10 mm |
| --- | --- | --- | --- |
| Sky-Watcher MAK 102 | 102 / 1300 mm | 52× | 130× |
| Sky-Watcher MAK 127 | 127 / 1500 mm | 60× | 150× |

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

## Verified on this Mac

- Stellarium **24.4.0** reads its user directory through the installed symlink.
- All 58 original files were copied and SHA-256 compared before configuration
  edits. Logs/output stay local; all other imported user files are tracked.
- All four MAK/eyepiece combinations were selected through the live API, with
  ocular mode enabled and no Barlow/reducer. Camera directions were also
  checked; Saturn above the horizon was used for the final visual check.
- Telescope and eyepiece selections persisted through a clean quit/restart.
- Authenticated reads worked; unauthenticated requests received HTTP 401.
- The installer was checked for backup preservation, repeat invocation, and
  refusal to replace an unrelated link. The config repository's required
  `make check` passed (19 tests) outside the macOS sandbox.

Only this Mac and this installed version have been exercised. Another computer
still requires cloning both repositories and running the link installer.

API reference: [Stellarium 24.4 RemoteControl API](https://stellarium.org/doc/24.0/remoteControlApi.html).
