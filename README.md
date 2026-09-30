# Astrolabe Projection Drawers

Generate horizon projection SVGs with `pixi`.

## Setup

This project uses `pixi` to manage Python and the project environment. The `pixi.toml` in this repository currently targets `win-64`, so the setup below is intended for Windows.

1. Clone this repository and enter the project directory.

   In PowerShell, run:

   ```powershell
   git clone https://github.com/Schuai/Astrolabe-Projection-Drawers.git
   cd programs
   ```

2. Install `pixi`.

   In PowerShell, run:

   ```powershell
   powershell -ExecutionPolicy Bypass -c "irm -useb https://pixi.sh/install.ps1 | iex"
   ```

   Then restart your terminal so the updated `PATH` takes effect.

3. Create the project environment.

   In this repository folder, run:

   ```powershell
   pixi install
   ```

   This reads `pixi.toml`, installs the required Python version, and creates the local project environment.

4. Run commands through `pixi`.

   You can run the scripts without manually activating anything:

   ```powershell
   pixi run draw-azimuthal-equidistant -- --help
   pixi run draw-stereographic -- --help
   ```

   `pixi run` will use the environment defined by this project. If the environment has not been installed yet, `pixi run` can install it automatically.

5. Optional: open a shell inside the project environment.

   ```powershell
   pixi shell
   ```

6. Run the interactive image rectifier.

   ```powershell
   pixi run perspective-correct -- --input-path "E:\path\to\input.png" --save-path "E:\path\to\output.png"
   ```

Official pixi docs:

- Installation: https://pixi.prefix.dev/latest/installation/
- `pixi install`: https://pixi.prefix.dev/latest/reference/cli/pixi/install/

## Desktop GUI

Ad astra abyssosque—welcome to this astrolabe design assistant!

Start the integrated desktop application with:

```powershell
pixi run gui
```

The two drawing workspaces are **Azimuthal Equidistant** and **Stereographic**.
Each workspace has peer **Main**, **Ecliptic**, and **Star Chart** preview tabs.
The shared parameter panel remains visible and is ordered into the same three
sections; switching a preview tab automatically scrolls the panel to its section.
Star Chart geometry does not duplicate the workspace controls: center pole,
boundary latitude, projection, diameter, and boundary width are inherited from
the Main section and are written into the exported Star Chart command.
Dependent controls still appear only when their parent feature is enabled. Hover
over an argument name for its description, then press **Update Preview** to render
all three previews in the current projection workspace without changing the
selected preview tab or overwriting a file. Each preview is updated independently;
if one render fails, its last valid image is retained while the others still update.

The perspective-correction tab loads an image directly into the application.
Click four corners in order, then update the preview to rectify the quadrilateral
to a square. Points can be undone or reset before correction.

Use **File > Import Configuration** to open a README/text/PowerShell file or to
paste a `pixi run` command, a PowerShell `@(...)` argument list, or plain CLI
arguments. Imported text is parsed but never executed. **Save** and **Save As**
export the currently selected Main, Ecliptic, or Star Chart preview as SVG,
transparent PNG, or white-background JPEG; raster projection output
uses the DPI selected under **Settings > Raster Export DPI** (300 by default).

Use **File > Export Configuration** to save the complete active projection
workspace to a `.txt` file. It contains both the projection command (Main and
Ecliptic sections) and the Star Chart command. Importing that file restores all
three sections together.

The interface starts in English. Use **Settings > Language** to switch the
entire application between English and Chinese; the selection takes effect
immediately and is remembered for the next launch.

Each workspace's **Star Chart** tab uses locally cached HYG and Stellarium data. Open
**Settings > Astronomical Data** to download/update the cache, clear it, or open
its folder. Updating a preview never starts a network request. Star size uses
only brightest- and faintest-level diameter fields, with intermediate levels
linearly interpolated;
line, star-name, constellation-name, font, position, and label-avoidance controls
appear only when relevant.

## Polar Star Chart (HYG + Stellarium)

Download the astronomical data explicitly before the first render:

```powershell
pixi run download-star-data
```

By default the data are stored inside this repository under `src/`: HYG is in
`src/hyg/`, Stellarium cultures are in `src/stellarium/`, and the integrity
manifest is `src/manifest.json`. The entire generated `src/` directory is ignored
by Git. The cache contains HYG 4.1 and the Stellarium 26.1 sky-culture files together
with a `manifest.json` recording their versions, source URLs, download time,
SHA-256 hashes, and licenses. The data are not committed to this repository.
Use `--data-cache` on either command to select a different cache directory.

The star chart can overlay the celestial equator (`--equator`) and ecliptic
(`--ecliptic`) independently; both default to off. Set their stroke widths in
millimeters with `--equator-width` and `--ecliptic-width` (default `0.1`). The GUI
provides matching “叠加赤道” and “叠加黄道” checkboxes with width controls. Both curves
follow the chart projection and rotation and are clipped to its circular boundary.
The ecliptic uses the same fixed obliquity as the existing projection charts.

Enable **叠加银河轮廓线** in the star-chart GUI, or pass `--milky-way` on the
command line. `--milky-way-width` sets the line width in millimeters (default
`0.1`). The overlay defaults to off and draws all five brightness contour levels
without fill, with precession to the chart year and clipping to its boundary.
Both projections, poles, and rotation directions are supported.

The source is [d3-celestial's `data/mw.json`](https://github.com/ofrohn/d3-celestial/blob/7e720a3de062059d4c5400a379146a601d9010e0/data/mw.json),
converted from Jose R. Vieira's **Milky Way Outline Catalog**. Its GeoJSON
coordinates are J2000 right ascension (degrees, wrapped to −180…180) and
declination. The d3-celestial project declares BSD-3-Clause; its license and
upstream source attribution are preserved as `src/milkyway/LICENSE` and
`src/milkyway/SOURCE.md`. The cache manifest records the fixed revision, source
URL, and file hashes. See the source attribution as well as the project license
when redistributing data.

**设置 → 天文数据 → 下载／更新** includes the outlines. To add only this small
dataset to an existing cache, run:

```powershell
pixi run download-star-data --milky-way-only
pixi run draw-star-chart --milky-way --milky-way-width 0.1
```

Rendering uses the local `src/milkyway/mw.json` cache and does not access the network.

```powershell
pixi run draw-star-chart -- @(
  "--center", "north",
  "--range-declination", "-30",
  "--projection", "azimuthal-equidistant",
  "--diameter", "120",
  "--boundary-width", "0.2",
  "--rotation", "0",
  "--rotation-direction", "counterclockwise",
  "--epoch-year", "2026",
  "--magnitude-max", "5.0",
  "--magnitude-levels", "5",
  "--star-diameter-max", "0.7",
  "--star-diameter-min", "0.2",
  "--star-stroke-width", "0.1",
  "--fill-stars",
  "--constellation-lines",
  "--sky-culture", "modern",
  "--constellation-width", "0.1",
  "--no-show-star-names",
  "--no-show-constellation-names",
  "--avoid-label-overlap",
  "--output", "output/star_chart.svg"
)
```

`--center` selects the north or south pole. `--range-declination` is the signed
declination at the circular edge, and `--projection` accepts
`azimuthal-equidistant` or `stereographic`. Right ascension 0h starts at the top;
`--rotation-direction` selects whether it increases clockwise or counterclockwise,
and `--rotation` applies an additional angular offset to the complete chart. In
the GUI workspace both controls are hidden: the offset is zero and the direction
follows `--ecliptic-rotation-direction`, or `--solar-motion-direction` when the
former is Automatic.

`--magnitude-max` is the only magnitude cutoff: every stellar object with a
visual magnitude less than or equal to it is included. The HYG convenience row
for the Sun is excluded. For sizing, the normal stellar range beginning at
`-1.5` is split into equal-width levels; any still-brighter star is assigned to
the brightest level. `--star-diameter-max` sets the brightest-level size and
`--star-diameter-min` sets the faintest-level size; all intermediate level
diameters are linearly interpolated. The old comma-separated `--star-diameters`
option remains accepted for configuration compatibility but is no longer shown
or exported by the GUI. Boolean switches support
their `--no-...` forms. Constellation segments are drawn only when both endpoint
stars satisfy the magnitude upper limit, and each segment is geometrically
clipped to the circular declination boundary. An edge with both endpoints outside
the declination range is omitted, preventing an exterior projected chord from
falsely crossing the whole chart. Only the culture's official
`constellations` collection is used; Stellarium's optional `asterisms` and
internal ray helpers are excluded. Star names and constellation/cultural-figure names have
independent language, system font, size, preferred eight-direction position,
radial offset, and tangential offset options. Automatic collision avoidance is
enabled by default; labels that cannot be placed are omitted and counted in the
render summary.

`--star-name-language` and `--constellation-name-language` independently accept
`en` or `zh`. These choices control text in the generated chart and never follow
or change with the desktop GUI language.

HYG 4.1 positions are interpreted at J2000. Astropy applies available space
motion and precession to `--epoch-year`; stars without complete distance or
radial-velocity information still use the available angular motion and are
reported as degraded. [HYG 4.1](https://github.com/astronexus/HYG-Database/tree/main/hyg)
is distributed under CC BY-SA 4.0. Sky-culture files come from the
[Stellarium 26.1](https://github.com/Stellarium/stellarium/releases/tag/v26.1)
GPL-2.0 project, while individual contributed sky cultures may state additional
licenses. Review the preserved culture license files and the source/license
entries in the cache manifest when redistributing derived work.

## Azimuthal Equidistant

Use `scripts/draw_azimuthal_equidistant.py` through the `draw-azimuthal-equidistant` task:

```powershell
pixi run draw-azimuthal-equidistant -- @(
  "--latitude", "35",
  "--center", "north",
  "--range-latitude", "-55",
  "--diameter", "40",
  "--azimuth-lines", "30",
  "--altitude-lines", "15",
  "--sub-azimuth-lines", "3",
  "--sub-altitude-lines", "3",
  "--boundary-width", "0.1",
  "--horizon-width", "0.2",
  "--azimuth-width", "0.1",
  "--altitude-width", "0.1",
  "--sub-azimuth-width", "0.05",
  "--sub-altitude-width", "0.05",
  "--civil-twilight",
  "--nautical-twilight",
  "--astronomical-twilight",
  "--twilight-width", "0.15",
  "--twilight-style", "dashed",
  "--equator-tropics",
  "--equator-tropics-width", "0.12",
  "--day-unequal-hour-lines",
  "--night-unequal-hour-lines",
  "--day-unequal-hour-labels",
  "--night-unequal-hour-labels",
  "--unequal-hour-label-style", "arabic",
  "--unequal-hour-width", "0.1",
  "--unequal-hour-label-size", "0.8",
  "--unequal-hour-label-width", "0.15",
  "--unequal-hour-label-line-position", "0.5",
  "--unequal-hour-label-arc-adjust", "0.0",
  "--solar-motion-direction", "clockwise",
  "--unequal-hour-label-letter-spacing", "0.6",
  "--azimuth-labels",
  "--azimuth-label-size", "0.8",
  "--azimuth-label-width", "0.15",
  "--azimuth-label-position", "0.35",
  "--azimuth-label-center-adjust", "0.0",
  "--azimuth-label-letter-spacing", "0.6",
  "--crosshair",
  "--crosshair-horizontal-width", "0.1",
  "--crosshair-vertical-width", "0.15",
  "--output", "output/readme_azimuthal_equidistant.svg"
)
```

![Azimuthal equidistant example](example/azimuthal_equidistant.svg)

## Notes

- `--range-latitude -55` means `55S`.
- `--diameter` is in millimeters.
- The exported SVG adds an automatic outer margin so thick strokes and labels are not clipped.
- The sky region appears above the image by default, for both north-centered and south-centered output.
- Use `--rotate-180` to rotate the projection 180 degrees and place the sky region below the image.
- `--boundary-width` sets the outer boundary line width in millimeters.
- `--horizon-width` sets the horizon line width in millimeters.
- `--azimuth-lines` draws azimuth lines every N degrees; use `0` to disable them.
- `--altitude-lines` draws altitude lines every N degrees; use `0` to disable them.
- `--sub-azimuth-lines` splits each azimuth main interval into `N` cells using sub-lines. `0` or `1` disables them.
- `--sub-altitude-lines` splits each altitude main interval into `N` cells using sub-lines. `0` or `1` disables them.
- `--azimuth-width` sets the azimuth line width in millimeters.
- `--altitude-width` sets the altitude line width in millimeters.
- `--sub-azimuth-width` sets the sub-azimuth line width in millimeters.
- `--sub-altitude-width` sets the sub-altitude line width in millimeters.
- `--civil-twilight` draws the `-6 degree` twilight line.
- `--nautical-twilight` draws the `-12 degree` twilight line.
- `--astronomical-twilight` draws the `-18 degree` twilight line.
- `--twilight-width` sets the shared twilight line width in millimeters.
- `--twilight-style` sets twilight lines to `solid` or `dashed`.
- `--astronomical-twilight-width` is kept as a legacy fallback when `--twilight-width` is not set.
- `--equator-tropics` draws the celestial equator and the northern/southern tropic lines.
- `--equator-tropics-width` sets the shared line width for those three lines in millimeters.
- The tropic declination is fixed at `23.4392911111` degrees.
- `--day-unequal-hour-lines` draws the 11 daytime unequal-hour lines, dividing sunrise to sunset into 12 equal temporal hours.
- `--night-unequal-hour-lines` draws the 11 nighttime unequal-hour lines, dividing sunset to sunrise into 12 equal temporal hours.
- `--unequal-hour-width` sets the shared line width for both daytime and nighttime unequal-hour lines in millimeters.
- `--day-unequal-hour-labels` labels the daytime unequal-hour lines.
- `--night-unequal-hour-labels` labels the nighttime unequal-hour lines.
- Unequal-hour labels are drawn only when their corresponding unequal-hour lines are also enabled.
- `--unequal-hour-label-style` switches unequal-hour labels between `roman` and `arabic`.
- `--unequal-hour-label-size` sets the unequal-hour label font size in millimeters.
- `--unequal-hour-label-width` sets the unequal-hour label stroke width in millimeters.
- `--unequal-hour-label-line-position` sets where the label sits along each unequal-hour line from the outer visible tropic-side anchor: `0` is closest to that outer anchor, `1` is farther inward, and negative values extend outward along the line trend.
- `--unequal-hour-label-arc-adjust` shifts the label along its label circle within `[-1, 1]`: positive moves toward larger hour numbers, negative toward smaller ones, scaled by the arc to the adjacent hour-line point on the same circle.
- `--solar-motion-direction` sets whether solar motion, unequal-hour label numbering, and azimuth label handedness increase `clockwise` or `counterclockwise`.
- `--unequal-hour-label-letter-spacing` sets the spacing between unequal-hour label glyphs in millimeters.
- Unequal-hour labels stay upright instead of rotating with the line, and are placed as close as practical to the outer visible tropic side while staying inside the current projection range.
- Unequal-hour lines are traced across the Sun's declination range between the two tropics, so at latitudes with circumpolar day or night they may appear only over part of that range.
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

Use `scripts/draw_stereographic.py` through the `draw-stereographic` task. It accepts the same arguments as the azimuthal-equidistant drawer:

```powershell
pixi run draw-stereographic -- @(
  "--latitude", "50",
  "--center", "south",
  "--range-latitude", "23.5",
  "--diameter", "40",
  "--azimuth-lines", "30",
  "--altitude-lines", "15",
  "--sub-azimuth-lines", "3",
  "--sub-altitude-lines", "3",
  "--boundary-width", "0.1",
  "--horizon-width", "0.2",
  "--azimuth-width", "0.1",
  "--altitude-width", "0.1",
  "--sub-azimuth-width", "0.05",
  "--sub-altitude-width", "0.05",
  "--civil-twilight",
  "--nautical-twilight",
  "--astronomical-twilight",
  "--twilight-width", "0.15",
  "--twilight-style", "dashed",
  "--equator-tropics",
  "--equator-tropics-width", "0.12",
  "--day-unequal-hour-lines",
  "--night-unequal-hour-lines",
  "--day-unequal-hour-labels",
  "--night-unequal-hour-labels",
  "--unequal-hour-label-style", "arabic",
  "--unequal-hour-width", "0.1",
  "--unequal-hour-label-size", "0.8",
  "--unequal-hour-label-width", "0.15",
  "--unequal-hour-label-line-position", "0.1",
  "--unequal-hour-label-arc-adjust", "0.2",
  "--solar-motion-direction", "counterclockwise",
  "--unequal-hour-label-letter-spacing", "0.6",
  "--azimuth-labels",
  "--azimuth-label-size", "0.8",
  "--azimuth-label-width", "0.15",
  "--azimuth-label-position", "0.35",
  "--azimuth-label-center-adjust", "0.0",
  "--azimuth-label-letter-spacing", "0.6",
  "--crosshair",
  "--crosshair-horizontal-width", "0.1",
  "--crosshair-vertical-width", "0.15",
  "--output", "output/readme_stereographic.svg"
)
```

![Stereographic example](example/stereographic.svg)

- `scripts/draw_stereographic.py` keeps the same CLI as `scripts/draw_azimuthal_equidistant.py`.
- In stereographic projection, the antipodal pole diverges to infinity, so `--range-latitude` cannot be the opposite pole itself.

## Ecliptic

Use `--ecliptic` to write the ecliptic as a separate companion SVG for the same projection, and `--ecliptic-width` to control its line width in millimeters.

- `--ecliptic-band-width` sets the band width in millimeters between the ecliptic and its inner concentric curve. If omitted, it defaults to the ecliptic circle radius.
- `--ecliptic-angle-lines` draws main inward ecliptic angle tick marks every `N` degrees along the ecliptic.
- `--sub-ecliptic-angle-lines` splits each main ecliptic angle interval into `N` cells using sub tick marks. `0` or `1` disables them.
- `--ecliptic-angle-width` sets the main ecliptic angle tick mark width in millimeters.
- `--sub-ecliptic-angle-width` sets the sub ecliptic angle tick mark width in millimeters.
- `--ecliptic-rotation-direction` sets whether ecliptic longitudes and date-ring dates increase `clockwise` or `counterclockwise` in the companion ecliptic SVG. If omitted, it follows `--solar-motion-direction`.
- Main tick marks and sub tick marks both span the full ecliptic band width.
- The companion ecliptic SVG draws both the outer ecliptic and its inner concentric curve, keeps the projection boundary circle for alignment, and emits ecliptic ticks from the traditional stereographic source point where the equinox and solstice chords intersect.
- `--date-ring` draws a date ring outside the projection counter in the companion ecliptic SVG.
- The date ring is concentric with the projection counter center, not with the ecliptic circle center.
- The projection counter itself is the date ring inner boundary.
- `--date-ring-width` sets the stroke width of the date ring inner and outer boundaries. If omitted, it follows `--ecliptic-width`.
- `--date-ring-band-width` sets the radial width in millimeters between the counter and the date ring outer boundary, independent of the ecliptic geometry.
- `--rotate-date-ring-180` rotates the entire date ring by `180` degrees. It is off by default.
- `--date-ring-month-width` sets the stroke width of month-end date ring ticks.
- `--date-ring-sub-width` sets the stroke width of sub day date ring ticks.
- `--date-ring-sub-interval` sets the day spacing of sub ticks. `1` means daily ticks. `0` disables them.
- `--date-ring-sub-sub-width` sets the stroke width of second-level sub day date ring ticks.
- `--date-ring-sub-sub-interval` sets the day spacing of second-level sub ticks. `1` means daily ticks. `0` disables them.
- `--date-ring-month-labels` labels the starts of months on the date ring with upright Arabic month numbers, aligned to the corresponding previous month-end boundary.
- `--date-ring-month-label-size` sets the month label font size in millimeters.
- `--date-ring-month-label-width` sets the month label stroke width in millimeters.
- `--date-ring-month-label-line-position` sets where the month label sits across the date-ring band from the outer boundary: `0` is outermost, `1` is closest to the counter, and negative values extend outward.
- `--date-ring-month-label-arc-adjust` shifts the month label along the date ring by a fixed angle in degrees: positive moves toward later dates in the month, negative toward earlier dates.
- `--date-ring-month-label-letter-spacing` sets the spacing between month label glyphs in millimeters.
- Date ring month labels are radially oriented by default with their tops pointing toward the center. `--reverse-date-ring-month-label-orientation` flips them so their bottoms point toward the center instead.
- `--date-ring-year` chooses which calendar year's solar-longitude progression is used to optimize the date-ring phase. The default is `2026`.
- The date ring always uses `365` equal day divisions. Leap years do not add a February 29 slot; the ring stays idealized and the selected year only changes the optimized phase and the reported error summary.
- Instead of forcing any specific calendar day to the vernal point, the program chooses the single phase offset that minimizes the maximum angular date-ring error across the selected year.
- That longitude approximation is a standard Julian-day solar-position formula of the Meeus/NOAA style: it computes Julian centuries from J2000, then solar mean longitude, mean anomaly, equation of center, true longitude, and a small apparent-longitude correction.
- This is intended for date-ring alignment and error estimation, not for high-precision ephemeris work.
- When `--date-ring` is enabled, the program prints a stdout summary of the equal-day ring error relative to approximate true solar ecliptic longitude progression for the selected year.

```powershell
pixi run draw-stereographic -- @(
  "--latitude", "50",
  "--center", "south",
  "--range-latitude", "23.5",
  "--diameter", "40",
  "--azimuth-lines", "0",
  "--altitude-lines", "0",
  "--ecliptic",
  "--ecliptic-width", "0.17",
  "--ecliptic-band-width", "2.0",
  "--ecliptic-angle-lines", "30",
  "--sub-ecliptic-angle-lines", "3",
  "--ecliptic-angle-width", "0.11",
  "--sub-ecliptic-angle-width", "0.05",
  "--ecliptic-rotation-direction", "counterclockwise",
  "--date-ring",
  "--date-ring-width", "0.17",
  "--date-ring-band-width", "2.0",
  "--date-ring-month-width", "0.11",
  "--date-ring-sub-width", "0.05",
  "--date-ring-sub-sub-width", "0.03",
  "--date-ring-sub-interval", "1",
  "--date-ring-sub-sub-interval", "5",
  "--date-ring-month-labels",
  "--date-ring-month-label-size", "0.8",
  "--date-ring-month-label-width", "0.15",
  "--date-ring-month-label-line-position", "0.5",
  "--date-ring-month-label-arc-adjust", "0.0",
  "--date-ring-month-label-letter-spacing", "0.6",
  "--date-ring-year", "2026",
  "--output", "output/ecliptic_projection.svg"
)
```

This produces:

- `output/ecliptic_projection.svg`
- `output/ecliptic_projection_ecliptic.svg`

![Ecliptic example](example/ecliptic.svg)

The companion ecliptic file uses the main `--output` filename with an added `_ecliptic` suffix before `.svg`.

## Image Rectifier

Use `scripts/perspective_corrector.py` through the `perspective-correct` task:

```powershell
pixi run perspective-correct -- --input-path "E:\path\to\input.png" --save-path "E:\path\to\output.png"
```

The script opens an interactive OpenCV window for manual rectification.

### Mode Selection

- Press `b` to use quadrilateral mode.
- Press `c` to select circle mode.

### Quadrilateral Mode

- Press `a` to arm the next point.
- Left click once to place that point.
- Press `d` to delete the most recently added point.
- Add 4 points in order around the target region.
- Starting from the second point, each new point is connected to the previous point.
- After the fourth point, the preview closes the shape back to the first point.
- Press `Enter` to rectify the selected quadrilateral into a square.

### Result Preview

- Press `s` to save the corrected image to `--save-path` and exit.
- Press `q` to exit without saving.
- Press `r` to discard the current result and restart from the original image.
- Press `a` to start a new selection on top of the corrected image.

### Circle Mode Status

- `c` mode is currently not implemented.
- Three points on a circle are not enough to recover a reliable perspective rectification uniquely.
- If circle-based rectification is needed later, the workflow should use more points and ellipse fitting or additional geometric constraints.

## Astrolabe Back / 星盘背面

运行 `pixi run gui`，在等距方位投影或球极投影工作区中选择“背面”标签页。
外径与外轮廓线宽跟随主图，日期和 EOT 年份跟随星图。背面是平面测量标尺，
两种投影分别保存设置，不再对背面刻度施加天球投影。
更新预览同时刷新背面；当前背面页可保存为 SVG、PNG、JPEG。
工作区配置包含新增命令，旧配置仍可导入。单独导入背面命令时，外径、线宽、年份会更新共享参数。

```powershell
pixi run draw-astrolabe-back -- --projection stereographic --diameter 120 --boundary-width 0.2 --epoch-year 2026 --angle-band-width 8 --date-band-width 7 --label-size 1.4 --eot-min-radius 0.95 --eot-max-radius 0.05 --calendar-mode concentric --upper-layout hours-sincos --sincos-scale both --shadow-band-width 5 --shadow-label-band-width 3 --output output/back_reference.svg
```

- 外圈包括四象限 0–90° 测高刻度和十二宫各 0–30° 黄经刻度。
  `--zodiac-zero` 设置白羊宫零点相对右水平线的逆时针角度，`--rotation-direction` 设置黄经方向；测高仍从水平线起算。
- `--calendar-mode concentric`：同心圈按公历每日 UT 正午的太阳视黄经定位，日期间隔不均匀。
- `--calendar-mode eccentric`：全年365或366日等距，拟合圆心与相位。
  这是偏心圆近似，无法严格复现椭圆轨道；CLI、SVG描述及GUI状态栏报告最大对齐误差。
  误差指日期刻度**外端点**从中心轴看去的黄经偏差。保留2月29日。
  年份范围1–3000，早期日期采用回推公历，太阳公式不是高精度星历。
- `--upper-layout hours`：传统不等时小时弧，将日出至日落分成十二份。
  以新的非镜像参考图为准，`hours-sincos`：左半保留小时弧并成对标注上午/下午，右半绘制极坐标
  `r=K sin(θ)`、`r=K cos(θ)`；`--sincos-scale` 可选50、60或 `both`（默认同时显示）。
  **内圈半径恒对应读数60**。`--sincos-zero-radius` 设置读数0的起始半径占内圆半径的比例（0至小于1，默认0）。
  读数v对应半径为 `R*(z+(1-z)*v/60)`；50倍曲线最大读数50，两种函数共用此标度。
  盘面只画函数曲线，不画读数标尺；配套刻度在新增的“标尺”页中输出。
- 下半影方每边默认12单位，通过 `--shadow-divisions` 调整。高度角α对应水平边读数
  `N cot(α)`、竖边读数 `N tan(α)`。已知水平距离D，水平边读数q对应高差
  `H=D*N/q`，竖边读数q对应 `H=D*q/N`；测高时另加观测轴离地高度。
  刻度带内外边界之间的分格沿中心轴射线绘制，保证在整条刻线上读数一致。
  `--shadow-band-width` 调刻度带宽，`--shadow-label-band-width` 调独立内侧文字带宽。
  默认不显示影方数字，与新参考图一致；`--shadow-numbers` 可打开数字。
- EOT曲线按太阳黄经排列，直接叠加在内部图案上，不占用独立环带，也不画EOT标尺或同心参考圈。
  `--eot-min-radius` 设置全年最慢时（最小时差）的半径比例，`--eot-max-radius` 设置全年最快时（最大时差）的半径比例。
  两者均相对于内圆半径，范围0至1；0.5表示内圆半径的一半，会随盘径、日期圈宽度等自动缩放。
  默认最慢为0.95、最快为0.05，GUI和CLI统一使用与reference一致的方向。
  其余时差在线性径向标度上插值；两个比例可反向设置，也可设为0。年度极值按该年每日UT正午的时差采样确定。
  旧配置中的毫米数值及−1自动值需改为0至1的比例；不再作为绝对距离解释。
  SVG曲线的 `data-eot-*` 属性记录时差极值、比例及换算后的毫米半径，供后续独立标尺使用。
  EOT定义为真太阳时减平太阳时；`--no-eot` 可隐藏。旧配置的 `--eot-band-width` 仍可读入，但不再使用。
  圈宽、间距、字号及线宽均可调，单位mm。
  圈宽挤占内部测量区时会报错，避免裁切。

### 背面文字设置

所有数字和文字均为原生 SVG `<text>`，保留大小写，可在矢量编辑器中修改。
字体由本机字体选择器提供；换机查看时需安装所选字体，否则查看器会替换字体。
在背面参数中的“文字设置类别”选择需要调整的一类，再修改其字体、字号和位置。
角度数字、黄道度数、黄道名称、日期数字、月份名称、小时数字、sin/cos名称、影方数字和影方名称分别独立设置。

CLI 对应前缀为 `angle`、`zodiac-degree`、`zodiac-name`、`day`、`month`、`hour`、`sincos`、`shadow-number`、`shadow-name`。
以月份为例：

```powershell
--month-label-font "Times New Roman" --month-label-size 1.8 --month-label-radial-offset 0.5 --month-label-angular-offset 2 --month-label-orientation tangent --month-label-rotation 180
```

- `*-label-size`：字号mm，0沿用该类默认字号，由公共 `--label-size` 派生。
- `*-label-radial-offset`：径向移动mm，向外为正。
- `*-label-angular-offset`：绕圆周移动角度，逆时针为正；只移动文字，不改变刻度。
- `*-label-orientation`：`auto` 自动保持可读、`tangent` 沿切向、`radial` 沿径向、`horizontal` 水平。
- `*-label-rotation`：额外旋转角度，顺时针为正；180可翻转文字。

偏心日期圈的日、月标签以日期圈自己的圆心移动，其他标签以盘心移动。文字设置会随工作区配置一同导入和导出。

小时弧参考 [The Astrolabe Project](https://www.astrolabeproject.com/26/02/2012/drafting-the-astrolabe-11-the-unequal-hour-arcs/)，
影方参考 [Shadow Squares](https://www.astrolabeproject.com/16/01/2012/drafting-the-astrolabe-10-the-shadow-squares/)，
时差采用 [NOAA/Meeus计算方法](https://gml.noaa.gov/grad/solcalc/calcdetails.html)。

### 配套标尺

两种投影工作区均有“标尺”标签页。点击更新预览，标尺会同步使用对应背面盘的内圆半径、
sin/cos零值比例、EOT两端比例和星图年份。左臂为0–60刻度（向外读数增大），右臂为EOT分钟刻度。
EOT刻度按间隔向外取整覆盖全年时差范围，边缘少量外推刻度仍使用同一线性标度。
整数5的倍数标注数字；数字为可编辑文本，可分别设置两侧的字体、字号和位置。

标尺及背面共用几何与数值换算，**改变尺身长度不会拉伸刻度**。
全局外圆的直径、轮廓线宽与主图一致，标尺外形的线宽独立设置。

```powershell
pixi run draw-astrolabe-ruler -- --diameter 120 --angle-band-width 8 --date-band-width 7 --epoch-year 2026 --sincos-zero-radius 0.12 --eot-min-radius 0.95 --eot-max-radius 0.05 --ruler-length-ratio 1 --ruler-symmetry rotational --ruler-arm-width 4 --ruler-hub-radius 5 --output output/ruler_rotational.svg
```

- `--ruler-length-ratio`：两尖端总长／全局外圆直径，1表示等长，0.8表示80%。
- `--ruler-symmetry rotational`：中心180°旋转对称，两臂位于长轴的相反侧，与参考图一致。
- `--ruler-symmetry axial`：关于过圆心、垂直于直径的轴镜像对称，两臂、刻度和数字均位于直径同侧。
- 两种对称方式的尺臂均以直径为读数边，刻线从尺边向尺身内部延伸。
- `--ruler-arm-width`：从直径读数边到尺身外缘的宽度，两种模式含义一致。
- `--ruler-hub-radius`、`--ruler-tip-length`：中心圆台和曲线尖端尺寸。
- `--ruler-hole-radius`：轴孔半径，默认0不画孔；设置轴孔时，落入孔内的刻度会省略。
- `--ruler-eot-step`：EOT刻度间隔，0.1至5分钟；`--ruler-tick-length` 和 `--ruler-tick-width` 设置刻线。
- `--ruler-sin-font/size/label-offset` 与 `--ruler-eot-font/size/label-offset`：两侧数字设置，偏移正值向尺臂内部移动。

缩短标尺后，超出可用直尺身（不含装饰尖端）的刻度会省略，GUI状态栏与CLI报告省略数量。
EOT两端半径比例相等时无法构成可读标尺，会明确报错。标尺支持SVG、PNG、JPEG保存；
工作区配置包含 `draw-astrolabe-ruler` 命令，旧配置仍可导入。单独导入标尺命令时也会同步其中的背面和全局参数。
