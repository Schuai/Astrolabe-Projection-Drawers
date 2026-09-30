import math
import os
import re
from pathlib import Path
import tempfile
import unittest
from xml.etree.ElementTree import fromstring

import numpy as np

from draw_astrolabe_back import back_geometry, render_back, sincos_radius, eot_extrema, eot_radius
from draw_astrolabe_ruler import build_parser, render_ruler, ruler_outline

NS={'s':'http://www.w3.org/2000/svg'}


class CalibrationTests(unittest.TestCase):
    def test_ruler_matches_both_calendar_modes_and_years(self):
        for year,mode in ((2024,'concentric'),(2026,'eccentric')):
            args=build_parser().parse_args(['--epoch-year',str(year),'--calendar-mode',mode,'--sincos-zero-radius','.15'])
            dates,*_,inner=back_geometry(args);extrema=eot_extrema(dates)
            svg,skipped=render_ruler(args);root=fromstring(svg)
            sine=root.findall(".//s:line[@data-scale='sin']",NS)
            self.assertEqual(len(sine),61)
            for tick in sine:
                value=float(tick.attrib['data-value'])
                self.assertAlmostEqual(-float(tick.attrib['x1']),inner*(.15+.85*value/60))
            for tick in root.findall(".//s:line[@data-scale='eot']",NS):
                value=float(tick.attrib['data-value'])
                self.assertAlmostEqual(float(tick.attrib['x1']),eot_radius(args,inner,value,extrema))
            circle=root.find(".//s:circle[@id='global-outline']",NS)
            self.assertEqual(float(circle.attrib['r']),args.diameter/2)
            self.assertEqual(float(circle.attrib['stroke-width']),args.boundary_width)
            self.assertGreater(len(root.findall('.//s:text',NS)),10)

    def test_shifted_sine_cosine_curves_match_ruler_calibration(self):
        args=build_parser().parse_args(['--upper-layout','hours-sincos','--sincos-zero-radius','.2'])
        *_,inner=back_geometry(args)
        root=fromstring(render_back(args)[0]);origin=float(root.attrib['viewBox'].split()[2])/2
        for k in (50,60):
            for name,fn in (('sin',math.sin),('cos',math.cos)):
                curve=root.find(f".//s:polyline[@id='{name}-curve-{k}']",NS)
                points=np.array([[float(v) for v in pair.split(',')] for pair in curve.attrib['points'].split()])
                radii=np.linalg.norm(points-origin,axis=1)
                expected=[sincos_radius(args,inner,k*fn(a)) for a in np.linspace(0,math.pi/2,len(points))]
                self.assertTrue(np.allclose(radii,expected,atol=1e-5))
        self.assertAlmostEqual(sincos_radius(args,inner,0),inner*.2)
        self.assertAlmostEqual(sincos_radius(args,inner,60),inner)

    def test_short_rule_does_not_stretch_ticks(self):
        args=build_parser().parse_args(['--sincos-zero-radius','.1'])
        full=fromstring(render_ruler(args)[0]);args.ruler_length_ratio=.65
        short,skipped=render_ruler(args);short=fromstring(short)
        self.assertGreater(skipped,0)
        mapping={(e.attrib['data-scale'],e.attrib['data-value']):e.attrib['x1'] for e in full.findall('.//s:line',NS)}
        for tick in short.findall('.//s:line',NS):
            self.assertEqual(tick.attrib['x1'],mapping[tick.attrib['data-scale'],tick.attrib['data-value']])
        self.assertEqual(short.find(".//s:circle[@id='global-outline']",NS).attrib,full.find(".//s:circle[@id='global-outline']",NS).attrib)

    def test_invalid_geometry_and_degenerate_eot(self):
        for options in (['--sincos-zero-radius','1'],['--ruler-length-ratio','.01'],['--ruler-arm-width','8'],['--eot-min-radius','.5','--eot-max-radius','.5']):
            with self.assertRaises(ValueError):render_ruler(build_parser().parse_args(options))

    def test_axial_ticks_and_numbers_share_diameter_side_without_recalibration(self):
        args=build_parser().parse_args(['--sincos-zero-radius','.12'])
        roots=[]
        for mode in ('rotational','axial'):
            args.ruler_symmetry=mode;root=fromstring(render_ruler(args)[0]);roots.append(root)
            for tick in root.findall('.//s:line',NS):
                self.assertEqual(float(tick.attrib['y1']),0)
                expected=-1 if mode=='axial' or tick.attrib['data-scale']=='sin' else 1
                self.assertGreater(float(tick.attrib['y2'])*expected,0)
            for label in root.findall('.//s:g[@data-label-scale]',NS):
                y=float(re.search(r'translate\([^ ]+ ([^)]+)\)',label.attrib['transform']).group(1))
                expected=-1 if mode=='axial' or label.attrib['data-label-scale']=='sin' else 1
                self.assertGreater(y*expected,0)
        positions=lambda root:[(e.attrib['data-scale'],e.attrib['data-value'],e.attrib['x1']) for e in root.findall('.//s:line',NS)]
        self.assertEqual(positions(roots[0]),positions(roots[1]))


class RulerGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFontDatabase
        cls.app=QApplication.instance() or QApplication([])
        if not QFontDatabase.families() and Path('C:/Windows/Fonts/arial.ttf').exists():
            QFontDatabase.addApplicationFont('C:/Windows/Fonts/arial.ttf')

    def test_shape_symmetry(self):
        from PySide6.QtCore import QByteArray,Qt
        from PySide6.QtGui import QImage,QPainter
        from PySide6.QtSvg import QSvgRenderer
        for mode in ('rotational','axial'):
            args=build_parser().parse_args(['--ruler-symmetry',mode])
            svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-62 -10 124 20"><path d="{ruler_outline(args)}" fill="black"/></svg>'
            renderer=QSvgRenderer(QByteArray(svg.encode()));im=QImage(1240,200,QImage.Format.Format_RGBA8888);im.fill(Qt.GlobalColor.white)
            painter=QPainter(im);renderer.render(painter);painter.end()
            pixels=np.array(im.bits()).reshape(200,1240,4)[:,:,0]<128
            if mode=='axial':
                self.assertLess(np.mean(pixels!=pixels[:,::-1]),.003)
                self.assertGreater(np.mean(pixels!=pixels[::-1,::-1]),.03)
            else:
                self.assertLess(np.mean(pixels!=pixels[::-1,::-1]),.003)
                self.assertGreater(np.mean(pixels!=pixels[:,::-1]),.03)
            # At x=+/-20 mm, the diameter is the actual material edge:
            # ticks start there, rather than in the middle of a centred strip.
            for x in (-20,20):
                col=round((x+62)*10)
                above=mode=='axial' or x<0
                self.assertEqual(bool(pixels[95,col]),above)
                self.assertEqual(bool(pixels[105,col]),not above)

    def test_tabs_shared_parameters_config_save_and_refresh(self):
        from astrolabe_gui import ProjectionWorkspace,tokenize_workspace_config
        from draw_projection import STEREOGRAPHIC,AZIMUTHAL_EQUIDISTANT
        for projection in (STEREOGRAPHIC,AZIMUTHAL_EQUIDISTANT):
            w=ProjectionWorkspace('draw-'+projection,projection,lambda:'zh')
            self.assertEqual(w.pages.count(),5);self.assertEqual(w.pages.tabText(4),'标尺')
            w.projection_controls.set_value('diameter',100);w.projection_controls.set_value('boundary_width',.3)
            w.star_chart.set_value('epoch_year',2024);w.back.set_value('sincos_zero_radius',.2)
            w.back.set_value('eot_min_radius',.85);w.ruler.set_value('ruler_length_ratio',.9)
            args=w.ruler_namespace()
            self.assertEqual((args.diameter,args.boundary_width,args.epoch_year,args.sincos_zero_radius,args.eot_min_radius),(100,.3,2024,.2,.85))
            commands=tokenize_workspace_config(w.export_config_text());self.assertEqual(commands[-1][0],'draw-astrolabe-ruler')
            w.ruler.set_value('ruler_length_ratio',1);w.import_ruler(commands[-1][1:])
            self.assertEqual(w.ruler.value('ruler_length_ratio'),.9)
            w.select_index(4);w.update_preview();self.assertIsNotNone(w.ruler.main_svg)
            self.assertEqual(w.main_svg,w.ruler.main_svg);self.assertTrue(w.ruler.preview.renderer().isValid())
            with tempfile.TemporaryDirectory() as directory:
                for ext in ('svg','png','jpg'):
                    p=Path(directory)/('rule.'+ext);w.save(p);self.assertGreater(p.stat().st_size,100)
            # Failure must preserve the last valid ruler and selected page.
            old=w.ruler.main_svg;w.ruler.set_value('ruler_length_ratio',.001);w.update_preview()
            self.assertEqual(w.ruler.main_svg,old);self.assertEqual(w.current_index(),4)
            self.assertIn('标尺预览失败',w.status.text());w.close()


if __name__=='__main__':unittest.main()
