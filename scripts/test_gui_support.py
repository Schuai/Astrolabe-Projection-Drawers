import unittest
import os
import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from astrolabe_gui import tokenize_config
from draw_projection import AZIMUTHAL_EQUIDISTANT, STEREOGRAPHIC, parse_args, svg_bytes


class ConfigTests(unittest.TestCase):
    def test_star_chart_plain_args_and_comma_list(self):
        from draw_star_chart import build_parser
        tokens = tokenize_config("pixi run draw-star-chart -- --projection stereographic --magnitude-levels 2 --star-diameters 1.2,0.5")
        self.assertEqual(tokens[0], "draw-star-chart")
        args = build_parser().parse_args(tokens[1:])
        self.assertEqual(args.projection, "stereographic")
        self.assertEqual(args.star_diameters, "1.2,0.5")

    def test_powershell_readme_command(self):
        text = '''pixi run draw-stereographic -- @(
          "--latitude", "50", "--center", "south",
          "--range-latitude", "23.5", "--diameter", "40", "--crosshair"
        )'''
        tokens = tokenize_config(text)
        self.assertEqual(tokens[0], "draw-stereographic")
        args = parse_args(STEREOGRAPHIC, tokens[1:])
        self.assertTrue(args.crosshair)
        self.assertEqual(args.latitude, 50)

    def test_in_memory_svg(self):
        args = parse_args(STEREOGRAPHIC, [
            "--latitude", "50", "--center", "south",
            "--range-latitude", "23.5", "--diameter", "40",
        ])
        result = svg_bytes(args)
        self.assertIn(b"<svg", result)
        self.assertIn(b"mm", result)

    def test_readme_chooses_runnable_example_not_help(self):
        text = '''```powershell
pixi run draw-stereographic -- --help
```
```powershell
pixi run draw-stereographic -- @(
 "--latitude", "50", "--center", "south",
 "--range-latitude", "23.5", "--diameter", "40"
)
```'''
        tokens = tokenize_config(text)
        self.assertEqual(tokens[:3], ["draw-stereographic", "--latitude", "50"])

    def test_azimuthal_ecliptic_band_is_constant_normal_offset(self):
        import math
        from draw_projection import (
            AZIMUTHAL_EQUIDISTANT, ecliptic_circle_center,
            offset_closed_curve_toward_center, projection_geometry,
            radius_scale_for_projection, sample_ecliptic_line,
        )
        args = parse_args(AZIMUTHAL_EQUIDISTANT, [
            "--latitude", "35", "--center", "north", "--range-latitude", "-55",
            "--diameter", "40", "--ecliptic", "--ecliptic-band-width", "2",
        ])
        _, _, canvas_radius, center = projection_geometry(args)
        radius_scale = radius_scale_for_projection(canvas_radius, 90 - args.range_latitude, args.projection)
        outer = sample_ecliptic_line(args.center, args.projection, radius_scale, center)
        interior = ecliptic_circle_center(args.center, args.projection, radius_scale, center)
        inner = offset_closed_curve_toward_center(outer, interior, 2.0)
        distances = [math.dist(a, b) for a, b in zip(outer[:-1], inner[:-1])]
        self.assertLess(max(abs(distance - 2.0) for distance in distances), 1e-9)
        unique_outer = outer[:-1]
        for index in range(0, len(unique_outer), 60):
            previous, following = unique_outer[(index - 1) % len(unique_outer)], unique_outer[(index + 1) % len(unique_outer)]
            tangent = (following[0] - previous[0], following[1] - previous[1])
            offset = (inner[index][0] - outer[index][0], inner[index][1] - outer[index][1])
            self.assertLess(abs(tangent[0] * offset[0] + tangent[1] * offset[1]), 1e-7)


class LanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_projection_tab_retranslates_immediately(self):
        from astrolabe_gui import ProjectionTab
        language = ["en"]
        tab = ProjectionTab("draw-stereographic", STEREOGRAPHIC, lambda: language[0])
        self.assertEqual(tab.update_button.text(), "Update Preview")
        language[0] = "zh"; tab.retranslate()
        self.assertEqual(tab.update_button.text(), "更新预览")
        self.assertEqual(tab.rows["latitude"][0].text(), "观察者纬度（--latitude）")
        self.assertEqual(tab.widgets["center"].currentText(), "南极")
        self.assertIn("观察者纬度", tab.rows["latitude"][0].toolTip())

    def test_tooltip_uses_readme_and_translates(self):
        from astrolabe_gui import ProjectionTab, README_HELP_EN
        language = ["en"]
        tab = ProjectionTab("draw-stereographic", STEREOGRAPHIC, lambda: language[0])
        self.assertEqual(tab.rows["azimuth_lines"][0].toolTip(), README_HELP_EN["--azimuth-lines"])
        language[0] = "zh"; tab.retranslate()
        self.assertIn("每隔 N 度", tab.rows["azimuth_lines"][0].toolTip())
        self.assertNotIn("Draw azimuth", tab.rows["azimuth_lines"][0].toolTip())

    def test_gui_help_uses_readme_and_has_chinese_translation(self):
        from astrolabe_gui import gui_help_markdown
        self.assertIn("pixi run gui", gui_help_markdown("en"))
        self.assertIn("Ad astra abyssosque", gui_help_markdown("en"))
        self.assertIn("向着星辰与深渊，欢迎使用本星盘辅助设计工具！", gui_help_markdown("zh"))
        self.assertIn("File > Export Configuration", gui_help_markdown("en"))
        self.assertIn("文件 > 导出配置", gui_help_markdown("zh"))
        self.assertIn("300 DPI", gui_help_markdown("zh"))

    def test_about_is_standalone_and_localized(self):
        from astrolabe_gui import MainWindow, REPOSITORY_URL, about_markdown
        self.assertIn(REPOSITORY_URL, about_markdown("en"))
        self.assertIn("Ad astra abyssosque", about_markdown("en"))
        self.assertIn("向着星辰与深渊，欢迎使用本星盘辅助设计工具！", about_markdown("zh"))
        self.assertIn("GPL-3.0", about_markdown("en")); self.assertIn("CC BY-SA 4.0", about_markdown("en"))
        self.assertIn("数据来源与许可", about_markdown("zh")); self.assertIn("Stellarium 26.1", about_markdown("zh"))
        window = MainWindow()
        self.assertIn(window.about_action, window.menuBar().actions())
        self.assertNotIn(window.about_action, window.help_menu.actions())
        window.set_language("en")
        self.assertEqual(window.about_action.text(), "About")
        window.set_language("zh"); self.assertEqual(window.about_action.text(), "关于")
        window.close()

    def test_raster_export_uses_configured_dpi(self):
        from astrolabe_gui import ProjectionTab
        from PySide6.QtGui import QImage
        tab = ProjectionTab("draw-stereographic", STEREOGRAPHIC, lambda: "en", lambda: 100)
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="25.4mm" height="12.7mm" viewBox="0 0 25.4 12.7"/>'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dpi.png"
            tab._write_raster(svg, path)
            image = QImage(str(path))
            self.assertEqual((image.width(), image.height()), (100, 50))

    def test_gui_defaults_follow_readme_examples(self):
        from astrolabe_gui import ProjectionTab
        from draw_projection import AZIMUTHAL_EQUIDISTANT
        az = ProjectionTab("draw-azimuthal-equidistant", AZIMUTHAL_EQUIDISTANT, lambda: "en")
        stereo = ProjectionTab("draw-stereographic", STEREOGRAPHIC, lambda: "en")
        self.assertEqual((az.value("latitude"), az.value("center"), az.value("range_latitude")), (35.0, "north", -55.0))
        self.assertEqual((stereo.value("latitude"), stereo.value("center"), stereo.value("range_latitude")), (50.0, "south", 23.5))
        self.assertEqual(stereo.value("boundary_width"), 0.1)
        self.assertTrue(stereo.value("civil_twilight"))
        self.assertEqual(stereo.value("unequal_hour_label_line_position"), 0.1)
        for tab in (az, stereo):
            self.assertTrue(tab.value("ecliptic"))
            self.assertEqual(tab.value("ecliptic_width"), 0.17)
            self.assertEqual(tab.value("ecliptic_angle_lines"), 30.0)
            self.assertTrue(tab.value("date_ring"))
            self.assertEqual(tab.value("date_ring_sub_interval"), 1)
            self.assertEqual(tab.value("date_ring_sub_sub_interval"), 5)

    def test_svg_preview_preserves_aspect_ratio(self):
        from astrolabe_gui import ProjectionTab
        from PySide6.QtCore import Qt
        tab = ProjectionTab("draw-stereographic", STEREOGRAPHIC, lambda: "en")
        tab.update_preview()
        self.assertEqual(tab.main_view.renderer().aspectRatioMode(), Qt.AspectRatioMode.KeepAspectRatio)
        self.assertEqual(tab.ecliptic_view.renderer().aspectRatioMode(), Qt.AspectRatioMode.KeepAspectRatio)

    def test_preview_validation_error_follows_language(self):
        from astrolabe_gui import ProjectionTab
        language = ["zh"]
        tab = ProjectionTab("draw-stereographic", STEREOGRAPHIC, lambda: language[0])
        tab.set_value("diameter", -1)
        tab.update_preview()
        self.assertIn("投影直径必须大于 0", tab.status.text())
        self.assertNotIn("must be positive", tab.status.text())

    def test_ecliptic_update_preserves_current_preview_tab(self):
        from astrolabe_gui import ProjectionTab
        tab = ProjectionTab("draw-stereographic", STEREOGRAPHIC, lambda: "en")
        tab.set_value("ecliptic", True)
        tab.set_value("ecliptic_width", 0.7)
        tab.set_value("date_ring", True)
        tab.update_preview()
        self.assertIsNotNone(tab.ecliptic_svg)
        self.assertEqual(tab.preview_tabs.count(), 2)
        self.assertIs(tab.preview_tabs.currentWidget(), tab.main_view)
        self.assertEqual(tab.preview_tabs.tabText(1), "Ecliptic")
        tab.preview_tabs.setCurrentWidget(tab.ecliptic_view)
        tab.update_preview()
        self.assertIs(tab.preview_tabs.currentWidget(), tab.ecliptic_view)

    def test_ecliptic_tab_is_visible_but_disabled_before_generation(self):
        from astrolabe_gui import ProjectionTab
        tab = ProjectionTab("draw-stereographic", STEREOGRAPHIC, lambda: "en")
        self.assertEqual(tab.preview_tabs.count(), 2)
        self.assertEqual(tab.preview_tabs.tabText(1), "Ecliptic")
        self.assertFalse(tab.preview_tabs.isTabEnabled(1))

    def test_partial_update_reports_each_preview_without_switching(self):
        from astrolabe_gui import ProjectionTab
        tab = ProjectionTab("draw-stereographic", STEREOGRAPHIC, lambda: "en")
        companion = b'<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm"/>'
        def render(_args, *, ecliptic=False):
            if not ecliptic: raise ValueError("diameter must be positive.")
            return companion
        with patch("astrolabe_gui.svg_bytes", side_effect=render): tab.update_preview()
        self.assertIs(tab.preview_tabs.currentWidget(), tab.main_view)
        self.assertIn("Main preview failed", tab.status.text())
        self.assertIn("Ecliptic preview updated", tab.status.text())

    def test_responsive_parameter_layout(self):
        from astrolabe_gui import ProjectionTab
        from PySide6.QtWidgets import QFormLayout
        from PySide6.QtCore import Qt
        language = ["en"]
        tab = ProjectionTab("draw-stereographic", STEREOGRAPHIC, lambda: language[0])
        tab.apply_responsive_layout(900)
        self.assertEqual(tab.form.rowWrapPolicy(), QFormLayout.RowWrapPolicy.WrapAllRows)
        self.assertTrue(tab.rows["latitude"][0].wordWrap())
        self.assertEqual(tab.main_view.minimumWidth(), 220)
        self.assertEqual(tab.scroll.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        language[0] = "zh"; tab.retranslate(); tab.apply_responsive_layout(1400)
        self.assertEqual(tab.form.rowWrapPolicy(), QFormLayout.RowWrapPolicy.DontWrapRows)
        self.assertFalse(tab.rows["latitude"][0].wordWrap())
        self.assertEqual(tab.main_view.minimumWidth(), 420)

    def test_numeric_wheel_is_ignored(self):
        from astrolabe_gui import NoWheelDoubleSpinBox
        class Event:
            ignored = False
            def ignore(self): self.ignored = True
        box = NoWheelDoubleSpinBox(); box.setValue(12.5); event = Event(); box.wheelEvent(event)
        self.assertTrue(event.ignored)
        self.assertEqual(box.value(), 12.5)

    def test_exported_configuration_round_trips(self):
        from astrolabe_gui import ProjectionTab, tokenize_config
        tab = ProjectionTab("draw-stereographic", STEREOGRAPHIC, lambda: "en")
        tab.set_value("latitude", 49.5)
        tab.set_value("ecliptic", True)
        tab.set_value("date_ring", True)
        text = tab.export_config_text()
        tokens = tokenize_config(text)
        args = parse_args(STEREOGRAPHIC, tokens[1:])
        self.assertEqual(tokens[0], "draw-stereographic")
        self.assertEqual(args.latitude, 49.5)
        self.assertTrue(args.ecliptic)
        self.assertTrue(args.date_ring)

    def test_star_chart_endpoint_diameters_preview_and_config(self):
        from astrolabe_gui import StarChartTab
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hyg = root / "hyg" / "hygdata_v41.csv"; hyg.parent.mkdir(parents=True)
            rows = [
                {"id":"1","hip":"1","hd":"","hr":"","gaia":"","ra":"0","dec":"80","mag":"0","proper":"Pole","pmra":"","pmdec":"","dist":"","rv":""},
                {"id":"2","hip":"2","hd":"","hr":"","gaia":"","ra":"6","dec":"40","mag":"2","proper":"Second","pmra":"","pmdec":"","dist":"","rv":""},
            ]
            with hyg.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
            culture = root / "stellarium" / "skycultures" / "modern" / "index.json"; culture.parent.mkdir(parents=True)
            culture.write_text(json.dumps({"name":"Modern","constellations":[{"id":"T","name":"Test","lines":[["HIP 1","HIP 2"]]}]}), encoding="utf-8")
            tab = StarChartTab(lambda: "en", dpi=lambda: 72, cache=root)
            tab.set_value("magnitude_levels", 3); tab.set_value("star_diameter_max", 1.2); tab.set_value("star_diameter_min", 0.4)
            self.assertNotIn("star_diameters", tab.widgets)
            tab.update_preview(); self.assertIn(b"<svg", tab.main_svg); self.assertIn("2 stars", tab.status.text())
            tokens = tokenize_config(tab.export_config_text()); self.assertEqual(tokens[0], "draw-star-chart")
            clone = StarChartTab(lambda: "en", cache=root); clone.import_args(tokens[1:])
            self.assertEqual((clone.value("magnitude_levels"),clone.value("star_diameter_max"),clone.value("star_diameter_min")),(3,1.2,0.4))
            svg_path, png_path, jpg_path = root/"chart.svg", root/"chart.png", root/"chart.jpg"
            tab.save(svg_path); tab.save(png_path); tab.save(jpg_path)
            self.assertIn(b"<svg", svg_path.read_bytes())
            from PySide6.QtGui import QImage
            png, jpg = QImage(str(png_path)), QImage(str(jpg_path))
            self.assertFalse(png.isNull()); self.assertEqual(png.pixelColor(0, 0).alpha(), 0)
            self.assertFalse(jpg.isNull()); self.assertGreater(jpg.pixelColor(0, 0).red(), 240)

    def test_star_chart_gui_uses_requested_defaults(self):
        from astrolabe_gui import StarChartTab
        tab=StarChartTab(lambda:"en")
        self.assertEqual((tab.value("magnitude_max"),tab.value("magnitude_levels"),tab.value("star_diameter_max"),tab.value("star_diameter_min")),(5.0,5,0.7,0.2))
        tab.close()

    def test_star_chart_reference_curve_controls_and_config(self):
        from astrolabe_gui import StarChartTab
        tab = StarChartTab(lambda: "zh")
        clone = StarChartTab(lambda: "zh")
        try:
            for curve in ("equator", "ecliptic", "milky_way"):
                self.assertFalse(tab.value(curve))
                self.assertTrue(tab.rows[curve + "_width"][0].isHidden())
                tab.set_value(curve, True)
                tab.set_value(curve + "_width", 0.27)
                self.assertFalse(tab.rows[curve + "_width"][0].isHidden())
            clone.import_args(tab.export_args())
            for curve in ("equator", "ecliptic", "milky_way"):
                self.assertTrue(getattr(clone.namespace(), curve))
                self.assertEqual(clone.value(curve + "_width"), 0.27)
        finally:
            tab.close(); clone.close()

    def test_legacy_per_level_diameters_import_as_endpoints(self):
        from astrolabe_gui import StarChartTab
        tab=StarChartTab(lambda:"en")
        tab.import_args(["--magnitude-levels","3","--star-diameters","1.5,0.9,0.3"])
        self.assertEqual((tab.value("star_diameter_max"),tab.value("star_diameter_min")),(1.5,0.3))
        exported=tab.export_args();self.assertIn("--star-diameter-max",exported);self.assertNotIn("--star-diameters",exported)
        tab.close()

    def test_star_and_constellation_label_languages_are_independent_of_gui_language(self):
        from astrolabe_gui import StarChartTab
        language = ["en"]
        tab = StarChartTab(lambda: language[0])
        tab.set_value("show_star_names", True); tab.set_value("show_constellation_names", True)
        tab.set_value("star_name_language", "zh"); tab.set_value("constellation_name_language", "en")
        tab.refresh_visibility(); tab.retranslate()
        self.assertFalse(tab.rows["star_name_language"][0].isHidden())
        self.assertFalse(tab.rows["constellation_name_language"][0].isHidden())
        self.assertEqual(tab.widgets["star_name_language"].currentText(), "Chinese")
        self.assertEqual(tab.widgets["constellation_name_language"].currentText(), "English")
        language[0] = "zh"; tab.retranslate()
        self.assertEqual((tab.value("star_name_language"), tab.value("constellation_name_language")), ("zh", "en"))
        self.assertEqual(tab.widgets["star_name_language"].currentText(), "汉语")
        self.assertEqual(tab.widgets["constellation_name_language"].currentText(), "英语")
        tab.close()

    def test_star_chart_missing_data_error_is_localized(self):
        from astrolabe_gui import StarChartTab
        with tempfile.TemporaryDirectory() as directory:
            tab = StarChartTab(lambda: "zh", cache=Path(directory)); tab.update_preview()
            self.assertIn("缺少恒星数据", tab.status.text()); self.assertNotIn("Star data is missing", tab.status.text())

    def test_projection_workspace_has_peer_drawing_pages(self):
        from astrolabe_gui import ProjectionWorkspace, tokenize_workspace_config
        from draw_star_chart import build_parser as build_star_parser
        workspace = ProjectionWorkspace("draw-stereographic", STEREOGRAPHIC, lambda: "en")
        self.assertEqual(workspace.pages.count(), 5)
        self.assertEqual([workspace.pages.tabText(i) for i in range(5)], ["Main", "Ecliptic", "Star Chart", "Back", "Ruler"])
        self.assertEqual([section.title() for section in workspace.sections], ["Main", "Ecliptic", "Star Chart", "Back", "Ruler"])
        self.assertTrue(workspace.projection_controls.rows["ecliptic"][0].isHidden())
        self.assertFalse(workspace.projection_controls.rows["azimuth_lines"][0].isHidden())
        self.assertFalse(workspace.projection_controls.rows["date_ring"][0].isHidden())
        for name in ("center", "range_declination", "projection", "diameter", "boundary_width", "rotation", "rotation_direction"):
            self.assertTrue(workspace.star_chart.rows[name][0].isHidden())
        self.assertEqual(workspace.star_chart.namespace().projection, STEREOGRAPHIC)
        workspace.projection_controls.set_value("center", "north")
        workspace.projection_controls.set_value("range_latitude", -42.0)
        workspace.projection_controls.set_value("diameter", 88.0)
        workspace.projection_controls.set_value("boundary_width", 0.35)
        shared = workspace.star_namespace()
        self.assertEqual((shared.center, shared.range_declination, shared.projection), ("north", -42.0, STEREOGRAPHIC))
        self.assertEqual((shared.diameter, shared.boundary_width), (88.0, 0.35))
        self.assertEqual((shared.rotation, shared.rotation_direction), (0.0, "counterclockwise"))
        workspace.projection_controls.set_value("ecliptic_rotation_direction", "clockwise")
        self.assertEqual(workspace.star_namespace().rotation_direction, "clockwise")
        workspace.projection_controls.set_value("latitude", 42.25)
        workspace.star_chart.set_value("magnitude_max", 5.75)
        commands = tokenize_workspace_config(workspace.export_config_text())
        self.assertEqual([command[0] for command in commands], ["draw-stereographic", "draw-star-chart", "draw-astrolabe-back", "draw-astrolabe-ruler"])
        self.assertIn("--ecliptic", commands[0]); self.assertIn("--projection", commands[1])
        exported_star = build_star_parser().parse_args(commands[1][1:])
        self.assertEqual((exported_star.center, exported_star.range_declination, exported_star.diameter, exported_star.boundary_width), ("north", -42.0, 88.0, 0.35))
        self.assertEqual((exported_star.rotation, exported_star.rotation_direction), (0.0, "clockwise"))
        clone = ProjectionWorkspace("draw-stereographic", STEREOGRAPHIC, lambda: "en")
        clone.import_projection(commands[0][1:]); clone.import_star(commands[1][1:])
        self.assertEqual(clone.projection_controls.value("latitude"), 42.25)
        self.assertEqual(clone.star_chart.value("magnitude_max"), 5.75)
        workspace.resize(850, 500); workspace.show(); self.app.processEvents()
        preview_views = (workspace.projection_controls.main_view, workspace.projection_controls.ecliptic_view, workspace.star_chart.preview)
        for index, view in enumerate(preview_views):
            workspace.select_index(index); self.app.processEvents()
            self.assertTrue(view.isVisible())
            self.assertTrue(workspace.page_widgets[index].isAncestorOf(view))
        first_label=workspace.projection_controls.rows["date_ring_sub_sub_width"][0]
        second_label=workspace.projection_controls.rows["date_ring_sub_sub_interval"][0]
        self.assertGreaterEqual(first_label.width(),230)
        self.assertGreaterEqual(first_label.height(),first_label.heightForWidth(first_label.width()))
        self.assertLessEqual(first_label.mapTo(workspace.ecliptic_section,first_label.rect().bottomLeft()).y(),second_label.mapTo(workspace.ecliptic_section,second_label.rect().topLeft()).y())
        workspace.select_index(0); self.app.processEvents()
        scrollbar = workspace.scroll.verticalScrollBar(); scrollbar.setValue(0); self.assertEqual(scrollbar.value(), 0)
        workspace.select_index(2); self.app.processEvents(); self.assertGreater(scrollbar.value(), 0)
        from types import SimpleNamespace
        sample=b'<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm"/>'
        stats=SimpleNamespace(stars=2,segments=1,star_labels=0,figure_labels=0,hidden_labels=0,missing_identifiers=0,degraded_motion=0)
        workspace.select_index(1)
        with patch("astrolabe_gui.svg_bytes",return_value=sample) as projection_render,patch("astrolabe_gui.render_star_chart",return_value=(sample,stats)) as star_render:
            workspace.update_preview()
        self.assertEqual(projection_render.call_count,2);self.assertEqual(star_render.call_count,1)
        self.assertIsNotNone(workspace.projection_controls.main_svg);self.assertIsNotNone(workspace.projection_controls.ecliptic_svg);self.assertIsNotNone(workspace.star_chart.main_svg)
        self.assertEqual(workspace.current_index(),1)
        self.assertIn("Ecliptic preview updated", workspace.status.text())
        workspace.close(); clone.close()

    def test_main_window_nests_star_charts_under_projections(self):
        from astrolabe_gui import MainWindow, ProjectionWorkspace
        window = MainWindow()
        self.assertEqual(window.tabs.count(), 3)
        self.assertTrue(all(isinstance(tab, ProjectionWorkspace) for tab in window.projection_tabs.values()))
        self.assertEqual(set(window.star_charts), {AZIMUTHAL_EQUIDISTANT, STEREOGRAPHIC})
        window.close()

    def test_workspace_partial_refresh_preserves_valid_previews_and_tab(self):
        from astrolabe_gui import ProjectionWorkspace
        workspace=ProjectionWorkspace("draw-stereographic",STEREOGRAPHIC,lambda:"en")
        old=b'<svg xmlns="http://www.w3.org/2000/svg" width="9mm" height="9mm"/>';new=b'<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm"/>'
        workspace.projection_controls.main_svg=old;workspace.projection_controls.ecliptic_svg=old;workspace.star_chart.main_svg=old;workspace.select_index(2)
        with patch("astrolabe_gui.svg_bytes",side_effect=[ValueError("main bad"),new]),patch("astrolabe_gui.render_star_chart",side_effect=ValueError("star bad")):
            workspace.update_preview()
        self.assertEqual(workspace.projection_controls.main_svg,old)
        self.assertEqual(workspace.projection_controls.ecliptic_svg,new)
        self.assertEqual(workspace.star_chart.main_svg,old);self.assertEqual(workspace.current_index(),2)
        self.assertIn("Main preview failed",workspace.status.text());self.assertIn("Ecliptic preview updated",workspace.status.text());self.assertIn("Star Chart preview failed",workspace.status.text())
        workspace.close()


if __name__ == "__main__":
    unittest.main()
