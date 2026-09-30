from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from draw_projection import AZIMUTHAL_EQUIDISTANT, CLOCKWISE, COUNTERCLOCKWISE, STEREOGRAPHIC
from star_chart import POSITIONS, default_data_cache, render_star_chart

HELP = {
    "milky_way": "Overlay the five Milky Way brightness contours from cached d3-celestial GeoJSON, precessed to the chart year.",
    "milky_way_width": "Milky Way contour stroke width in millimeters.",
    "equator": "Overlay the celestial equator on the star chart.",
    "equator_width": "Equator stroke width in millimeters.",
    "ecliptic": "Overlay the ecliptic using the same obliquity as the projection charts.",
    "ecliptic_width": "Ecliptic stroke width in millimeters.",
    "center": "Celestial pole placed at the center of the chart.",
    "range_declination": "Signed declination in degrees at the circular chart boundary.",
    "projection": "Radial projection used for all stars, lines, and labels.",
    "diameter": "Diameter of the circular chart boundary in millimeters.",
    "boundary_width": "Boundary stroke width in millimeters.", "rotation": "Rotate the complete chart in degrees.",
    "rotation_direction": "Direction in which right ascension increases around the chart.",
    "epoch_year": "Target year used for space motion and precession from J2000.",
    "magnitude_max": "Faintest included visual magnitude; every brighter star is included.",
    "magnitude_levels": "Number of equal-width visual-magnitude levels.",
    "star_diameter_max": "Diameter in millimeters for the brightest magnitude level.",
    "star_diameter_min": "Diameter in millimeters for the faintest magnitude level; intermediate levels are linearly interpolated.",
    "star_stroke_width": "Star-circle outline width in millimeters.", "fill_stars": "Fill star circles; use --no-fill-stars for hollow circles.",
    "constellation_lines": "Draw the selected sky culture's official constellation or primary cultural-figure lines; optional asterisms are excluded.",
    "sky_culture": "Stellarium sky-culture identifier available in the local cache.",
    "constellation_width": "Constellation line width in millimeters.",
    "show_star_names": "Draw names for visible stars.", "show_constellation_names": "Draw official constellation or primary cultural-figure names.",
    "avoid_label_overlap": "Try all eight positions and hide labels that still collide.",
    "data_cache": "Directory containing downloaded HYG and Stellarium data.", "output": "Output SVG path.",
}
for prefix, title in (("star_name", "star name"), ("constellation_name", "constellation/cultural-figure name")):
    HELP.update({f"{prefix}_language": f"English or Chinese text for each {title}; independent of the GUI language.", f"{prefix}_font": f"System font family for each {title}.",
        f"{prefix}_size": f"Font size for each {title} in millimeters.", f"{prefix}_position": f"Preferred one of eight positions for each {title}.",
        f"{prefix}_radial_offset": f"Radial offset for each {title} in millimeters.", f"{prefix}_tangential_offset": f"Tangential offset for each {title} in millimeters."})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Draw a polar star chart from HYG and Stellarium data.")
    p.add_argument("--center", choices=("north", "south"), default="north")
    p.add_argument("--range-declination", type=float, default=-30.0)
    p.add_argument("--projection", choices=(AZIMUTHAL_EQUIDISTANT, STEREOGRAPHIC), default=AZIMUTHAL_EQUIDISTANT)
    p.add_argument("--diameter", type=float, default=120.0); p.add_argument("--boundary-width", type=float, default=0.2)
    p.add_argument("--rotation", type=float, default=0.0)
    p.add_argument("--rotation-direction", choices=(CLOCKWISE, COUNTERCLOCKWISE), default=COUNTERCLOCKWISE)
    p.add_argument("--epoch-year", type=int, default=date.today().year)
    p.add_argument("--milky-way", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--milky-way-width", type=float, default=0.1)
    for curve in ("equator", "ecliptic"):
        p.add_argument(f"--{curve}", action=argparse.BooleanOptionalAction, default=False)
        p.add_argument(f"--{curve}-width", type=float, default=0.1)
    p.add_argument("--magnitude-max", type=float, default=5.0)
    p.add_argument("--magnitude-levels", type=int, default=5)
    p.add_argument("--star-diameter-max", type=float, default=0.7)
    p.add_argument("--star-diameter-min", type=float, default=0.2)
    p.add_argument("--star-diameters", default=None, help=argparse.SUPPRESS)
    p.add_argument("--star-stroke-width", type=float, default=0.1); p.add_argument("--fill-stars", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--constellation-lines", action=argparse.BooleanOptionalAction, default=True); p.add_argument("--sky-culture", default="modern")
    p.add_argument("--constellation-width", type=float, default=0.1)
    for prefix, title in (("star-name", "star name"), ("constellation-name", "constellation name")):
        dest = prefix.replace("-", "_")
        p.add_argument(f"--show-{prefix}s", action=argparse.BooleanOptionalAction, default=False)
        p.add_argument(f"--{prefix}-language", choices=("en", "zh"), default="en")
        p.add_argument(f"--{prefix}-font", default="sans-serif"); p.add_argument(f"--{prefix}-size", type=float, default=2.0 if prefix == "star-name" else 3.0)
        p.add_argument(f"--{prefix}-position", choices=POSITIONS, default="northeast")
        p.add_argument(f"--{prefix}-radial-offset", type=float, default=2.0); p.add_argument(f"--{prefix}-tangential-offset", type=float, default=0.0)
    p.add_argument("--avoid-label-overlap", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--data-cache", type=Path, default=default_data_cache()); p.add_argument("--output", type=Path, default=Path("output/star_chart.svg"))
    for action in p._actions:
        if action.dest in HELP: action.help = HELP[action.dest]
    return p


def main(argv=None):
    args = build_parser().parse_args(argv); svg, stats = render_star_chart(args)
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_bytes(svg)
    print(f"stars={stats.stars} segments={stats.segments} star_labels={stats.star_labels} constellation_labels={stats.figure_labels} hidden_labels={stats.hidden_labels} missing_ids={stats.missing_identifiers} degraded_motion={stats.degraded_motion}")


if __name__ == "__main__": main()
