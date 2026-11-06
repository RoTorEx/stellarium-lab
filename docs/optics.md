# Optical comparison guide

The on-screen Ocular, Telescope and Lens controls describe one optical system.
They are not three alternative ways to select an instrument.

- **Telescope:** aperture and focal length of the main instrument. Aperture
  governs light gathering and potential resolving power. Focal length combines
  with an eyepiece to determine magnification.
- **Ocular / eyepiece:** the interchangeable viewing eyepiece. Its millimetre
  value is its focal length, not its aperture. With the stock pairs in this
  workflow, the longer eyepiece gives the wider view and lower magnification.
- **Lens:** an optional Barlow or focal reducer. `None` is the normal baseline
  and still includes the selected eyepiece. The PowerSeeker's 3x Barlow triples
  magnification and narrows the field; it is disabled in wide-field presets.
- **Binocular:** a complete fixed system stored in Stellarium's ocular list.
  Vortex 8x42 means 8x magnification and 42 mm objectives. In binocular mode,
  Stellarium ignores the separate telescope. The helper also clears the lens.
- **EQ / Dobsonian:** mount types for pointing and tracking, not magnification.
  This workflow does not connect to or drive a physical mount.

Magnification = telescope focal length / eyepiece focal length x Barlow factor.
For example, MAK 102 has a 1300 mm focal length: 1300 / 25 = 52x; with 10 mm it
becomes 130x. Its 102 mm aperture is a different measurement.

## Wide-field presets

These are calculated from the active optical profiles, using Stellarium 24.4's
field-stop formula where a field stop is supplied, otherwise apparent field /
magnification. The inherited Sky-Watcher field stops remain unmeasured user
values, so the figures are simulated framing, not a fresh optical calibration.

| Complete system | Eyepiece | Magnification | Field diameter |
| --- | --- | --- | --- |
| Vortex Diamondback 8x42 | Fixed | 8x | 7.50 degrees |
| PowerSeeker 70EQ, provisional identification | 20 mm | 35x | 1.43 degrees |
| MAK 102/1300 | Super 25 mm | 52x | 0.97 degrees |
| MAK 127/1500 | Super 25 mm | 60x | 0.84 degrees |
| Heritage 130P | Super 25 mm | 26x | 1.94 degrees |
| Heritage 150P | Super 25 mm | 30x | 1.68 degrees |

The [Vortex specification](https://vortexoptics.com/vortex-diamondback-8x42-binocular.html)
confirms 8x, 42 mm and 7.5 degrees. The user's recalled 8x42 identification has
not been checked against a physical label. HD/non-HD generation is unresolved;
this profile makes no claims about transmission, coatings or contrast.

## What the framing implies

**Moon:** its roughly half-degree disk fits in all six wide presets. The MAKs
make it larger in the eyepiece while still showing the entire disk. Switching
to 10 mm gives 130x/150x for a closer view of lunar features, with less surrounding
sky and potentially part of the disk outside the field. Real detail depends on
seeing, instrument temperature, alignment and optical quality.

**Pleiades:** Stellarium's M45 catalog size is about 1.83 degrees. Vortex includes
ample context. Heritage 130P's nominal field is just wider than that catalog
extent; Heritage 150P can clip its outer region. The MAK wide presets show
sections of the cluster rather than the entire extent. This is a framing
inference from the stored fields; cluster boundaries are not a sharp edge.

**Jupiter and Saturn:** they are much smaller than the Moon. The wide presets
are useful for finding them but do not maximize their apparent size. Existing
10 mm eyepieces yield 130x/150x in the MAKs and 65x/75x in the Heritage scopes.
That gives the MAK stock kits a larger planetary image at these particular
eyepieces; it does not prove better optics or a higher ultimate resolution than
the larger Heritage apertures. Barlow magnification alone does not add detail.

Vortex is well suited to a wide cluster view and a small lunar disk, rather
than resolving planetary surface detail. Jupiter's moons can sometimes be
spotted with practice and a steady view; Saturn's rings are not a realistic
expectation at 8x. See [NASA's binocular observing guide](https://science.nasa.gov/solar-system/skywatching/night-sky-network/binoculars-a-great-first-telescope/).
For aperture, magnification and seeing limits, see the
[Sky-Watcher FAQ](https://www.skywatcher.com/faq/).

Stellarium establishes scale, orientation and framing. Bright photographic
nebula textures, rendered contrast and a clean image do not predict the view
through an actual eyepiece under a particular sky.

## Selecting complete systems

`[Existing]` means owned equipment, `[Compare]` means candidates under
consideration, and `[Legacy]` preserves older custom records that are not
confirmed inventory. Each group is contiguous: owned first, candidates next,
then legacy records and shipped examples. `[Built-in]` marks entries whose
names match Stellarium 24.4's shipped examples; it does not mean hardware was
discovered or connected, or that every example is unmodified.
No old instrument was deleted or had its optical values changed by grouping.

**Alt+O (Option+O on macOS)** opens the native popup with selection lists.
Alternatively run `python3 stellarium.py menu`. Binocular mode intentionally
hides the telescope and lens submenus; switch back to a normal ocular to show
them again. For a complete telescope/stock-eyepiece pair, use `view` rather than
manually selecting two unrelated components.

```sh
python3 stellarium.py view --binocular vortex-8x42 --object Moon
python3 stellarium.py view --telescope 102 --object Moon
python3 stellarium.py tour --object Moon --seconds 5
```

The tour follows the grouped preset order: Vortex, PowerSeeker, MAK 102,
MAK 127, Heritage 130P, Heritage 150P. Every telescope uses its widest stock eyepiece; all lenses are
disabled. It leaves the last view open. Use `--seconds 0` for scripted checks.
Progress goes to stderr and the complete results are returned as JSON on stdout.
For an identical lunar demonstration:

```sh
python3 stellarium.py scene --at 2026-11-18T18:00:00+01:00
python3 stellarium.py tour --object Moon --seconds 5
```

That is an explicitly simulated date at 18:00 Warsaw (CET, UTC+01:00), with the
existing observer location preserved. It is not a statement about the current
real-time lunar visibility.
