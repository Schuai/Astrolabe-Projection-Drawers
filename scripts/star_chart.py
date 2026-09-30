from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import re
import shutil
import tempfile
import urllib.request
import urllib.error
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Iterable
from xml.etree.ElementTree import Element, ElementTree, SubElement, register_namespace

from astropy.coordinates import FK5, SkyCoord
from astropy.time import Time
import astropy.units as u

from draw_projection import AZIMUTHAL_EQUIDISTANT, STEREOGRAPHIC, ecliptic_to_equatorial, points_to_path, project_point

HYG_VERSION = "4.1"
STELLARIUM_VERSION = "26.1"
HYG_URLS = (
    "https://raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv",
    "https://raw.githubusercontent.com/astronexus/HYG-Database/master/hyg/CURRENT/hygdata_v41.csv",
)
HYG_URL = HYG_URLS[0]
STELLARIUM_URL = "https://github.com/Stellarium/stellarium/archive/refs/tags/v26.1.zip"
SVG_NS = "http://www.w3.org/2000/svg"
POSITIONS = ("north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest")
MAGNITUDE_LEVEL_FLOOR = -1.5
MILKY_WAY_VERSION = "7e720a3de062059d4c5400a379146a601d9010e0"
MILKY_WAY_BASE_URL = f"https://raw.githubusercontent.com/ofrohn/d3-celestial/{MILKY_WAY_VERSION}"
MILKY_WAY_FILES = {"mw.json": "data/mw.json", "LICENSE": "LICENSE", "SOURCE.md": "readme.md"}


def load_milky_way(path: Path) -> list[list[tuple[float, float]]]:
    """Read J2000 equatorial GeoJSON rings, including holes and separate islands."""
    if not path.exists():
        raise FileNotFoundError(f"Milky Way data is missing: {path}. Run download-star-data --milky-way-only.")
    raw = json.loads(path.read_text(encoding="utf-8"))
    rings = []
    try:
        if raw["type"] != "FeatureCollection": raise ValueError()
        for feature in raw["features"]:
            geometry = feature["geometry"]
            if geometry["type"] == "Polygon": polygons = [geometry["coordinates"]]
            elif geometry["type"] == "MultiPolygon": polygons = geometry["coordinates"]
            else: raise ValueError()
            for polygon in polygons:
                for ring in polygon:
                    points = [(float(point[0]), float(point[1])) for point in ring]
                    if len(points) < 4 or points[0] != points[-1]: raise ValueError()
                    if any(not math.isfinite(ra) or not math.isfinite(dec) or not -180 <= ra <= 180 or not -90 <= dec <= 90 for ra, dec in points): raise ValueError()
                    rings.append(points)
        if not rings: raise ValueError()
    except (KeyError, TypeError, IndexError, ValueError) as exc:
        raise ValueError("Invalid Milky Way GeoJSON data") from exc
    return rings


def add_milky_way(group: Element, cache: Path, args: argparse.Namespace, scale: float, center: float, radius: float) -> None:
    rings = load_milky_way(cache / "milkyway" / "mw.json")
    flat = [point for ring in rings for point in ring]
    coordinates = SkyCoord(ra=[p[0] for p in flat] * u.deg, dec=[p[1] for p in flat] * u.deg,
                           frame=FK5(equinox=Time("J2000"))).transform_to(FK5(equinox=Time(f"J{args.epoch_year}")))
    transformed = iter(zip(coordinates.ra.deg, coordinates.dec.deg))
    overlay = SubElement(group, "g", {"id": "star-chart-milky-way", "fill": "none", "stroke": "#000",
                                     "stroke-width": f"{args.milky_way_width:.4f}"})
    for ring in rings:
        vertices = [next(transformed) for _ in ring]
        commands = []
        for first, second in zip(vertices, vertices[1:]):
            inside = [dec >= args.range_declination if args.center == "north" else dec <= args.range_declination for _, dec in (first, second)]
            if not any(inside): continue
            endpoints = [projected_xy(ra / 15, dec, args, scale, center) for ra, dec in (first, second)]
            clipped = clip_segment_to_circle(*endpoints, (center, center), radius)
            if clipped:
                commands.append(points_to_path(clipped, closed=False))
        if commands: SubElement(overlay, "path", {"d": " ".join(commands)})


def default_data_cache() -> Path:
    return Path(__file__).resolve().parent.parent / "src"


@dataclass
class Star:
    id: int
    hip: str
    hd: str
    hr: str
    gaia: str
    ra_hours: float
    dec_degrees: float
    magnitude: float
    proper_name: str
    pmra: float | None = None
    pmdec: float | None = None
    distance_pc: float | None = None
    radial_velocity: float | None = None

    def identifiers(self) -> tuple[str, ...]:
        values = []
        for prefix, value in (("HYG", self.id), ("HIP", self.hip), ("HD", self.hd), ("HR", self.hr), ("GAIA DR3", self.gaia), ("GAIA", self.gaia)):
            if str(value).strip(): values.append(normalize_identifier(f"{prefix} {value}"))
        return tuple(values)


@dataclass
class CultureFigure:
    identifier: str
    english_name: str
    native_name: str
    lines: list[list[str]]


@dataclass
class CultureData:
    identifier: str
    english_name: str
    native_name: str
    figures: list[CultureFigure]
    star_names: dict[str, tuple[str, str]]


@dataclass
class RenderStats:
    stars: int = 0
    segments: int = 0
    star_labels: int = 0
    figure_labels: int = 0
    hidden_labels: int = 0
    missing_identifiers: int = 0
    degraded_motion: int = 0


def normalize_identifier(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value).strip().upper())
    text = text.replace("GAIA DR 3", "GAIA DR3")
    return text


def optional_float(value: str | None) -> float | None:
    try:
        result = float(value) if value not in (None, "") else None
    except ValueError:
        return None
    return result if result is not None and math.isfinite(result) else None


def load_hyg(path: Path) -> list[Star]:
    stars: list[Star] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                ra, dec, mag = float(row["ra"]), float(row["dec"]), float(row["mag"])
            except (KeyError, TypeError, ValueError):
                continue
            distance = optional_float(row.get("dist"))
            if distance is not None and distance >= 100000: distance = None
            stars.append(Star(
                id=int(row.get("id") or 0), hip=(row.get("hip") or "").strip(), hd=(row.get("hd") or "").strip(),
                hr=(row.get("hr") or "").strip(), gaia=(row.get("gaia") or row.get("gaia_dr3") or "").strip(),
                ra_hours=ra, dec_degrees=dec, magnitude=mag, proper_name=(row.get("proper") or "").strip(),
                pmra=optional_float(row.get("pmra")), pmdec=optional_float(row.get("pmdec")),
                distance_pc=distance, radial_velocity=optional_float(row.get("rv")),
            ))
    return stars


def name_parts(value: object) -> tuple[str, str]:
    if isinstance(value, list):
        return name_parts(value[0]) if value else ("", "")
    if isinstance(value, str): return value, value
    if not isinstance(value, dict): return "", ""
    english = str(value.get("english") or value.get("name") or value.get("native") or "")
    native = str(value.get("native") or value.get("name") or english)
    return english, native


def identifier_from_object(value: object) -> str:
    if isinstance(value, bool): return ""
    if isinstance(value, (int, float)): return normalize_identifier(f"HIP {abs(int(value))}")
    if isinstance(value, str):
        stripped = value.strip()
        # Stellarium's JSON uses numeric values for HIP and quoted long numeric
        # strings for Gaia source IDs.
        if re.fullmatch(r"[-+]?\d+", stripped): return normalize_identifier(f"GAIA DR3 {stripped.lstrip('+-')}")
        return normalize_identifier(stripped)
    if isinstance(value, dict):
        for key in ("hip", "HIP", "hd", "HD", "hr", "HR", "gaia", "gaia_dr3", "id", "star", "designation"):
            if key in value:
                raw = value[key]
                lowered = key.lower()
                if lowered == "hip": return normalize_identifier(f"HIP {raw}")
                if lowered == "hd": return normalize_identifier(f"HD {raw}")
                if lowered == "hr": return normalize_identifier(f"HR {raw}")
                if lowered in ("gaia", "gaia_dr3"): return normalize_identifier(f"GAIA DR3 {raw}")
                return identifier_from_object(raw)
    return ""


@lru_cache(maxsize=8)
def load_po_translations(path: Path) -> dict[str, str]:
    """Read the msgid/msgstr subset used by Stellarium sky-culture PO files."""
    if not path.exists(): return {}
    result: dict[str, str] = {}; msgid: list[str] | None = None; msgstr: list[str] | None = None; active = None
    def commit():
        if msgid and msgstr:
            source, translated = "".join(msgid), "".join(msgstr)
            if source and translated: result.setdefault(source, translated)
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines() + [""]:
        line = raw.strip()
        if line.startswith("msgid "):
            commit(); msgid, msgstr, active = [ast.literal_eval(line[6:])], [], "id"
        elif line.startswith("msgstr "):
            msgstr, active = [ast.literal_eval(line[7:])], "str"
        elif line.startswith('"') and active:
            (msgid if active == "id" else msgstr).append(ast.literal_eval(line))
        elif not line:
            commit(); msgid = msgstr = None; active = None
    return result


def load_culture(path: Path) -> CultureData:
    raw = json.loads(path.read_text(encoding="utf-8"))
    culture_id = path.parent.name
    translations = load_po_translations(path.parents[2] / "translations" / "zh_CN.po")
    english, native = name_parts(raw.get("name") or raw.get("common_name") or culture_id.replace("_", " ").title())
    native = translations.get(english, native)
    figures: list[CultureFigure] = []
    # `asterisms` are optional, informal overlays (and may contain internal ray
    # helpers). The constellation/星官 layer intentionally renders only the
    # culture's primary `constellations` collection.
    collection = list(raw.get("constellations") or [])
    if isinstance(collection, dict):
        collection = [dict(value, id=key) if isinstance(value, dict) else {"id": key} for key, value in collection.items()]
    for index, item in enumerate(collection):
        if not isinstance(item, dict): continue
        if item.get("is_ray_helper"): continue
        fig_id = str(item.get("id") or item.get("abbreviation") or index)
        fig_en, fig_native = name_parts(item.get("common_name") or item.get("name") or fig_id)
        fig_native = translations.get(fig_en, fig_native)
        lines: list[list[str]] = []
        for line in item.get("lines") or item.get("edges") or []:
            if isinstance(line, dict): line = line.get("points") or line.get("stars") or []
            ids = [identifier_from_object(point) for point in line]
            ids = [value for value in ids if value]
            if len(ids) >= 2: lines.append(ids)
        figures.append(CultureFigure(fig_id, fig_en, fig_native, lines))
    star_names: dict[str, tuple[str, str]] = {}
    common = raw.get("common_names") or raw.get("star_names") or {}
    if isinstance(common, list):
        common = {identifier_from_object(item): item for item in common if isinstance(item, dict)}
    if isinstance(common, dict):
        for key, value in common.items():
            identifier = identifier_from_object(key) or identifier_from_object(value)
            if identifier:
                names = name_parts(value.get("common_name", value) if isinstance(value, dict) else value)
                star_names[identifier] = (names[0], translations.get(names[0], names[1]))
    return CultureData(culture_id, english, native, figures, star_names)


def available_cultures(cache: Path) -> list[tuple[str, str]]:
    root = cache / "stellarium" / "skycultures"
    result = []
    if root.exists():
        for index in root.glob("*/index.json"):
            try:
                raw = json.loads(index.read_text(encoding="utf-8")); identifier = index.parent.name
                english, _native = name_parts(raw.get("name") or raw.get("common_name") or identifier.replace("_", " ").title())
                result.append((identifier, english or identifier))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
    return sorted(result, key=lambda item: item[1].casefold())


def culture_path(cache: Path, identifier: str) -> Path:
    return cache / "stellarium" / "skycultures" / identifier / "index.json"


def star_index(stars: Iterable[Star]) -> dict[str, Star]:
    result: dict[str, Star] = {}
    for star in stars:
        for identifier in star.identifiers(): result.setdefault(identifier, star)
    return result


def adjusted_position(star: Star, year: int) -> tuple[float, float, bool]:
    kwargs: dict[str, object] = {}
    degraded = False
    if star.pmra is not None and star.pmdec is not None:
        kwargs["pm_ra_cosdec"] = star.pmra * u.mas / u.yr
        kwargs["pm_dec"] = star.pmdec * u.mas / u.yr
        if star.distance_pc:
            kwargs["distance"] = star.distance_pc * u.pc
            if star.radial_velocity is not None: kwargs["radial_velocity"] = star.radial_velocity * u.km / u.s
            else: degraded = True
        else:
            degraded = True
    else:
        degraded = True
    coordinate = SkyCoord(ra=star.ra_hours * 15 * u.deg, dec=star.dec_degrees * u.deg, frame=FK5(equinox=Time("J2000")), obstime=Time("J2000"), **kwargs)
    try:
        if "pm_ra_cosdec" in kwargs: coordinate = coordinate.apply_space_motion(new_obstime=Time(f"J{year}"))
    except Exception:
        degraded = True
    result = coordinate.transform_to(FK5(equinox=Time(f"J{year}")))
    return result.ra.deg / 15.0, result.dec.deg, degraded


def adjusted_positions(stars: Iterable[Star], year: int) -> dict[int, tuple[float, float, bool]]:
    """Vectorized space-motion/precession calculation for interactive rendering."""
    stars = list(stars); result: dict[int, tuple[float, float, bool]] = {}
    target, j2000 = Time(f"J{year}"), Time("J2000")
    complete = [star for star in stars if star.pmra is not None and star.pmdec is not None and star.distance_pc and star.radial_velocity is not None]
    complete_ids = {star.id for star in complete}
    angular = [star for star in stars if star.pmra is not None and star.pmdec is not None and star.id not in complete_ids]
    static = [star for star in stars if star.pmra is None or star.pmdec is None]
    for group, mode, degraded in ((complete, "complete", False), (angular, "angular", True), (static, "static", True)):
        if not group: continue
        kwargs: dict[str, object] = {}
        if mode != "static":
            kwargs.update(pm_ra_cosdec=[star.pmra for star in group] * u.mas/u.yr, pm_dec=[star.pmdec for star in group] * u.mas/u.yr)
        if mode == "complete":
            kwargs.update(distance=[star.distance_pc for star in group] * u.pc, radial_velocity=[star.radial_velocity for star in group] * u.km/u.s)
        coordinates = SkyCoord(ra=[star.ra_hours * 15 for star in group] * u.deg, dec=[star.dec_degrees for star in group] * u.deg,
            frame=FK5(equinox=j2000), obstime=j2000, **kwargs)
        if mode != "static": coordinates = coordinates.apply_space_motion(new_obstime=target)
        transformed = coordinates.transform_to(FK5(equinox=target))
        for star, ra, dec in zip(group, transformed.ra.deg, transformed.dec.deg): result[star.id] = (float(ra) / 15.0, float(dec), degraded)
    return result


def parse_diameters(value: str | Iterable[float]) -> list[float]:
    if isinstance(value, str): values = [float(item.strip()) for item in value.split(",") if item.strip()]
    else: values = [float(item) for item in value]
    if not values or any(item <= 0 for item in values): raise ValueError("star-diameters must contain positive values")
    return values


def resolved_star_diameters(args: argparse.Namespace) -> list[float]:
    """Resolve legacy explicit sizes or linearly interpolate the two endpoints."""
    legacy = getattr(args, "star_diameters", None)
    if legacy:
        values = parse_diameters(legacy)
        if len(values) != args.magnitude_levels: raise ValueError("star-diameters count must equal magnitude-levels")
        return values
    maximum = float(args.star_diameter_max); minimum = float(args.star_diameter_min)
    if maximum <= 0 or minimum <= 0: raise ValueError("star diameters must be positive")
    if maximum < minimum: raise ValueError("star-diameter-max must be greater than or equal to star-diameter-min")
    if args.magnitude_levels == 1: return [maximum]
    return [maximum + (minimum - maximum) * index / (args.magnitude_levels - 1)
            for index in range(args.magnitude_levels)]


def magnitude_level(magnitude: float, minimum: float, maximum: float, levels: int) -> int:
    if maximum <= minimum or levels <= 0: raise ValueError("invalid magnitude range or level count")
    if magnitude <= minimum: return 0
    width = (maximum - minimum) / levels
    return min(levels - 1, max(0, math.ceil((magnitude - minimum) / width) - 1))


def projected_xy(ra_hours: float, dec: float, args: argparse.Namespace, radius_scale: float, canvas_radius: float) -> tuple[float, float]:
    direction = getattr(args, "rotation_direction", "counterclockwise")
    hour_angle = ra_hours * 15.0 * (-1.0 if direction == "clockwise" else 1.0)
    x, y = project_point(dec, hour_angle, args.center, args.projection, radius_scale, canvas_radius)
    angle = math.radians(args.rotation)
    dx, dy = x - canvas_radius, y - canvas_radius
    return canvas_radius + dx * math.cos(angle) - dy * math.sin(angle), canvas_radius + dx * math.sin(angle) + dy * math.cos(angle)


def label_offset(position: str, radial: float, tangential: float) -> tuple[float, float, str]:
    angles = {name: index * 45 - 90 for index, name in enumerate(POSITIONS)}
    angle = math.radians(angles.get(position, -45))
    ux, uy = math.cos(angle), math.sin(angle)
    return ux * radial - uy * tangential, uy * radial + ux * tangential, "middle"


def bbox_for_text(x: float, y: float, text: str, size: float, rotation: float = 0.0) -> tuple[float, float, float, float]:
    width = max(size * 0.55 * len(text), size * 0.6)
    angle = math.radians(rotation)
    cosine, sine = math.cos(angle), math.sin(angle)
    corners = [(x + dx * cosine - dy * sine, y + dx * sine + dy * cosine)
               for dx in (-width / 2, width / 2) for dy in (-size, size * 0.25)]
    return min(p[0] for p in corners), min(p[1] for p in corners), max(p[0] for p in corners), max(p[1] for p in corners)


def overlaps(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> bool:
    return first[0] < second[2] and first[2] > second[0] and first[1] < second[3] and first[3] > second[1]


def clip_segment_to_circle(
    first: tuple[float, float], second: tuple[float, float], center: tuple[float, float], radius: float,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Return only the portion of a segment inside a circular chart boundary."""
    x1, y1 = first; x2, y2 = second; cx, cy = center
    dx, dy = x2 - x1, y2 - y1
    a = dx * dx + dy * dy
    if a <= 1e-24:
        return (first, second) if (x1 - cx) ** 2 + (y1 - cy) ** 2 <= radius * radius else None
    ox, oy = x1 - cx, y1 - cy
    b = 2.0 * (ox * dx + oy * dy)
    c = ox * ox + oy * oy - radius * radius
    discriminant = b * b - 4.0 * a * c
    if discriminant < 0:
        return (first, second) if c <= 0 else None
    root = math.sqrt(max(0.0, discriminant))
    lower, upper = sorted(((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)))
    start, end = max(0.0, lower), min(1.0, upper)
    if start >= end: return None
    return ((x1 + start * dx, y1 + start * dy), (x1 + end * dx, y1 + end * dy))


def render_star_chart(args: argparse.Namespace) -> tuple[bytes, RenderStats]:
    validate_star_args(args)
    cache = Path(args.data_cache)
    hyg_path = cache / "hyg" / "hygdata_v41.csv"
    if not hyg_path.exists(): raise FileNotFoundError(f"Star data is missing: {hyg_path}. Run download-star-data.")
    stars = load_hyg(hyg_path)
    culture = None
    if args.constellation_lines or args.show_constellation_names or args.show_star_names:
        path = culture_path(cache, args.sky_culture)
        if not path.exists(): raise FileNotFoundError(f"Sky culture is missing: {args.sky_culture}. Run download-star-data.")
        culture = load_culture(path)
    margin, radius = 6.0, args.diameter / 2
    total, center = args.diameter + 2 * margin, radius + margin
    pole_sign = 1 if args.center == "north" else -1
    outer_angle = 90 - pole_sign * args.range_declination
    radius_scale = radius / outer_angle if args.projection == AZIMUTHAL_EQUIDISTANT else radius / math.tan(math.radians(outer_angle) / 2)
    register_namespace("", SVG_NS)
    root = Element(f"{{{SVG_NS}}}svg", {"width": f"{total:.4f}mm", "height": f"{total:.4f}mm", "viewBox": f"0 0 {total:.4f} {total:.4f}"})
    defs = SubElement(root, "defs"); clip = SubElement(defs, "clipPath", {"id": "chart-clip"}); SubElement(clip, "circle", {"cx": str(center), "cy": str(center), "r": str(radius)})
    group = SubElement(root, "g", {"clip-path": "url(#chart-clip)"})
    if getattr(args, "milky_way", False): add_milky_way(group, cache, args, radius_scale, center, radius)
    for curve in ("equator", "ecliptic"):
        if not getattr(args, curve, False): continue
        points = []
        for index in range(1440):
            longitude = index / 4.0
            dec, ra = (0.0, longitude) if curve == "equator" else ecliptic_to_equatorial(longitude)
            points.append(projected_xy(ra / 15.0, dec, args, radius_scale, center))
        SubElement(group, "path", {"id": f"star-chart-{curve}", "d": points_to_path(points, closed=True),
                                  "fill": "none", "stroke": "#000", "stroke-width": f"{getattr(args, curve + '_width', 0.1):.4f}"})
    stats, positions, selected = RenderStats(), {}, []
    identifiers = star_index(stars)
    # HYG includes the Sun as a convenience row; it is not a fixed star-chart
    # object. All other stars brighter than the single faint-limit are included.
    candidates = [star for star in stars if star.magnitude <= args.magnitude_max and star.proper_name.casefold() != "sol"]
    magnitude_ids = {star.id for star in candidates}
    needed = {star.id: star for star in candidates}
    coordinates = adjusted_positions(needed.values(), args.epoch_year)
    for star in candidates:
        ra, dec, degraded = coordinates[star.id]
        if (args.center == "north" and dec < args.range_declination) or (args.center == "south" and dec > args.range_declination): continue
        x, y = projected_xy(ra, dec, args, radius_scale, center)
        positions[star.id] = (x, y, star, dec); selected.append(star)
        if degraded: stats.degraded_motion += 1
    occupied: list[tuple[float, float, float, float]] = []
    if culture and args.constellation_lines:
        for figure in culture.figures:
            for line in figure.lines:
                for first_id, second_id in zip(line, line[1:]):
                    first, second = identifiers.get(first_id), identifiers.get(second_id)
                    if not first or not second: stats.missing_identifiers += int(not first) + int(not second); continue
                    if first.id not in magnitude_ids or second.id not in magnitude_ids: continue
                    endpoints = []; endpoint_inside = []
                    for star in (first, second):
                        ra, dec, _ = coordinates[star.id]; endpoints.append(projected_xy(ra, dec, args, radius_scale, center))
                        endpoint_inside.append(dec >= args.range_declination if args.center == "north" else dec <= args.range_declination)
                    # A chord between two projected points outside the polar cap
                    # can falsely cut across the whole chart even though the
                    # actual constellation edge stays outside the declination
                    # range. Only edges anchored by a visible endpoint enter it.
                    if not any(endpoint_inside): continue
                    clipped = clip_segment_to_circle(endpoints[0], endpoints[1], (center, center), radius)
                    if clipped is None: continue
                    SubElement(group, "line", {"x1": f"{clipped[0][0]:.4f}", "y1": f"{clipped[0][1]:.4f}", "x2": f"{clipped[1][0]:.4f}", "y2": f"{clipped[1][1]:.4f}", "stroke": "#000", "stroke-width": f"{args.constellation_width:.4f}"})
                    stats.segments += 1
    diameters = resolved_star_diameters(args)
    for star in sorted(selected, key=lambda value: value.magnitude, reverse=True):
        x, y, _, _ = positions[star.id]
        level_floor = min(MAGNITUDE_LEVEL_FLOOR, args.magnitude_max - 1.0)
        diameter = diameters[magnitude_level(star.magnitude, level_floor, args.magnitude_max, args.magnitude_levels)]
        SubElement(group, "circle", {"cx": f"{x:.4f}", "cy": f"{y:.4f}", "r": f"{diameter/2:.4f}", "fill": "#000" if args.fill_stars else "none", "stroke": "#000", "stroke-width": f"{args.star_stroke_width:.4f}"})
        stats.stars += 1
    def add_label(text: str, x: float, y: float, font: str, size: float, preferred: str, radial: float, tangential: float) -> bool:
        candidates = [preferred] + [item for item in POSITIONS if item != preferred] if args.avoid_label_overlap else [preferred]
        for candidate in candidates:
            dx, dy, anchor = label_offset(candidate, radial, tangential)
            label_x, label_y = x + dx, y + dy
            # SVG text's local top is -Y: turn it toward the circumference.
            rotation = math.degrees(math.atan2(label_x - center, center - label_y)) if (label_x, label_y) != (center, center) else 0.0
            box = bbox_for_text(label_x, label_y, text, size, rotation)
            if args.avoid_label_overlap and any(overlaps(box, other) for other in occupied): continue
            SubElement(group, "text", {"x": f"{label_x:.4f}", "y": f"{label_y:.4f}", "transform": f"rotate({rotation:.4f} {label_x:.4f} {label_y:.4f})", "font-family": font, "font-size": f"{size:.4f}", "text-anchor": anchor, "fill": "#000"}).text = text
            occupied.append(box); return True
        stats.hidden_labels += 1; return False
    if args.show_star_names:
        cultural_names = culture.star_names if culture else {}
        for star in sorted(selected, key=lambda value: value.magnitude):
            names = next((cultural_names[key] for key in star.identifiers() if key in cultural_names), (star.proper_name, star.proper_name))
            text = names[1] if args.star_name_language == "zh" else names[0]
            if text:
                x, y, _, _ = positions[star.id]
                if add_label(text, x, y, args.star_name_font, args.star_name_size, args.star_name_position, args.star_name_radial_offset, args.star_name_tangential_offset): stats.star_labels += 1
    if culture and args.show_constellation_names:
        for figure in culture.figures:
            nodes = []
            for line in figure.lines:
                for identifier in line:
                    star = identifiers.get(identifier)
                    if star and star.id in positions: nodes.append(positions[star.id][:2])
            if nodes:
                text = figure.native_name if args.constellation_name_language == "zh" else figure.english_name
                x, y = sum(p[0] for p in nodes)/len(nodes), sum(p[1] for p in nodes)/len(nodes)
                if text and add_label(text, x, y, args.constellation_name_font, args.constellation_name_size, args.constellation_name_position, args.constellation_name_radial_offset, args.constellation_name_tangential_offset): stats.figure_labels += 1
    SubElement(root, "circle", {"cx": str(center), "cy": str(center), "r": str(radius), "fill": "none", "stroke": "#000", "stroke-width": f"{args.boundary_width:.4f}"})
    from io import BytesIO
    output = BytesIO(); ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    return output.getvalue(), stats


def validate_star_args(args: argparse.Namespace) -> None:
    for curve in ("equator", "ecliptic", "milky_way"):
        width = getattr(args, curve + "_width", 0.1)
        if not math.isfinite(width) or width < 0:
            raise ValueError(f"{curve.replace('_', '-')}-width must be finite and non-negative")
    if not -90 <= args.range_declination <= 90: raise ValueError("range-declination must be within [-90, 90]")
    if args.diameter <= 0: raise ValueError("diameter must be positive")
    if args.magnitude_levels <= 0: raise ValueError("magnitude-levels must be positive")
    resolved_star_diameters(args)
    pole_sign = 1 if args.center == "north" else -1
    outer = 90 - pole_sign * args.range_declination
    if outer <= 0 or (args.projection == STEREOGRAPHIC and outer >= 180): raise ValueError("range-declination is invalid for this projection center")


def _download(url: str, destination: Path) -> str:
    digest = hashlib.sha256(); destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Astrolabe-Star-Chart/0.1", "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=120) as source, destination.open("wb") as target:
        while chunk := source.read(1024 * 1024): target.write(chunk); digest.update(chunk)
    return digest.hexdigest()


def _download_from_sources(urls: Iterable[str], destination: Path) -> tuple[str, str]:
    errors = []
    for url in urls:
        try: return _download(url, destination), url
        except (OSError, urllib.error.URLError) as exc:
            destination.unlink(missing_ok=True); errors.append(f"{url}: {exc}")
    raise OSError("All HYG download sources failed:\n" + "\n".join(errors))


def download_milky_way_data(cache: Path, progress=None) -> dict:
    """Download only the small outline dataset, preserving existing star caches."""
    progress = progress or (lambda _message: None)
    progress("Downloading Milky Way outlines...")
    with tempfile.TemporaryDirectory() as directory:
        stage = Path(directory)
        hashes = {f"milkyway/{name}": _download(f"{MILKY_WAY_BASE_URL}/{source}", stage / name)
                  for name, source in MILKY_WAY_FILES.items()}
        load_milky_way(stage / "mw.json")
        manifest_path = cache / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        target = cache / "milkyway"; target.mkdir(parents=True, exist_ok=True)
        for name in MILKY_WAY_FILES: shutil.copy2(stage / name, target / name)
        manifest.setdefault("files", {}).update(hashes)
        manifest["milky_way"] = {"version": MILKY_WAY_VERSION, "url": f"{MILKY_WAY_BASE_URL}/data/mw.json",
            "source": "Milky Way Outline Catalog, Jose R. Vieira; GeoJSON conversion by Olaf Frohn (d3-celestial)",
            "license": "d3-celestial BSD-3-Clause; upstream attribution preserved in milkyway/SOURCE.md",
            "downloaded_at": datetime.now(timezone.utc).isoformat()}
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def download_star_data(cache: Path, progress=None) -> dict:
    progress = progress or (lambda _message: None)
    with tempfile.TemporaryDirectory() as directory:
        stage = Path(directory) / "cache"; stage.mkdir()
        progress("Downloading HYG 4.1..."); hyg_path = stage / "hyg" / "hygdata_v41.csv"; hyg_hash, hyg_url = _download_from_sources(HYG_URLS, hyg_path)
        with hyg_path.open("r", encoding="utf-8-sig", newline="") as handle:
            fields = set(next(csv.reader(handle), []))
        required = {"id", "hip", "ra", "dec", "mag", "pmra", "pmdec", "dist", "rv"}
        if not required.issubset(fields): raise ValueError("Downloaded HYG file has an invalid schema")
        progress("Downloading Stellarium 26.1 sky cultures...")
        archive = Path(directory) / "stellarium.zip"; stellarium_hash = _download(STELLARIUM_URL, archive)
        extracted = stage / "stellarium"; extracted.mkdir(parents=True)
        with zipfile.ZipFile(archive) as bundle:
            corrupt = bundle.testzip()
            if corrupt: raise ValueError(f"Downloaded Stellarium archive is corrupt: {corrupt}")
            for member in bundle.infolist():
                parts = Path(member.filename).parts
                basename = parts[-1] if parts else ""
                if "skycultures" in parts and (basename == "index.json" or basename.upper().startswith(("LICENSE", "COPYING"))):
                    index = parts.index("skycultures"); relative = Path(*parts[index:])
                elif member.filename.endswith("stellarium-skycultures/zh_CN.po"):
                    relative = Path("translations") / "zh_CN.po"
                else: continue
                target = extracted / relative; target.parent.mkdir(parents=True, exist_ok=True)
                if not member.is_dir(): target.write_bytes(bundle.read(member))
        if not any(extracted.glob("skycultures/*/index.json")): raise ValueError("Downloaded Stellarium archive contains no sky cultures")
        milky_manifest = download_milky_way_data(stage, progress)
        (stage / "manifest.json").unlink()
        file_hashes = {str(path.relative_to(stage)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest() for path in stage.rglob("*") if path.is_file()}
        manifest = {"downloaded_at": datetime.now(timezone.utc).isoformat(), "files": file_hashes,
            "milky_way": milky_manifest["milky_way"],
            "hyg": {"version": HYG_VERSION, "url": hyg_url, "sha256": hyg_hash, "license": "CC BY-SA 4.0"},
            "stellarium": {"version": STELLARIUM_VERSION, "url": STELLARIUM_URL, "sha256": stellarium_hash,
                "license": "GPL-2.0 project; individual sky-culture licenses are preserved in the cache"}}
        cache.mkdir(parents=True, exist_ok=True)
        for name in ("hyg", "stellarium", "milkyway"):
            target = cache / name; shutil.rmtree(target, ignore_errors=True); shutil.move(str(stage / name), str(target))
        load_po_translations.cache_clear()
        (cache / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    progress("Done")
    return manifest


def validate_star_cache(cache: Path) -> list[str]:
    """Return human-readable cache integrity errors without modifying the cache."""
    try: manifest = json.loads((cache / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError): return ["Cache manifest is missing or invalid"]
    errors = []
    for relative, expected in manifest.get("files", {}).items():
        path = cache / relative
        if not path.exists(): errors.append(f"Missing cached file: {relative}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected: errors.append(f"Cached file hash mismatch: {relative}")
    if not manifest.get("files"): errors.append("Cache manifest contains no file hashes")
    return errors
