import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from astrolabe_gui import tokenize_config
from draw_projection import STEREOGRAPHIC, parse_args, svg_bytes


class ConfigTests(unittest.TestCase):
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
        self.assertIn("File > Export Configuration", gui_help_markdown("en"))
        self.assertIn("文件 > 导出配置", gui_help_markdown("zh"))
        self.assertIn("300 DPI", gui_help_markdown("zh"))

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

    def test_chinese_labels_expand_settings_panel(self):
        from astrolabe_gui import ProjectionTab
        language = ["en"]
        tab = ProjectionTab("draw-stereographic", STEREOGRAPHIC, lambda: language[0])
        language[0] = "zh"; tab.retranslate()
        self.assertGreaterEqual(tab.left_panel.minimumWidth(), 700)

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


if __name__ == "__main__":
    unittest.main()
