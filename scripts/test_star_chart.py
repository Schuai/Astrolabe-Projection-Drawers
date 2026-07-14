import csv
import json
import tempfile
import unittest
from pathlib import Path

from draw_star_chart import build_parser
from star_chart import adjusted_position, clip_segment_to_circle, default_data_cache, identifier_from_object, load_culture, load_hyg, magnitude_level, projected_xy, render_star_chart, resolved_star_diameters, validate_star_cache


class StarChartTests(unittest.TestCase):
    def test_requested_star_chart_defaults(self):
        args=build_parser().parse_args([])
        self.assertEqual((args.magnitude_max,args.magnitude_levels,args.star_diameter_max,args.star_diameter_min),(5.0,5,0.7,0.2))

    def test_default_cache_is_repo_src(self):
        self.assertEqual(default_data_cache(), Path(__file__).resolve().parent.parent / "src")

    def fixture(self, root: Path):
        hyg = root / "hyg" / "hygdata_v41.csv"; hyg.parent.mkdir(parents=True)
        rows = [
            {"id":"1","hip":"1","hd":"10","hr":"100","gaia":"1000","ra":"0","dec":"80","mag":"-1.5","proper":"Pole A","pmra":"10","pmdec":"5","dist":"10","rv":"1"},
            {"id":"2","hip":"2","hd":"20","hr":"200","gaia":"2000","ra":"6","dec":"40","mag":"2.5","proper":"Pole B","pmra":"","pmdec":"","dist":"100000","rv":""},
            {"id":"3","hip":"3","hd":"30","hr":"300","gaia":"3000","ra":"12","dec":"-50","mag":"6.5","proper":"Outside","pmra":"","pmdec":"","dist":"","rv":""},
        ]
        with hyg.open("w",encoding="utf-8",newline="") as handle:
            writer=csv.DictWriter(handle,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
        culture=root/"stellarium"/"skycultures"/"modern"/"index.json";culture.parent.mkdir(parents=True)
        culture.write_text(json.dumps({"name":{"english":"Modern","native":"现代"},"constellations":[{"id":"Tst","common_name":{"english":"Test Figure","native":"测试星官"},"lines":[["HIP 1","HIP 2"],["HIP 2","HIP 999"]]}],"common_names":{"HIP 1":{"english":"Alpha","native":"甲星"}}}),encoding="utf-8")
        return hyg,culture

    def test_load_and_identifier_culture(self):
        with tempfile.TemporaryDirectory() as directory:
            hyg,culture=self.fixture(Path(directory));stars=load_hyg(hyg);data=load_culture(culture)
            self.assertEqual(stars[0].hip,"1");self.assertEqual(data.figures[0].native_name,"测试星官")
            self.assertEqual(data.star_names["HIP 1"][1],"甲星")

    def test_magnitude_boundaries(self):
        self.assertEqual(magnitude_level(-1.5,-1.5,6.5,4),0)
        self.assertEqual(magnitude_level(0.5,-1.5,6.5,4),0)
        self.assertEqual(magnitude_level(6.5,-1.5,6.5,4),3)

    def test_star_diameters_are_linearly_interpolated(self):
        args=build_parser().parse_args(["--magnitude-levels","4","--star-diameter-max","1.6","--star-diameter-min","0.4"])
        for actual, expected in zip(resolved_star_diameters(args),[1.6,1.2,0.8,0.4]): self.assertAlmostEqual(actual,expected)
        single=build_parser().parse_args(["--magnitude-levels","1","--star-diameter-max","2","--star-diameter-min","0.5"])
        self.assertEqual(resolved_star_diameters(single),[2.0])

    def test_rotation_direction_changes_handedness_without_moving_zero_hours(self):
        parser = build_parser()
        counterclockwise = parser.parse_args(["--rotation-direction", "counterclockwise"])
        clockwise = parser.parse_args(["--rotation-direction", "clockwise"])
        self.assertEqual(projected_xy(0, 45, counterclockwise, 1, 50), projected_xy(0, 45, clockwise, 1, 50))
        ccw = projected_xy(6, 45, counterclockwise, 1, 50)
        cw = projected_xy(6, 45, clockwise, 1, 50)
        self.assertLess(ccw[0], 50); self.assertGreater(cw[0], 50)
        self.assertAlmostEqual(ccw[1], cw[1])

    def test_single_magnitude_upper_limit_includes_all_brighter_stars(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);hyg,_=self.fixture(root)
            with hyg.open("a",encoding="utf-8",newline="") as handle:
                writer=csv.DictWriter(handle,fieldnames=["id","hip","hd","hr","gaia","ra","dec","mag","proper","pmra","pmdec","dist","rv"])
                writer.writerow({"id":"4","hip":"4","hd":"","hr":"","gaia":"","ra":"3","dec":"70","mag":"-5","proper":"Bright Fixture","pmra":"","pmdec":"","dist":"","rv":""})
                writer.writerow({"id":"0","hip":"","hd":"","hr":"","gaia":"","ra":"0","dec":"0","mag":"-26.7","proper":"Sol","pmra":"","pmdec":"","dist":"","rv":""})
            parser=build_parser();self.assertNotIn("--magnitude-min",parser.format_help())
            args=parser.parse_args(["--data-cache",str(root),"--magnitude-max","3"])
            _,stats=render_star_chart(args)
            self.assertEqual(stats.stars,3)

    def test_constellation_segments_respect_magnitude_and_chart_boundary(self):
        import math
        from xml.etree import ElementTree
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);hyg,culture_path=self.fixture(root)
            with hyg.open("a",encoding="utf-8",newline="") as handle:
                writer=csv.DictWriter(handle,fieldnames=["id","hip","hd","hr","gaia","ra","dec","mag","proper","pmra","pmdec","dist","rv"])
                writer.writerow({"id":"5","hip":"5","hd":"","hr":"","gaia":"","ra":"0","dec":"-50","mag":"6","proper":"Outside Pair","pmra":"","pmdec":"","dist":"","rv":""})
            culture=json.loads(culture_path.read_text(encoding="utf-8"));culture["constellations"][0]["lines"].extend([["HIP 2","HIP 3"],["HIP 3","HIP 5"]])
            culture_path.write_text(json.dumps(culture),encoding="utf-8")
            limited=build_parser().parse_args(["--data-cache",str(root),"--magnitude-max","3"])
            _,limited_stats=render_star_chart(limited)
            self.assertEqual(limited_stats.segments,1)
            full=build_parser().parse_args(["--data-cache",str(root),"--magnitude-max","6.5"])
            svg,full_stats=render_star_chart(full);self.assertEqual(full_stats.segments,2)
            document=ElementTree.fromstring(svg);center=66.0;radius=60.0
            for line in document.findall(".//{http://www.w3.org/2000/svg}line"):
                for x,y in ((float(line.attrib["x1"]),float(line.attrib["y1"])),(float(line.attrib["x2"]),float(line.attrib["y2"]))):
                    self.assertLessEqual(math.hypot(x-center,y-center),radius+1e-3)

    def test_circle_segment_clipping(self):
        self.assertEqual(clip_segment_to_circle((-2,0),(2,0),(0,0),1),((-1.0,0.0),(1.0,0.0)))
        self.assertIsNone(clip_segment_to_circle((2,2),(3,3),(0,0),1))

    def test_epoch_and_render(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);hyg,_=self.fixture(root);star=load_hyg(hyg)[0]
            ra,dec,degraded=adjusted_position(star,2050);self.assertFalse(degraded);self.assertNotEqual(ra,star.ra_hours)
            args=build_parser().parse_args(["--data-cache",str(root),"--magnitude-levels","2","--star-diameters","1.2,0.5","--show-star-names","--show-constellation-names","--constellation-name-language","zh","--no-avoid-label-overlap"])
            svg,stats=render_star_chart(args)
            self.assertIn(b"Alpha",svg);self.assertIn("测试星官".encode(),svg)
            self.assertEqual(stats.stars,2);self.assertEqual(stats.segments,1);self.assertGreaterEqual(stats.missing_identifiers,1)

            inverse=build_parser().parse_args(["--data-cache",str(root),"--show-star-names","--star-name-language","zh","--show-constellation-names","--constellation-name-language","en","--no-avoid-label-overlap"])
            inverse_svg,_=render_star_chart(inverse)
            self.assertIn("甲星".encode(),inverse_svg);self.assertIn(b"Test Figure",inverse_svg)

    def test_diameter_count_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root);args=build_parser().parse_args(["--data-cache",str(root),"--magnitude-levels","3","--star-diameters","1,2"])
            with self.assertRaisesRegex(ValueError,"count"):render_star_chart(args)

    def test_diameter_endpoint_validation(self):
        args=build_parser().parse_args(["--star-diameter-max","0.4","--star-diameter-min","1.0"])
        with self.assertRaisesRegex(ValueError,"greater than or equal"):resolved_star_diameters(args)

    def test_real_stellarium_numeric_hip_and_name_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"stellarium"/"skycultures"/"modern"/"index.json";path.parent.mkdir(parents=True)
            translation=Path(directory)/"stellarium"/"translations"/"zh_CN.po";translation.parent.mkdir(parents=True)
            translation.write_text('msgid "Alpha"\nmsgstr "阿尔法"\n\nmsgid "Test"\nmsgstr "测试星座"\n',encoding="utf-8")
            path.write_text(json.dumps({"id":"modern","constellations":[{"id":"CON modern T","common_name":{"english":"Test"},"lines":[[1,2,-3]]}],"asterisms":[{"id":"AST helper","is_ray_helper":True,"lines":[[1,999]]},{"id":"AST optional","common_name":{"english":"Optional"},"lines":[[1,2]]}],"common_names":{"HIP 1":[{"english":"Alpha","native":"Alpha Native"}]}}),encoding="utf-8")
            culture=load_culture(path)
            self.assertEqual(culture.english_name,"Modern");self.assertEqual(len(culture.figures),1);self.assertEqual(culture.figures[0].lines[0],["HIP 1","HIP 2","HIP 3"])
            self.assertEqual(culture.figures[0].native_name,"测试星座");self.assertEqual(culture.star_names["HIP 1"],("Alpha","阿尔法"))
            self.assertEqual(identifier_from_object("5350358584482202880"),"GAIA DR3 5350358584482202880")

    def test_cache_hash_mismatch_is_reported(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);item=root/"hyg"/"hygdata_v41.csv";item.parent.mkdir();item.write_text("original",encoding="utf-8")
            digest=hashlib.sha256(item.read_bytes()).hexdigest();(root/"manifest.json").write_text(json.dumps({"files":{"hyg/hygdata_v41.csv":digest}}),encoding="utf-8")
            self.assertEqual(validate_star_cache(root),[]);item.write_text("changed",encoding="utf-8")
            self.assertIn("hash mismatch",validate_star_cache(root)[0])


if __name__=="__main__":unittest.main()
