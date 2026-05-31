from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Iterable, Sequence
from xml.etree.ElementTree import Element, ElementTree, SubElement


SVG_NS = "http://www.w3.org/2000/svg"
DEFAULT_CANVAS_MARGIN_MM = 6.0
LABEL_GLYPH_WIDTH = 0.7
LABEL_GLYPH_SPACING = 0.18
TROPIC_DECLINATION = 23.4392911111
ROMAN_NUMERALS = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI")
ARABIC_NUMERALS = tuple(str(number) for number in range(1, 12))
AZIMUTHAL_EQUIDISTANT = "azimuthal-equidistant"
STEREOGRAPHIC = "stereographic"
CLOCKWISE = "clockwise"
COUNTERCLOCKWISE = "counterclockwise"
PROJECTION_DESCRIPTIONS = {
    AZIMUTHAL_EQUIDISTANT: "Draw a horizon azimuthal-equidistant SVG for a given observer latitude.",
    STEREOGRAPHIC: "Draw a horizon stereographic SVG for a given observer latitude.",
}
PROJECTION_OUTPUTS = {
    AZIMUTHAL_EQUIDISTANT: Path("azimuthal_equidistant_projection.svg"),
    STEREOGRAPHIC: Path("stereographic_projection.svg"),
}


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def parse_args(projection: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=PROJECTION_DESCRIPTIONS[projection])
    parser.add_argument("--latitude", type=float, required=True, help="Observer latitude in degrees.")
    parser.add_argument(
        "--center",
        choices=("north", "south"),
        required=True,
        help="Projection center pole.",
    )
    parser.add_argument(
        "--range-latitude",
        type=float,
        required=True,
        help="Latitude shown on the outer boundary of the projection.",
    )
    parser.add_argument(
        "--diameter",
        type=float,
        required=True,
        help="Diameter in millimeters for the projected range circle.",
    )
    parser.add_argument(
        "--azimuth-lines",
        type=int,
        default=12,
        help="Number of azimuth lines to draw. Use 0 to disable.",
    )
    parser.add_argument(
        "--altitude-lines",
        type=int,
        default=6,
        help="Number of altitude lines to draw. Use 0 to disable.",
    )
    parser.add_argument(
        "--boundary-width",
        type=float,
        default=1.0,
        help="Stroke width of the outer boundary circle.",
    )
    parser.add_argument(
        "--horizon-width",
        type=float,
        default=1.5,
        help="Stroke width of the horizon line.",
    )
    parser.add_argument(
        "--azimuth-width",
        type=float,
        default=0.8,
        help="Stroke width of the azimuth lines.",
    )
    parser.add_argument(
        "--altitude-width",
        type=float,
        default=0.8,
        help="Stroke width of the altitude lines.",
    )
    parser.add_argument(
        "--civil-twilight",
        action="store_true",
        help="Draw the civil twilight line at altitude -6 degrees.",
    )
    parser.add_argument(
        "--nautical-twilight",
        action="store_true",
        help="Draw the nautical twilight line at altitude -12 degrees.",
    )
    parser.add_argument(
        "--astronomical-twilight",
        action="store_true",
        help="Draw the astronomical twilight line at altitude -18 degrees.",
    )
    parser.add_argument(
        "--twilight-width",
        type=float,
        default=None,
        help="Shared stroke width of enabled twilight lines.",
    )
    parser.add_argument(
        "--twilight-style",
        choices=("solid", "dashed"),
        default="solid",
        help="Line style for enabled twilight lines.",
    )
    parser.add_argument(
        "--astronomical-twilight-width",
        type=float,
        default=0.8,
        help="Legacy fallback stroke width for twilight lines when twilight-width is not set.",
    )
    parser.add_argument(
        "--equator-tropics",
        action="store_true",
        help="Draw the celestial equator and the northern/southern tropic lines.",
    )
    parser.add_argument(
        "--equator-tropics-width",
        type=float,
        default=0.8,
        help="Shared stroke width of the celestial equator and tropic lines.",
    )
    parser.add_argument(
        "--day-unequal-hour-lines",
        action="store_true",
        help="Draw the 11 daytime unequal-hour lines that divide sunrise to sunset into 12 equal temporal hours.",
    )
    parser.add_argument(
        "--night-unequal-hour-lines",
        action="store_true",
        help="Draw the 11 nighttime unequal-hour lines that divide sunset to sunrise into 12 equal temporal hours.",
    )
    parser.add_argument(
        "--unequal-hour-width",
        type=float,
        default=0.8,
        help="Shared stroke width of the daytime and nighttime unequal-hour lines.",
    )
    parser.add_argument(
        "--day-unequal-hour-labels",
        action="store_true",
        help="Label the daytime unequal-hour lines.",
    )
    parser.add_argument(
        "--night-unequal-hour-labels",
        action="store_true",
        help="Label the nighttime unequal-hour lines.",
    )
    parser.add_argument(
        "--unequal-hour-label-style",
        choices=("roman", "arabic"),
        default="roman",
        help="Number style for unequal-hour labels.",
    )
    parser.add_argument(
        "--unequal-hour-label-size",
        type=float,
        default=4.0,
        help="Font size in millimeters for unequal-hour labels.",
    )
    parser.add_argument(
        "--unequal-hour-label-width",
        type=float,
        default=0.2,
        help="Stroke width in millimeters for unequal-hour labels.",
    )
    parser.add_argument(
        "--unequal-hour-label-line-position",
        type=float,
        default=0.18,
        help="Label position from the outer visible end of each unequal-hour line (0) toward its inner visible end (1). Negative values extend outward along the line trend.",
    )
    parser.add_argument(
        "--unequal-hour-label-arc-adjust",
        type=float,
        default=0.0,
        help="Circular adjustment for unequal-hour labels within [-1, 1]. Positive moves toward larger label numbers, negative toward smaller ones, scaled by the arc to the adjacent hour-line point on the same label circle.",
    )
    parser.add_argument(
        "--solar-motion-direction",
        choices=(CLOCKWISE, COUNTERCLOCKWISE),
        default=CLOCKWISE,
        help="Whether solar motion and unequal-hour label numbering increase clockwise or counterclockwise.",
    )
    parser.add_argument(
        "--unequal-hour-label-letter-spacing",
        type=float,
        default=LABEL_GLYPH_SPACING,
        help="Additional spacing between unequal-hour label glyphs in millimeters.",
    )
    parser.add_argument(
        "--azimuth-labels",
        action="store_true",
        help="Label the eight main azimuths between the horizon and astronomical twilight.",
    )
    parser.add_argument(
        "--azimuth-label-size",
        type=float,
        default=4.0,
        help="Font size in millimeters for azimuth labels.",
    )
    parser.add_argument(
        "--azimuth-label-width",
        type=float,
        default=0.2,
        help="Stroke width in millimeters for azimuth labels.",
    )
    parser.add_argument(
        "--azimuth-label-position",
        type=float,
        default=0.5,
        help="Label position between horizon (0) and astronomical twilight (1).",
    )
    parser.add_argument(
        "--azimuth-label-center-adjust",
        type=float,
        default=0.0,
        help="Tangential centering adjustment in millimeters for azimuth labels.",
    )
    parser.add_argument(
        "--azimuth-label-letter-spacing",
        type=float,
        default=LABEL_GLYPH_SPACING,
        help="Additional spacing between azimuth label glyphs in millimeters.",
    )
    parser.add_argument(
        "--crosshair",
        action="store_true",
        help="Draw horizontal and vertical center lines through the projection center.",
    )
    parser.add_argument(
        "--crosshair-width",
        type=float,
        default=0.8,
        help="Fallback stroke width for both crosshair lines when neither axis-specific width is set.",
    )
    parser.add_argument(
        "--crosshair-horizontal-width",
        type=float,
        default=None,
        help="Stroke width of the horizontal crosshair line.",
    )
    parser.add_argument(
        "--crosshair-vertical-width",
        type=float,
        default=None,
        help="Stroke width of the vertical crosshair line.",
    )
    parser.add_argument(
        "--rotate-180",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Rotate the whole projection by 180 degrees so the sky region appears below the image. Disabled by default.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECTION_OUTPUTS[projection],
        help="Output SVG path.",
    )
    args = parser.parse_args()
    args.projection = projection
    return args


def validate_args(args: argparse.Namespace) -> None:
    for label, value in (
        ("latitude", args.latitude),
        ("range-latitude", args.range_latitude),
    ):
        if not -90.0 <= value <= 90.0:
            raise ValueError(f"{label} must be within [-90, 90] degrees.")

    if not 0.0 <= args.azimuth_label_position <= 1.0:
        raise ValueError("azimuth-label-position must be within [0, 1].")
    if args.unequal_hour_label_line_position > 1.0:
        raise ValueError("unequal-hour-label-line-position cannot be greater than 1.")
    if not -1.0 <= args.unequal_hour_label_arc_adjust <= 1.0:
        raise ValueError("unequal-hour-label-arc-adjust must be within [-1, 1].")

    if args.diameter <= 0:
        raise ValueError("diameter must be positive.")

    for label, value in (
        ("azimuth-lines", args.azimuth_lines),
        ("altitude-lines", args.altitude_lines),
    ):
        if value < 0:
            raise ValueError(f"{label} cannot be negative.")

    if args.twilight_width is not None and args.twilight_width < 0:
        raise ValueError("twilight-width cannot be negative.")

    for label, value in (
        ("boundary-width", args.boundary_width),
        ("horizon-width", args.horizon_width),
        ("azimuth-width", args.azimuth_width),
        ("altitude-width", args.altitude_width),
        ("astronomical-twilight-width", args.astronomical_twilight_width),
        ("equator-tropics-width", args.equator_tropics_width),
        ("unequal-hour-width", args.unequal_hour_width),
        ("unequal-hour-label-size", args.unequal_hour_label_size),
        ("unequal-hour-label-width", args.unequal_hour_label_width),
        ("azimuth-label-size", args.azimuth_label_size),
        ("azimuth-label-width", args.azimuth_label_width),
        ("crosshair-width", args.crosshair_width),
    ):
        if value < 0:
            raise ValueError(f"{label} cannot be negative.")

    for label, value in (
        ("crosshair-horizontal-width", args.crosshair_horizontal_width),
        ("crosshair-vertical-width", args.crosshair_vertical_width),
    ):
        if value is not None and value < 0:
            raise ValueError(f"{label} cannot be negative.")

    if args.azimuth_label_letter_spacing <= -LABEL_GLYPH_WIDTH:
        raise ValueError(
            "azimuth-label-letter-spacing must be greater than the glyph width negation."
        )
    if args.unequal_hour_label_letter_spacing <= -LABEL_GLYPH_WIDTH:
        raise ValueError(
            "unequal-hour-label-letter-spacing must be greater than the glyph width negation."
        )

    pole_sign = 1.0 if args.center == "north" else -1.0
    outer_angle = 90.0 - pole_sign * args.range_latitude
    if outer_angle <= 0:
        raise ValueError("range-latitude collapses the projection to zero radius.")
    if args.projection == STEREOGRAPHIC and outer_angle >= 180.0:
        raise ValueError(
            "range-latitude reaches the antipodal pole and diverges in stereographic projection."
        )


def horizontal_to_equatorial(
    observer_latitude: float,
    altitude: float,
    azimuth: float,
) -> tuple[float, float]:
    phi = math.radians(observer_latitude)
    h = math.radians(altitude)
    a = math.radians(azimuth)
    cos_phi = math.cos(phi)

    if abs(cos_phi) < 1e-12:
        declination = altitude if observer_latitude >= 0 else -altitude
        if observer_latitude >= 0:
            hour_angle = (azimuth + 180.0) % 360.0
        else:
            hour_angle = (-azimuth) % 360.0
        if hour_angle > 180.0:
            hour_angle -= 360.0
        return declination, hour_angle

    sin_dec = math.sin(phi) * math.sin(h) + cos_phi * math.cos(h) * math.cos(a)
    dec = math.asin(clamp(sin_dec, -1.0, 1.0))
    cos_dec = math.cos(dec)

    if abs(cos_dec) < 1e-12:
        hour_angle = 0.0
    else:
        sin_h = -math.sin(a) * math.cos(h) / cos_dec
        cos_h = (math.sin(h) - math.sin(phi) * math.sin(dec)) / (cos_phi * cos_dec)
        hour_angle = math.atan2(sin_h, cos_h)

    return math.degrees(dec), math.degrees(hour_angle)


def project_point(
    declination: float,
    hour_angle: float,
    center: str,
    projection: str,
    radius_scale: float,
    canvas_radius: float,
) -> tuple[float, float]:
    pole_sign = 1.0 if center == "north" else -1.0
    angular_distance = 90.0 - pole_sign * declination
    if projection == AZIMUTHAL_EQUIDISTANT:
        projected_radius = angular_distance * radius_scale
    else:
        angular_distance = clamp(angular_distance, 0.0, 179.999999)
        projected_radius = math.tan(math.radians(angular_distance) / 2.0) * radius_scale
    hour = math.radians(hour_angle)

    x = canvas_radius - projected_radius * math.sin(hour)
    y = canvas_radius - projected_radius * math.cos(hour)
    return x, y


def sample_horizon(
    observer_latitude: float,
    center: str,
    projection: str,
    radius_scale: float,
    canvas_radius: float,
    samples: int = 720,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(samples + 1):
        azimuth = 360.0 * index / samples
        declination, hour_angle = horizontal_to_equatorial(observer_latitude, 0.0, azimuth)
        points.append(
            project_point(declination, hour_angle, center, projection, radius_scale, canvas_radius)
        )
    return points


def sample_altitude_line(
    observer_latitude: float,
    altitude: float,
    center: str,
    projection: str,
    radius_scale: float,
    canvas_radius: float,
    samples: int = 720,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(samples + 1):
        azimuth = 360.0 * index / samples
        declination, hour_angle = horizontal_to_equatorial(observer_latitude, altitude, azimuth)
        points.append(
            project_point(declination, hour_angle, center, projection, radius_scale, canvas_radius)
        )
    return points


def sample_declination_line(
    declination: float,
    center: str,
    projection: str,
    radius_scale: float,
    canvas_radius: float,
    samples: int = 720,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(samples + 1):
        hour_angle = 360.0 * index / samples
        points.append(
            project_point(declination, hour_angle, center, projection, radius_scale, canvas_radius)
        )
    return points


def solar_rise_set_hour_angle(observer_latitude: float, declination: float) -> float | None:
    phi = math.radians(observer_latitude)
    dec = math.radians(declination)
    cos_hour_angle = -math.tan(phi) * math.tan(dec)
    if cos_hour_angle < -1.0 or cos_hour_angle > 1.0:
        return None
    return math.degrees(math.acos(clamp(cos_hour_angle, -1.0, 1.0)))


def temporal_hour_angle(
    observer_latitude: float,
    declination: float,
    hour_index: int,
    daytime: bool,
) -> float | None:
    hour_angle_limit = solar_rise_set_hour_angle(observer_latitude, declination)
    if hour_angle_limit is None:
        return None

    if daytime:
        return -hour_angle_limit + (2.0 * hour_angle_limit * hour_index / 12.0)

    hour_angle = hour_angle_limit + ((360.0 - 2.0 * hour_angle_limit) * hour_index / 12.0)
    if hour_angle > 180.0:
        hour_angle -= 360.0
    return hour_angle


def sample_temporal_hour_line(
    observer_latitude: float,
    center: str,
    projection: str,
    radius_scale: float,
    canvas_radius: float,
    hour_index: int,
    daytime: bool,
    samples: int = 720,
) -> list[list[tuple[float, float]]]:
    declination_start = -TROPIC_DECLINATION
    declination_stop = TROPIC_DECLINATION
    segments: list[list[tuple[float, float]]] = []
    current_segment: list[tuple[float, float]] = []

    for index in range(samples + 1):
        declination = declination_start + (declination_stop - declination_start) * index / samples
        hour_angle = temporal_hour_angle(observer_latitude, declination, hour_index, daytime)
        if hour_angle is None:
            if len(current_segment) >= 2:
                segments.append(current_segment)
            current_segment = []
            continue

        current_segment.append(
            project_point(declination, hour_angle, center, projection, radius_scale, canvas_radius)
        )

    if len(current_segment) >= 2:
        segments.append(current_segment)

    return segments


def project_horizontal_point(
    observer_latitude: float,
    altitude: float,
    azimuth: float,
    center: str,
    projection: str,
    radius_scale: float,
    canvas_radius: float,
) -> tuple[float, float]:
    declination, hour_angle = horizontal_to_equatorial(observer_latitude, altitude, azimuth)
    return project_point(declination, hour_angle, center, projection, radius_scale, canvas_radius)


def sample_azimuth_line(
    observer_latitude: float,
    azimuth: float,
    center: str,
    projection: str,
    radius_scale: float,
    canvas_radius: float,
    samples: int = 360,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []

    for index in range(samples + 1):
        altitude = 90.0 * index / samples
        declination, hour_angle = horizontal_to_equatorial(observer_latitude, altitude, azimuth)
        points.append(
            project_point(declination, hour_angle, center, projection, radius_scale, canvas_radius)
        )

    return points


def points_to_path(points: Sequence[tuple[float, float]], closed: bool) -> str:
    if not points:
        raise ValueError("Cannot build a path from zero points.")

    commands = [f"M {points[0][0]:.4f} {points[0][1]:.4f}"]
    commands.extend(f"L {x:.4f} {y:.4f}" for x, y in points[1:])
    if closed:
        commands.append("Z")
    return " ".join(commands)


def add_path(
    parent: Element,
    points: Sequence[tuple[float, float]],
    stroke_width: float,
    clip_id: str,
    closed: bool = False,
    dashed: bool = False,
) -> None:
    if stroke_width == 0:
        return

    attributes = {
        "d": points_to_path(points, closed=closed),
        "fill": "none",
        "stroke": "#000000",
        "stroke-width": f"{stroke_width:.4f}",
        "clip-path": f"url(#{clip_id})",
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
    }
    if dashed:
        dash = max(stroke_width * 4.0, 0.2)
        gap = max(stroke_width * 3.0, 0.15)
        attributes["stroke-dasharray"] = f"{dash:.4f} {gap:.4f}"

    SubElement(parent, "path", attributes)


def add_line(
    parent: Element,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    stroke_width: float,
    clip_id: str,
) -> None:
    if stroke_width == 0:
        return

    SubElement(
        parent,
        "line",
        {
            "x1": f"{x1:.4f}",
            "y1": f"{y1:.4f}",
            "x2": f"{x2:.4f}",
            "y2": f"{y2:.4f}",
            "stroke": "#000000",
            "stroke-width": f"{stroke_width:.4f}",
            "clip-path": f"url(#{clip_id})",
            "stroke-linecap": "round",
        },
    )


def point_inside_circle(
    point: tuple[float, float],
    center: float,
    radius: float,
    tolerance: float = 1e-6,
) -> bool:
    return math.hypot(point[0] - center, point[1] - center) <= radius + tolerance


def line_circle_intersection(
    start: tuple[float, float],
    end: tuple[float, float],
    center: float,
    radius: float,
) -> tuple[float, float] | None:
    start_x = start[0] - center
    start_y = start[1] - center
    delta_x = end[0] - start[0]
    delta_y = end[1] - start[1]

    a = delta_x * delta_x + delta_y * delta_y
    if a == 0:
        return None

    b = 2.0 * (start_x * delta_x + start_y * delta_y)
    c = start_x * start_x + start_y * start_y - radius * radius
    discriminant = b * b - 4.0 * a * c
    if discriminant < 0:
        return None

    root = math.sqrt(discriminant)
    candidates = sorted(
        t for t in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)) if 0.0 <= t <= 1.0
    )
    if not candidates:
        return None

    t = candidates[0] if point_inside_circle(start, center, radius) else candidates[-1]
    return start[0] + delta_x * t, start[1] + delta_y * t


def split_by_projection_circle(
    points: Sequence[tuple[float, float]],
    center: float,
    radius: float,
) -> list[list[tuple[float, float]]]:
    segments: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []

    for point in points:
        inside = point_inside_circle(point, center, radius)
        if not current:
            if inside:
                current.append(point)
            continue

        previous = current[-1]
        previous_inside = point_inside_circle(previous, center, radius)
        if previous_inside and inside:
            current.append(point)
            continue

        intersection = line_circle_intersection(previous, point, center, radius)
        if previous_inside and not inside:
            if intersection is not None:
                current.append(intersection)
            if len(current) >= 2:
                segments.append(current)
            current = []
        elif not previous_inside and inside:
            current = []
            if intersection is not None:
                current.append(intersection)
            current.append(point)

    if len(current) >= 2:
        segments.append(current)

    return segments


def build_label_segments(
    text: str,
    size: float,
    letter_spacing: float,
) -> tuple[list[tuple[tuple[float, float], tuple[float, float]]], float]:
    glyphs: dict[str, tuple[tuple[tuple[float, float], ...], ...]] = {
        "0": (
            ((0.14, -0.5), (LABEL_GLYPH_WIDTH * 0.86, -0.5)),
            ((LABEL_GLYPH_WIDTH * 0.86, -0.5), (LABEL_GLYPH_WIDTH, -0.34)),
            ((LABEL_GLYPH_WIDTH, -0.34), (LABEL_GLYPH_WIDTH, 0.34)),
            ((LABEL_GLYPH_WIDTH, 0.34), (LABEL_GLYPH_WIDTH * 0.86, 0.5)),
            ((LABEL_GLYPH_WIDTH * 0.86, 0.5), (0.14, 0.5)),
            ((0.14, 0.5), (0.0, 0.34)),
            ((0.0, 0.34), (0.0, -0.34)),
            ((0.0, -0.34), (0.14, -0.5)),
        ),
        "1": (
            ((LABEL_GLYPH_WIDTH * 0.5, -0.5), (LABEL_GLYPH_WIDTH * 0.5, 0.5)),
            ((LABEL_GLYPH_WIDTH * 0.32, -0.32), (LABEL_GLYPH_WIDTH * 0.5, -0.5)),
            ((LABEL_GLYPH_WIDTH * 0.28, 0.5), (LABEL_GLYPH_WIDTH * 0.72, 0.5)),
        ),
        "2": (
            ((0.0, -0.34), (0.14, -0.5)),
            ((0.14, -0.5), (LABEL_GLYPH_WIDTH * 0.86, -0.5)),
            ((LABEL_GLYPH_WIDTH * 0.86, -0.5), (LABEL_GLYPH_WIDTH, -0.34)),
            ((LABEL_GLYPH_WIDTH, -0.34), (LABEL_GLYPH_WIDTH, -0.14)),
            ((LABEL_GLYPH_WIDTH, -0.14), (0.0, 0.5)),
            ((0.0, 0.5), (LABEL_GLYPH_WIDTH, 0.5)),
        ),
        "3": (
            ((0.0, -0.34), (0.14, -0.5)),
            ((0.14, -0.5), (LABEL_GLYPH_WIDTH * 0.86, -0.5)),
            ((LABEL_GLYPH_WIDTH * 0.86, -0.5), (LABEL_GLYPH_WIDTH, -0.34)),
            ((LABEL_GLYPH_WIDTH, -0.34), (LABEL_GLYPH_WIDTH * 0.72, 0.0)),
            ((LABEL_GLYPH_WIDTH * 0.72, 0.0), (LABEL_GLYPH_WIDTH, 0.34)),
            ((LABEL_GLYPH_WIDTH, 0.34), (LABEL_GLYPH_WIDTH * 0.86, 0.5)),
            ((LABEL_GLYPH_WIDTH * 0.86, 0.5), (0.14, 0.5)),
            ((0.14, 0.5), (0.0, 0.34)),
            ((0.2, 0.0), (LABEL_GLYPH_WIDTH * 0.72, 0.0)),
        ),
        "4": (
            ((LABEL_GLYPH_WIDTH * 0.78, -0.5), (LABEL_GLYPH_WIDTH * 0.78, 0.5)),
            ((0.0, 0.10), (LABEL_GLYPH_WIDTH * 0.92, 0.10)),
            ((0.0, 0.10), (LABEL_GLYPH_WIDTH * 0.62, -0.5)),
        ),
        "5": (
            ((LABEL_GLYPH_WIDTH, -0.5), (0.12, -0.5)),
            ((0.12, -0.5), (0.12, -0.08)),
            ((0.12, -0.08), (LABEL_GLYPH_WIDTH * 0.74, -0.08)),
            ((LABEL_GLYPH_WIDTH * 0.74, -0.08), (LABEL_GLYPH_WIDTH, 0.10)),
            ((LABEL_GLYPH_WIDTH, 0.10), (LABEL_GLYPH_WIDTH, 0.34)),
            ((LABEL_GLYPH_WIDTH, 0.34), (LABEL_GLYPH_WIDTH * 0.86, 0.5)),
            ((LABEL_GLYPH_WIDTH * 0.86, 0.5), (0.14, 0.5)),
            ((0.14, 0.5), (0.0, 0.34)),
        ),
        "6": (
            ((LABEL_GLYPH_WIDTH * 0.86, -0.5), (0.14, -0.5)),
            ((0.14, -0.5), (0.0, -0.34)),
            ((0.0, -0.34), (0.0, 0.34)),
            ((0.0, 0.34), (0.14, 0.5)),
            ((0.14, 0.5), (LABEL_GLYPH_WIDTH * 0.86, 0.5)),
            ((LABEL_GLYPH_WIDTH * 0.86, 0.5), (LABEL_GLYPH_WIDTH, 0.34)),
            ((LABEL_GLYPH_WIDTH, 0.34), (LABEL_GLYPH_WIDTH, 0.10)),
            ((LABEL_GLYPH_WIDTH, 0.10), (LABEL_GLYPH_WIDTH * 0.86, -0.04)),
            ((LABEL_GLYPH_WIDTH * 0.86, -0.04), (0.0, -0.04)),
        ),
        "7": (
            ((0.0, -0.5), (LABEL_GLYPH_WIDTH, -0.5)),
            ((LABEL_GLYPH_WIDTH, -0.5), (LABEL_GLYPH_WIDTH * 0.28, 0.5)),
        ),
        "8": (
            ((0.14, -0.5), (LABEL_GLYPH_WIDTH * 0.86, -0.5)),
            ((LABEL_GLYPH_WIDTH * 0.86, -0.5), (LABEL_GLYPH_WIDTH, -0.34)),
            ((LABEL_GLYPH_WIDTH, -0.34), (LABEL_GLYPH_WIDTH, -0.10)),
            ((LABEL_GLYPH_WIDTH, -0.10), (LABEL_GLYPH_WIDTH * 0.86, 0.0)),
            ((LABEL_GLYPH_WIDTH * 0.86, 0.0), (0.14, 0.0)),
            ((0.14, 0.0), (0.0, -0.10)),
            ((0.0, -0.10), (0.0, -0.34)),
            ((0.0, -0.34), (0.14, -0.5)),
            ((0.14, 0.0), (LABEL_GLYPH_WIDTH * 0.86, 0.0)),
            ((LABEL_GLYPH_WIDTH * 0.86, 0.0), (LABEL_GLYPH_WIDTH, 0.10)),
            ((LABEL_GLYPH_WIDTH, 0.10), (LABEL_GLYPH_WIDTH, 0.34)),
            ((LABEL_GLYPH_WIDTH, 0.34), (LABEL_GLYPH_WIDTH * 0.86, 0.5)),
            ((LABEL_GLYPH_WIDTH * 0.86, 0.5), (0.14, 0.5)),
            ((0.14, 0.5), (0.0, 0.34)),
            ((0.0, 0.34), (0.0, 0.10)),
            ((0.0, 0.10), (0.14, 0.0)),
        ),
        "9": (
            ((0.14, -0.5), (LABEL_GLYPH_WIDTH * 0.86, -0.5)),
            ((LABEL_GLYPH_WIDTH * 0.86, -0.5), (LABEL_GLYPH_WIDTH, -0.34)),
            ((LABEL_GLYPH_WIDTH, -0.34), (LABEL_GLYPH_WIDTH, -0.10)),
            ((LABEL_GLYPH_WIDTH, -0.10), (LABEL_GLYPH_WIDTH * 0.86, 0.04)),
            ((LABEL_GLYPH_WIDTH * 0.86, 0.04), (0.14, 0.04)),
            ((0.14, 0.04), (0.0, -0.10)),
            ((0.0, -0.10), (0.0, -0.34)),
            ((0.0, -0.34), (0.14, -0.5)),
            ((LABEL_GLYPH_WIDTH, -0.34), (LABEL_GLYPH_WIDTH, 0.34)),
            ((LABEL_GLYPH_WIDTH, 0.34), (LABEL_GLYPH_WIDTH * 0.86, 0.5)),
            ((LABEL_GLYPH_WIDTH * 0.86, 0.5), (0.14, 0.5)),
        ),
        "I": (((LABEL_GLYPH_WIDTH * 0.5, -0.5), (LABEL_GLYPH_WIDTH * 0.5, 0.5)),),
        "N": (
            ((0.0, -0.5), (0.0, 0.5)),
            ((0.0, -0.5), (LABEL_GLYPH_WIDTH, 0.5)),
            ((LABEL_GLYPH_WIDTH, -0.5), (LABEL_GLYPH_WIDTH, 0.5)),
        ),
        "E": (
            ((LABEL_GLYPH_WIDTH, -0.5), (0.0, -0.5)),
            ((0.0, -0.5), (0.0, 0.5)),
            ((0.0, 0.0), (LABEL_GLYPH_WIDTH * 0.72, 0.0)),
            ((0.0, 0.5), (LABEL_GLYPH_WIDTH, 0.5)),
        ),
        "S": (
            ((LABEL_GLYPH_WIDTH, -0.5), (0.14, -0.5)),
            ((0.14, -0.5), (0.0, -0.34)),
            ((0.0, -0.34), (0.0, -0.10)),
            ((0.0, -0.10), (0.14, 0.0)),
            ((0.14, 0.0), (LABEL_GLYPH_WIDTH * 0.56, 0.0)),
            ((LABEL_GLYPH_WIDTH * 0.56, 0.0), (LABEL_GLYPH_WIDTH, 0.10)),
            ((LABEL_GLYPH_WIDTH, 0.10), (LABEL_GLYPH_WIDTH, 0.34)),
            ((LABEL_GLYPH_WIDTH, 0.34), (LABEL_GLYPH_WIDTH * 0.86, 0.5)),
            ((LABEL_GLYPH_WIDTH * 0.86, 0.5), (0.0, 0.5)),
        ),
        "W": (
            ((0.0, -0.5), (LABEL_GLYPH_WIDTH * 0.18, 0.5)),
            ((LABEL_GLYPH_WIDTH * 0.18, 0.5), (LABEL_GLYPH_WIDTH * 0.5, -0.08)),
            ((LABEL_GLYPH_WIDTH * 0.5, -0.08), (LABEL_GLYPH_WIDTH * 0.82, 0.5)),
            ((LABEL_GLYPH_WIDTH * 0.82, 0.5), (LABEL_GLYPH_WIDTH, -0.5)),
        ),
        "V": (
            ((0.0, -0.5), (LABEL_GLYPH_WIDTH * 0.5, 0.5)),
            ((LABEL_GLYPH_WIDTH * 0.5, 0.5), (LABEL_GLYPH_WIDTH, -0.5)),
        ),
        "X": (
            ((0.0, -0.5), (LABEL_GLYPH_WIDTH, 0.5)),
            ((LABEL_GLYPH_WIDTH, -0.5), (0.0, 0.5)),
        ),
    }

    advance = LABEL_GLYPH_WIDTH + letter_spacing
    text_width = len(text) * LABEL_GLYPH_WIDTH + max(0, len(text) - 1) * letter_spacing
    x_origin = -text_width / 2.0
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []

    for index, char in enumerate(text):
        glyph = glyphs[char]
        x_offset = x_origin + index * advance
        for start, end in glyph:
            segments.append(
                (
                    ((start[0] + x_offset) * size, start[1] * size),
                    ((end[0] + x_offset) * size, end[1] * size),
                )
            )

    weighted_mid_x = 0.0
    weighted_mid_y = 0.0
    total_length = 0.0
    for (x1, y1), (x2, y2) in segments:
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0:
            continue
        weighted_mid_x += ((x1 + x2) / 2.0) * length
        weighted_mid_y += ((y1 + y2) / 2.0) * length
        total_length += length

    if total_length > 0:
        center_x = weighted_mid_x / total_length
        center_y = weighted_mid_y / total_length
        segments = [
            ((x1 - center_x, y1 - center_y), (x2 - center_x, y2 - center_y))
            for (x1, y1), (x2, y2) in segments
        ]

    return segments, text_width * size


def add_vector_label(
    parent: Element,
    text: str,
    x: float,
    y: float,
    angle: float,
    size: float,
    stroke_width: float,
    letter_spacing: float,
) -> None:
    label_group = SubElement(
        parent,
        "g",
        {"transform": f"translate({x:.4f} {y:.4f}) rotate({angle:.4f})"},
    )
    segments, _ = build_label_segments(text, size, letter_spacing)
    for (x1, y1), (x2, y2) in segments:
        SubElement(
            label_group,
            "line",
            {
                "x1": f"{x1:.4f}",
                "y1": f"{y1:.4f}",
                "x2": f"{x2:.4f}",
                "y2": f"{y2:.4f}",
                "stroke": "#000000",
                "stroke-width": f"{stroke_width:.4f}",
                "stroke-linecap": "round",
                "stroke-linejoin": "round",
            },
        )


def label_extent(text: str, size: float, letter_spacing: float) -> tuple[float, float]:
    _, width = build_label_segments(text, size, letter_spacing)
    return width, size


def unequal_hour_label_text(hour_index: int, style: str) -> str:
    if style == "arabic":
        return ARABIC_NUMERALS[hour_index - 1]
    return ROMAN_NUMERALS[hour_index - 1]


def displayed_hour_index(hour_index: int, solar_motion_direction: str) -> int:
    if solar_motion_direction == CLOCKWISE:
        return hour_index
    return 12 - hour_index


def unequal_hour_display_text(
    hour_index: int,
    style: str,
    solar_motion_direction: str,
) -> str:
    return unequal_hour_label_text(displayed_hour_index(hour_index, solar_motion_direction), style)


def neighboring_hour_index(
    hour_index: int,
    toward_larger_label: bool,
    solar_motion_direction: str,
) -> int | None:
    if solar_motion_direction == CLOCKWISE:
        delta = 1 if toward_larger_label else -1
    else:
        delta = -1 if toward_larger_label else 1

    neighbor = hour_index + delta
    if 1 <= neighbor <= 11:
        return neighbor
    return None


def polyline_length(points: Sequence[tuple[float, float]]) -> float:
    return sum(
        math.hypot(points[index][0] - points[index - 1][0], points[index][1] - points[index - 1][1])
        for index in range(1, len(points))
    )


def point_along_polyline(
    points: Sequence[tuple[float, float]],
    distance_from_start: float,
) -> tuple[float, float]:
    if len(points) == 1:
        return points[0]

    remaining = clamp(distance_from_start, 0.0, polyline_length(points))
    for index in range(1, len(points)):
        start = points[index - 1]
        end = points[index]
        segment_length = math.hypot(end[0] - start[0], end[1] - start[1])
        if segment_length <= 1e-12:
            continue
        if remaining <= segment_length:
            t = remaining / segment_length
            return start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t
        remaining -= segment_length
    return points[-1]


def unequal_hour_label_ordered_points(
    observer_latitude: float,
    center: str,
    projection: str,
    radius_scale: float,
    canvas_center: float,
    canvas_radius: float,
    hour_index: int,
    daytime: bool,
) -> list[tuple[float, float]] | None:
    outer_tropic_declination = (
        TROPIC_DECLINATION
        if math.hypot(
            *(
                coordinate - canvas_center
                for coordinate in project_point(
                    TROPIC_DECLINATION,
                    0.0,
                    center,
                    projection,
                    radius_scale,
                    canvas_center,
                )
            )
        )
        >= math.hypot(
            *(
                coordinate - canvas_center
                for coordinate in project_point(
                    -TROPIC_DECLINATION,
                    0.0,
                    center,
                    projection,
                    radius_scale,
                    canvas_center,
                )
            )
        )
        else -TROPIC_DECLINATION
    )

    visible_segments: list[list[tuple[float, float]]] = []
    segment_declinations: list[list[float]] = []
    for segment in sample_temporal_hour_line(
        observer_latitude,
        center,
        projection,
        radius_scale,
        canvas_center,
        hour_index,
        daytime,
    ):
        current_points: list[tuple[float, float]] = []
        current_declinations: list[float] = []
        for sample_index, point in enumerate(segment):
            declination = -TROPIC_DECLINATION + (2.0 * TROPIC_DECLINATION * sample_index / (len(segment) - 1))
            if point_inside_circle(point, canvas_center, canvas_radius):
                current_points.append(point)
                current_declinations.append(declination)
            else:
                if len(current_points) >= 2:
                    visible_segments.append(current_points)
                    segment_declinations.append(current_declinations)
                current_points = []
                current_declinations = []
        if len(current_points) >= 2:
            visible_segments.append(current_points)
            segment_declinations.append(current_declinations)

    if not visible_segments:
        return None

    outer_segment_index = min(
        range(len(visible_segments)),
        key=lambda index: min(
            abs(declination - outer_tropic_declination) for declination in segment_declinations[index]
        ),
    )
    outer_segment = visible_segments[outer_segment_index]
    outer_segment_declinations = segment_declinations[outer_segment_index]
    if len(outer_segment) < 2:
        return None

    target_index = min(
        range(len(outer_segment)),
        key=lambda index: abs(outer_segment_declinations[index] - outer_tropic_declination),
    )
    target_point = outer_segment[target_index]
    target_radius = math.hypot(
        target_point[0] - canvas_center,
        target_point[1] - canvas_center,
    )
    start_radius = math.hypot(
        outer_segment[0][0] - canvas_center,
        outer_segment[0][1] - canvas_center,
    )
    end_radius = math.hypot(
        outer_segment[-1][0] - canvas_center,
        outer_segment[-1][1] - canvas_center,
    )

    # `unequal-hour-label-line-position` should run from the outer tropic-side anchor
    # toward whichever end of the visible line lies farther inward.
    if end_radius < start_radius:
        ordered_points = list(outer_segment[target_index:])
    else:
        ordered_points = list(reversed(outer_segment[: target_index + 1]))

    if len(ordered_points) < 2:
        return None

    return ordered_points


def circle_line_intersections(
    start: tuple[float, float],
    end: tuple[float, float],
    center: float,
    radius: float,
) -> list[tuple[float, float, float]]:
    start_x = start[0] - center
    start_y = start[1] - center
    delta_x = end[0] - start[0]
    delta_y = end[1] - start[1]
    a = delta_x * delta_x + delta_y * delta_y
    if a <= 1e-12:
        return []

    b = 2.0 * (start_x * delta_x + start_y * delta_y)
    c = start_x * start_x + start_y * start_y - radius * radius
    discriminant = b * b - 4.0 * a * c
    if discriminant < 0:
        return []

    root = math.sqrt(discriminant)
    intersections: list[tuple[float, float, float]] = []
    for t in sorted(((-b - root) / (2.0 * a), (-b + root) / (2.0 * a))):
        intersections.append((t, start[0] + delta_x * t, start[1] + delta_y * t))
    return intersections


def shortest_signed_angle_delta(from_angle: float, to_angle: float) -> float:
    return (to_angle - from_angle + math.pi) % (2.0 * math.pi) - math.pi


def hour_line_point_at_radius(
    ordered_points: Sequence[tuple[float, float]],
    canvas_center: float,
    target_radius: float,
) -> tuple[float, float] | None:
    if len(ordered_points) < 2:
        return None

    first_radius = math.hypot(
        ordered_points[0][0] - canvas_center,
        ordered_points[0][1] - canvas_center,
    )
    if abs(first_radius - target_radius) <= 1e-6:
        return ordered_points[0]

    if target_radius > first_radius:
        inward_dx = ordered_points[1][0] - ordered_points[0][0]
        inward_dy = ordered_points[1][1] - ordered_points[0][1]
        outward_end = (
            ordered_points[0][0] - inward_dx,
            ordered_points[0][1] - inward_dy,
        )
        intersections = circle_line_intersections(
            ordered_points[0],
            outward_end,
            canvas_center,
            target_radius,
        )
        for t, x, y in intersections:
            if t >= 0.0:
                return x, y
        return None

    for index in range(1, len(ordered_points)):
        start = ordered_points[index - 1]
        end = ordered_points[index]
        start_radius = math.hypot(start[0] - canvas_center, start[1] - canvas_center)
        end_radius = math.hypot(end[0] - canvas_center, end[1] - canvas_center)
        if (
            min(start_radius, end_radius) - 1e-6
            <= target_radius
            <= max(start_radius, end_radius) + 1e-6
        ):
            intersections = circle_line_intersections(start, end, canvas_center, target_radius)
            for t, x, y in intersections:
                if 0.0 <= t <= 1.0:
                    return x, y
    return None


def polyline_points_at_radius(
    points: Sequence[tuple[float, float]],
    canvas_center: float,
    target_radius: float,
) -> list[tuple[float, float]]:
    intersections: list[tuple[float, float]] = []
    for index in range(1, len(points)):
        start = points[index - 1]
        end = points[index]
        start_radius = math.hypot(start[0] - canvas_center, start[1] - canvas_center)
        end_radius = math.hypot(end[0] - canvas_center, end[1] - canvas_center)
        if (
            min(start_radius, end_radius) - 1e-6
            <= target_radius
            <= max(start_radius, end_radius) + 1e-6
        ):
            for t, x, y in circle_line_intersections(start, end, canvas_center, target_radius):
                if 0.0 <= t <= 1.0:
                    candidate = (x, y)
                    if not any(
                        math.hypot(candidate[0] - existing[0], candidate[1] - existing[1]) <= 1e-6
                        for existing in intersections
                    ):
                        intersections.append(candidate)
    return intersections


def temporal_hour_label_anchor(
    observer_latitude: float,
    center: str,
    projection: str,
    radius_scale: float,
    canvas_center: float,
    canvas_radius: float,
    hour_index: int,
    daytime: bool,
    line_position: float,
    text: str,
    font_size: float,
    letter_spacing: float,
) -> tuple[float, float, float] | None:
    ordered_points = unequal_hour_label_ordered_points(
        observer_latitude,
        center,
        projection,
        radius_scale,
        canvas_center,
        canvas_radius,
        hour_index,
        daytime,
    )
    if ordered_points is None:
        return None

    total_length = polyline_length(ordered_points)
    if line_position >= 0.0:
        anchor = point_along_polyline(ordered_points, total_length * line_position)
    else:
        inward_dx = ordered_points[1][0] - ordered_points[0][0]
        inward_dy = ordered_points[1][1] - ordered_points[0][1]
        inward_length = math.hypot(inward_dx, inward_dy)
        if inward_length <= 1e-12:
            return None
        outward_unit_x = -inward_dx / inward_length
        outward_unit_y = -inward_dy / inward_length
        outward_distance = total_length * abs(line_position)
        anchor = (
            ordered_points[0][0] + outward_unit_x * outward_distance,
            ordered_points[0][1] + outward_unit_y * outward_distance,
        )
    radial_x = anchor[0] - canvas_center
    radial_y = anchor[1] - canvas_center
    radial_length = math.hypot(radial_x, radial_y)
    if radial_length <= 1e-12:
        return None

    x = anchor[0]
    y = anchor[1]

    width, height = label_extent(text, font_size, letter_spacing)
    half_diagonal = math.hypot(width / 2.0, height / 2.0)
    max_center_radius = canvas_radius - half_diagonal
    if max_center_radius <= 0:
        return None

    adjusted_radius = math.hypot(x - canvas_center, y - canvas_center)
    if adjusted_radius > max_center_radius:
        if line_position < 0.0:
            return None
        radial_unit_x = radial_x / radial_length
        radial_unit_y = radial_y / radial_length
        x = canvas_center + radial_unit_x * max_center_radius
        y = canvas_center + radial_unit_y * max_center_radius
        adjusted_radius = max_center_radius

    return x, y, adjusted_radius


def add_azimuth_labels(
    parent: Element,
    observer_latitude: float,
    center: str,
    projection: str,
    radius_scale: float,
    canvas_radius: float,
    font_size: float,
    stroke_width: float,
    position: float,
    center_adjust: float,
    letter_spacing: float,
    solar_motion_direction: str,
) -> None:
    labels = (
        ("N", 0.0),
        ("NE", 45.0),
        ("E", 90.0),
        ("SE", 135.0),
        ("S", 180.0),
        ("SW", 225.0),
        ("W", 270.0),
        ("NW", 315.0),
    )

    for text, azimuth in labels:
        display_azimuth = azimuth
        if solar_motion_direction == COUNTERCLOCKWISE:
            display_azimuth = (-azimuth) % 360.0

        hx, hy = project_horizontal_point(
            observer_latitude, 0.0, display_azimuth, center, projection, radius_scale, canvas_radius
        )
        tx, ty = project_horizontal_point(
            observer_latitude, -18.0, display_azimuth, center, projection, radius_scale, canvas_radius
        )

        delta = 0.2
        h_prev_x, h_prev_y = project_horizontal_point(
            observer_latitude,
            0.0,
            (display_azimuth - delta) % 360.0,
            center,
            projection,
            radius_scale,
            canvas_radius,
        )
        h_next_x, h_next_y = project_horizontal_point(
            observer_latitude,
            0.0,
            (display_azimuth + delta) % 360.0,
            center,
            projection,
            radius_scale,
            canvas_radius,
        )

        tangent_x = h_next_x - h_prev_x
        tangent_y = h_next_y - h_prev_y
        normal_candidates = ((-tangent_y, tangent_x), (tangent_y, -tangent_x))

        to_label_x = tx - hx
        to_label_y = ty - hy
        normal_x, normal_y = max(
            normal_candidates,
            key=lambda normal: normal[0] * to_label_x + normal[1] * to_label_y,
        )

        normal_length = math.hypot(normal_x, normal_y)
        if normal_length > 1e-12:
            normal_unit_x = normal_x / normal_length
            normal_unit_y = normal_y / normal_length
        else:
            normal_unit_x = 0.0
            normal_unit_y = -1.0

        twilight_dx = tx - hx
        twilight_dy = ty - hy
        normal_distance = twilight_dx * normal_unit_x + twilight_dy * normal_unit_y
        x = hx + normal_unit_x * normal_distance * position
        y = hy + normal_unit_y * normal_distance * position

        tangent_length = math.hypot(tangent_x, tangent_y)
        if tangent_length > 1e-12:
            tangent_unit_x = tangent_x / tangent_length
            tangent_unit_y = tangent_y / tangent_length
            x += tangent_unit_x * center_adjust
            y += tangent_unit_y * center_adjust

        angle = math.degrees(math.atan2(normal_y, normal_x)) + 270.0
        add_vector_label(parent, text, x, y, angle, font_size, stroke_width, letter_spacing)


def add_unequal_hour_labels(
    parent: Element,
    observer_latitude: float,
    center: str,
    projection: str,
    radius_scale: float,
    canvas_center: float,
    projection_radius: float,
    font_size: float,
    stroke_width: float,
    line_position: float,
    arc_adjust: float,
    letter_spacing: float,
    label_style: str,
    solar_motion_direction: str,
    daytime: bool,
) -> None:
    horizon_points = sample_horizon(
        observer_latitude,
        center,
        projection,
        radius_scale,
        canvas_center,
    )
    label_layouts: list[tuple[int, str, float, float, float]] = []
    for hour_index in range(1, 12):
        label = unequal_hour_display_text(hour_index, label_style, solar_motion_direction)
        anchor = temporal_hour_label_anchor(
            observer_latitude,
            center,
            projection,
            radius_scale,
            canvas_center,
            projection_radius,
            hour_index,
            daytime,
            line_position,
            label,
            font_size,
            letter_spacing,
        )
        if anchor is None:
            continue

        x, y, radius = anchor
        if arc_adjust != 0.0:
            ordered_points = unequal_hour_label_ordered_points(
                observer_latitude,
                center,
                projection,
                radius_scale,
                canvas_center,
                projection_radius,
                hour_index,
                daytime,
            )
            if ordered_points is not None:
                current_point = hour_line_point_at_radius(ordered_points, canvas_center, radius)
                if current_point is not None:
                    current_angle = math.atan2(
                        current_point[1] - canvas_center,
                        current_point[0] - canvas_center,
                    )
                    neighbor_hour_index = neighboring_hour_index(
                        hour_index,
                        toward_larger_label=arc_adjust > 0.0,
                        solar_motion_direction=solar_motion_direction,
                    )
                    if neighbor_hour_index is not None:
                        neighbor_points = unequal_hour_label_ordered_points(
                            observer_latitude,
                            center,
                            projection,
                            radius_scale,
                            canvas_center,
                            projection_radius,
                            neighbor_hour_index,
                            daytime,
                        )
                        if neighbor_points is not None:
                            neighbor_point = hour_line_point_at_radius(
                                neighbor_points,
                                canvas_center,
                                radius,
                            )
                            if neighbor_point is not None:
                                neighbor_angle = math.atan2(
                                    neighbor_point[1] - canvas_center,
                                    neighbor_point[0] - canvas_center,
                                )
                                angle_delta = shortest_signed_angle_delta(
                                    current_angle,
                                    neighbor_angle,
                                )
                                current_angle += angle_delta * abs(arc_adjust)
                                x = canvas_center + radius * math.cos(current_angle)
                                y = canvas_center + radius * math.sin(current_angle)
                    else:
                        horizon_intersections = polyline_points_at_radius(
                            horizon_points,
                            canvas_center,
                            radius,
                        )
                        if horizon_intersections:
                            candidates = [
                                (
                                    shortest_signed_angle_delta(
                                        current_angle,
                                        math.atan2(
                                            point[1] - canvas_center,
                                            point[0] - canvas_center,
                                        ),
                                    ),
                                    point,
                                )
                                for point in horizon_intersections
                            ]
                            angle_delta, point = min(
                                candidates,
                                key=lambda item: abs(item[0]),
                            )
                            current_angle += angle_delta * abs(arc_adjust)
                            x = canvas_center + radius * math.cos(current_angle)
                            y = canvas_center + radius * math.sin(current_angle)

        label_layouts.append((hour_index, label, x, y, radius))

    for _, label, x, y, _ in label_layouts:
        add_vector_label(parent, label, x, y, 0.0, font_size, stroke_width, letter_spacing)


def evenly_spaced_values(count: int, start: float, stop: float) -> Iterable[float]:
    if count <= 0:
        return []
    step = (stop - start) / count
    return [start + step * index for index in range(count)]


def crosshair_widths(args: argparse.Namespace) -> tuple[float, float]:
    if args.crosshair_horizontal_width is None and args.crosshair_vertical_width is None:
        return args.crosshair_width, args.crosshair_width
    return args.crosshair_horizontal_width or 0.0, args.crosshair_vertical_width or 0.0


def twilight_width(args: argparse.Namespace) -> float:
    if args.twilight_width is not None:
        return args.twilight_width
    return args.astronomical_twilight_width


def radius_scale_for_projection(canvas_radius: float, outer_angle: float, projection: str) -> float:
    if projection == AZIMUTHAL_EQUIDISTANT:
        return canvas_radius / outer_angle
    return canvas_radius / math.tan(math.radians(outer_angle) / 2.0)


def build_svg(args: argparse.Namespace) -> ElementTree:
    crosshair_horizontal_width, crosshair_vertical_width = crosshair_widths(args)
    shared_twilight_width = twilight_width(args)
    margin = max(
        DEFAULT_CANVAS_MARGIN_MM,
        args.boundary_width,
        args.horizon_width,
        args.azimuth_width,
        args.altitude_width,
        shared_twilight_width,
        args.equator_tropics_width,
        args.unequal_hour_width,
        crosshair_horizontal_width,
        crosshair_vertical_width,
        args.azimuth_label_size,
        args.unequal_hour_label_size,
    )
    total_size = args.diameter + margin * 2.0
    canvas_radius = args.diameter / 2.0
    center = canvas_radius + margin
    pole_sign = 1.0 if args.center == "north" else -1.0
    outer_angle = 90.0 - pole_sign * args.range_latitude
    radius_scale = radius_scale_for_projection(canvas_radius, outer_angle, args.projection)
    clip_id = "projection-clip"

    root = Element(
        "svg",
        {
            "xmlns": SVG_NS,
            "width": f"{total_size:.4f}mm",
            "height": f"{total_size:.4f}mm",
            "viewBox": f"0 0 {total_size:.4f} {total_size:.4f}",
        },
    )

    defs = SubElement(root, "defs")
    clip_path = SubElement(defs, "clipPath", {"id": clip_id})
    SubElement(
        clip_path,
        "circle",
        {
            "cx": f"{center:.4f}",
            "cy": f"{center:.4f}",
            "r": f"{canvas_radius:.4f}",
        },
    )

    grid_attributes: dict[str, str] = {}
    if args.rotate_180:
        grid_attributes["transform"] = f"rotate(180 {center:.4f} {center:.4f})"
    grid = SubElement(root, "g", grid_attributes)

    if args.crosshair:
        add_line(
            grid,
            margin,
            center,
            margin + args.diameter,
            center,
            crosshair_horizontal_width,
            clip_id,
        )
        add_line(
            grid,
            center,
            margin,
            center,
            margin + args.diameter,
            crosshair_vertical_width,
            clip_id,
        )

    if args.altitude_lines > 0:
        altitudes = evenly_spaced_values(args.altitude_lines, 90.0 / (args.altitude_lines + 1), 90.0)
        for altitude in altitudes:
            points = sample_altitude_line(
                args.latitude, altitude, args.center, args.projection, radius_scale, center
            )
            add_path(grid, points, args.altitude_width, clip_id, closed=True)

    if args.azimuth_lines > 0:
        azimuths = evenly_spaced_values(args.azimuth_lines, 0.0, 360.0)
        for azimuth in azimuths:
            points = sample_azimuth_line(
                args.latitude, azimuth, args.center, args.projection, radius_scale, center
            )
            for segment in split_by_projection_circle(points, center, canvas_radius):
                add_path(grid, segment, args.azimuth_width, clip_id)

    if args.equator_tropics:
        for declination in (0.0, TROPIC_DECLINATION, -TROPIC_DECLINATION):
            points = sample_declination_line(
                declination, args.center, args.projection, radius_scale, center
            )
            add_path(grid, points, args.equator_tropics_width, clip_id, closed=True)

    if args.day_unequal_hour_lines:
        for hour_index in range(1, 12):
            points_segments = sample_temporal_hour_line(
                args.latitude,
                args.center,
                args.projection,
                radius_scale,
                center,
                hour_index,
                daytime=True,
            )
            for segment in points_segments:
                for visible_segment in split_by_projection_circle(segment, center, canvas_radius):
                    add_path(grid, visible_segment, args.unequal_hour_width, clip_id)

    if args.day_unequal_hour_lines and args.day_unequal_hour_labels:
        label_grid = SubElement(grid, "g", {"clip-path": f"url(#{clip_id})"})
        add_unequal_hour_labels(
            label_grid,
            args.latitude,
            args.center,
            args.projection,
            radius_scale,
            center,
            canvas_radius,
            args.unequal_hour_label_size,
            args.unequal_hour_label_width,
            args.unequal_hour_label_line_position,
            args.unequal_hour_label_arc_adjust,
            args.unequal_hour_label_letter_spacing,
            args.unequal_hour_label_style,
            args.solar_motion_direction,
            daytime=True,
        )

    if args.night_unequal_hour_lines:
        for hour_index in range(1, 12):
            points_segments = sample_temporal_hour_line(
                args.latitude,
                args.center,
                args.projection,
                radius_scale,
                center,
                hour_index,
                daytime=False,
            )
            for segment in points_segments:
                for visible_segment in split_by_projection_circle(segment, center, canvas_radius):
                    add_path(grid, visible_segment, args.unequal_hour_width, clip_id)

    if args.night_unequal_hour_lines and args.night_unequal_hour_labels:
        label_grid = SubElement(grid, "g", {"clip-path": f"url(#{clip_id})"})
        add_unequal_hour_labels(
            label_grid,
            args.latitude,
            args.center,
            args.projection,
            radius_scale,
            center,
            canvas_radius,
            args.unequal_hour_label_size,
            args.unequal_hour_label_width,
            args.unequal_hour_label_line_position,
            args.unequal_hour_label_arc_adjust,
            args.unequal_hour_label_letter_spacing,
            args.unequal_hour_label_style,
            args.solar_motion_direction,
            daytime=False,
        )

    twilight_lines = (
        (args.civil_twilight, -6.0),
        (args.nautical_twilight, -12.0),
        (args.astronomical_twilight, -18.0),
    )
    for enabled, altitude in twilight_lines:
        if not enabled:
            continue
        twilight = sample_altitude_line(
            args.latitude, altitude, args.center, args.projection, radius_scale, center
        )
        add_path(
            grid,
            twilight,
            shared_twilight_width,
            clip_id,
            closed=True,
            dashed=args.twilight_style == "dashed",
        )

    if args.azimuth_labels:
        label_grid = SubElement(grid, "g", {"clip-path": f"url(#{clip_id})"})
        add_azimuth_labels(
            label_grid,
            args.latitude,
            args.center,
            args.projection,
            radius_scale,
            center,
            args.azimuth_label_size,
            args.azimuth_label_width,
            args.azimuth_label_position,
            args.azimuth_label_center_adjust,
            args.azimuth_label_letter_spacing,
            args.solar_motion_direction,
        )

    horizon = sample_horizon(args.latitude, args.center, args.projection, radius_scale, center)
    add_path(grid, horizon, args.horizon_width, clip_id, closed=True)

    if args.boundary_width > 0:
        SubElement(
            root,
            "circle",
            {
                "cx": f"{center:.4f}",
                "cy": f"{center:.4f}",
                "r": f"{canvas_radius:.4f}",
                "fill": "none",
                "stroke": "#000000",
                "stroke-width": f"{args.boundary_width:.4f}",
            },
        )

    return ElementTree(root)


def main(projection: str) -> None:
    args = parse_args(projection)
    validate_args(args)
    tree = build_svg(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(args.output, encoding="utf-8", xml_declaration=True)
