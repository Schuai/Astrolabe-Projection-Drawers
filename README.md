# Astrolabe Projection Drawers

Generate horizon projection SVGs with `pixi`.

## Install

This project uses `pixi` to manage Python and the project environment. The `pixi.toml` in this repository currently targets `win-64`, so the setup below is intended for Windows.

1. Install `pixi`.

   In PowerShell, run:

   ```powershell
   powershell -ExecutionPolicy Bypass -c "irm -useb https://pixi.sh/install.ps1 | iex"
   ```

   Then restart your terminal so the updated `PATH` takes effect.

2. Create the project environment.

   In this repository folder, run:

   ```powershell
   pixi install
   ```

   This reads `pixi.toml`, installs the required Python version, and creates the local project environment.

3. Run commands through `pixi`.

   You can run the scripts without manually activating anything:

   ```powershell
   pixi run draw-azimuthal-equidistant -- --help
   pixi run draw-stereographic -- --help
   ```

   `pixi run` will use the environment defined by this project. If the environment has not been installed yet, `pixi run` can install it automatically.

4. Optional: open a shell inside the project environment.

   ```powershell
   pixi shell
   ```

Official pixi docs:

- Installation: https://pixi.prefix.dev/latest/installation/
- `pixi install`: https://pixi.prefix.dev/latest/reference/cli/pixi/install/

## Azimuthal Equidistant

Use `draw_azimuthal_equidistant.py` through the `draw-azimuthal-equidistant` task:

```powershell
pixi run draw-azimuthal-equidistant -- @(
  "--latitude", "49.86667",
  "--center", "north",
  "--range-latitude", "-55",
  "--diameter", "40",
  "--azimuth-lines", "12",
  "--altitude-lines", "5",
  "--boundary-width", "0.1",
  "--horizon-width", "0.2",
  "--azimuth-width", "0.1",
  "--altitude-width", "0.1",
  "--civil-twilight",
  "--nautical-twilight",
  "--astronomical-twilight",
  "--twilight-width", "0.15",
  "--twilight-style", "dashed",
  "--equator-tropics",
  "--equator-tropics-width", "0.12",
  "--azimuth-labels",
  "--azimuth-label-size", "0.8",
  "--azimuth-label-width", "0.15",
  "--azimuth-label-position", "0.35",
  "--azimuth-label-center-adjust", "0.0",
  "--azimuth-label-letter-spacing", "0.6",
  "--crosshair",
  "--crosshair-horizontal-width", "0.1",
  "--crosshair-vertical-width", "0.15",
  "--output", "sample.svg"
)
```

## Notes

- `--range-latitude -55` means `55S`.
- `--diameter` is in millimeters.
- The exported SVG adds an automatic outer margin so thick strokes and labels are not clipped.
- The sky region appears above the image by default, for both north-centered and south-centered output.
- Use `--rotate-180` to rotate the projection 180 degrees and place the sky region below the image.
- `--boundary-width` sets the outer boundary line width in millimeters.
- `--horizon-width` sets the horizon line width in millimeters.
- `--azimuth-width` sets the azimuth line width in millimeters.
- `--altitude-width` sets the altitude line width in millimeters.
- `--civil-twilight` draws the `-6 degree` twilight line.
- `--nautical-twilight` draws the `-12 degree` twilight line.
- `--astronomical-twilight` draws the `-18 degree` twilight line.
- `--twilight-width` sets the shared twilight line width in millimeters.
- `--twilight-style` sets twilight lines to `solid` or `dashed`.
- `--astronomical-twilight-width` is kept as a legacy fallback when `--twilight-width` is not set.
- `--equator-tropics` draws the celestial equator and the northern/southern tropic lines.
- `--equator-tropics-width` sets the shared line width for those three lines in millimeters.
- The tropic declination is fixed at `23.4392911111` degrees.
- `--azimuth-labels` adds `N, NE, E, SE, S, SW, W, NW` between the horizon and the astronomical twilight line.
- `--azimuth-label-size` sets the label font size in millimeters.
- `--azimuth-label-width` sets the label stroke width in millimeters.
- `--azimuth-label-position` sets where the label sits between horizon and astronomical twilight: `0` is on the horizon, `1` is on the astronomical twilight line.
- `--azimuth-label-center-adjust` nudges labels along the local tangent in millimeters. Use positive or negative values if they look visually left- or right-shifted.
- `--azimuth-label-letter-spacing` sets the spacing between glyphs in millimeters.
- Azimuth labels are drawn with built-in vector sans-serif glyphs, so they do not depend on installed fonts.
- `--crosshair` draws horizontal and vertical center lines across the whole projection.
- `--crosshair-width` sets the fallback line width for both crosshair lines in millimeters when neither axis-specific width is set.
- `--crosshair-horizontal-width` sets the horizontal crosshair line width in millimeters.
- `--crosshair-vertical-width` sets the vertical crosshair line width in millimeters.
- If only one axis-specific crosshair width is set, the other axis defaults to `0` and is not drawn.

## Stereographic

Use `draw_stereographic.py` through the `draw-stereographic` task. It accepts the same arguments as the azimuthal-equidistant drawer:

```powershell
pixi run draw-stereographic -- @(
  "--latitude", "49.86667",
  "--center", "north",
  "--range-latitude", "-23.5",
  "--diameter", "40",
  "--azimuth-lines", "12",
  "--altitude-lines", "5",
  "--boundary-width", "0.1",
  "--horizon-width", "0.2",
  "--azimuth-width", "0.1",
  "--altitude-width", "0.1",
  "--civil-twilight",
  "--nautical-twilight",
  "--astronomical-twilight",
  "--twilight-width", "0.15",
  "--twilight-style", "dashed",
  "--equator-tropics",
  "--equator-tropics-width", "0.12",
  "--azimuth-labels",
  "--azimuth-label-size", "0.8",
  "--azimuth-label-width", "0.15",
  "--azimuth-label-position", "0.35",
  "--azimuth-label-center-adjust", "0.0",
  "--azimuth-label-letter-spacing", "0.6",
  "--crosshair",
  "--crosshair-horizontal-width", "0.1",
  "--crosshair-vertical-width", "0.15",
  "--output", "stereographic.svg"
)
```

- `draw_stereographic.py` keeps the same CLI as `draw_azimuthal_equidistant.py`.
- In stereographic projection, the antipodal pole diverges to infinity, so `--range-latitude` cannot be the opposite pole itself.
