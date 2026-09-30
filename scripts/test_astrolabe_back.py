import datetime as dt
import math
import os
from pathlib import Path
import tempfile
import unittest
from xml.etree.ElementTree import fromstring

import numpy as np

from draw_astrolabe_back import build_parser, calendar_geometry, equation_of_time, render_back
from draw_projection import true_solar_ecliptic_longitude, STEREOGRAPHIC, AZIMUTHAL_EQUIDISTANT


class BackGeometryTests(unittest.TestCase):
    def test_concentric_calendar_matches_sun_and_keeps_leap_day(self):
        dates, center, radius, angles, error = calendar_geometry(2024, 'concentric', 50)
        self.assertEqual(len(dates), 366)
        self.assertIn(dt.date(2024, 2, 29), dates)
        self.assertGreater(np.ptp(np.diff(angles)), .0005)
        for date, angle in zip(dates, angles):
            self.assertAlmostEqual(math.cos(angle), math.cos(math.radians(true_solar_ecliptic_longitude(date))), places=12)
        self.assertEqual(error, 0)

    def test_eccentric_spacing_fit_containment_and_direction(self):
        for year in (2000, 2024, 2026):
            for sign in (-1, 1):
                dates, center, radius, angles, error = calendar_geometry(year, 'eccentric', 50, sign, .4)
                self.assertTrue(np.allclose(np.diff(angles), sign*2*math.pi/len(dates)))
                self.assertGreater(np.linalg.norm(center), .5)
                self.assertAlmostEqual(np.linalg.norm(center)+radius, 50)
                actual = np.arctan2(center[1]+radius*np.sin(angles), center[0]+radius*np.cos(angles))
                target = .4 + sign*np.radians([true_solar_ecliptic_longitude(d) for d in dates])
                residual = np.abs(np.degrees(np.angle(np.exp(1j*(actual-target)))))
                self.assertAlmostEqual(max(residual), error)
                self.assertLess(error, .5)

    def test_eot_sign_and_seasonal_values(self):
        self.assertAlmostEqual(equation_of_time(dt.date(2024, 2, 11)), -14.23, delta=.1)
        self.assertAlmostEqual(equation_of_time(dt.date(2024, 11, 3)), 16.49, delta=.1)
        self.assertLess(abs(equation_of_time(dt.date(2024, 6, 14))), .5)

    def test_eot_radial_endpoints_longitude_and_no_ruler(self):
        ns={'s':'http://www.w3.org/2000/svg'}
        for lo, hi in ((.05,.95),(.95,.05),(0,1),(.5,.5)):
            args=build_parser().parse_args(['--epoch-year','2024','--eot-min-radius',str(lo),'--eot-max-radius',str(hi),'--upper-layout','hours-sincos'])
            root=fromstring(render_back(args)[0])
            curve=root.find(".//s:polyline[@id='eot-curve']",ns)
            points=np.array([[float(v) for v in pair.split(',')] for pair in curve.attrib['points'].split()])
            origin=float(root.attrib['viewBox'].split()[2])/2
            vectors=points[:-1]-origin; vectors[:,1]*=-1
            radii=np.linalg.norm(vectors,axis=1)
            dates=[dt.date(2024,1,1)+dt.timedelta(days=i) for i in range(366)]
            values=np.array([equation_of_time(d) for d in dates])
            inner=float(curve.attrib['data-inner-radius'])
            expected=inner*(lo+(values-values.min())/np.ptp(values)*(hi-lo))
            self.assertTrue(np.allclose(radii,expected,atol=1e-5))
            for d, v, r in zip(dates,vectors,radii):
                if r>1e-4:
                    a=math.radians(true_solar_ecliptic_longitude(d))
                    self.assertTrue(np.allclose(v,r*np.array([math.cos(a),math.sin(a)]),atol=1e-5))
            self.assertTrue(np.array_equal(points[0],points[-1]))
            self.assertFalse(any(g.attrib.get('aria-label')=='EOT MIN' for g in root.iter()))
            circles=len(root.findall('.//s:circle',ns))
            args.eot=False
            without=fromstring(render_back(args)[0])
            self.assertEqual(circles,len(without.findall('.//s:circle',ns)))
            self.assertIsNone(without.find(".//s:polyline[@id='eot-curve']",ns))
        args.eot=True;args.eot_max_radius=1000
        with self.assertRaises(ValueError):render_back(args)

    def test_eot_ratios_follow_inner_circle_size(self):
        ns={'s':'http://www.w3.org/2000/svg'}
        args=build_parser().parse_args([])
        self.assertEqual((args.eot_min_radius,args.eot_max_radius),(.95,.05))
        for diameter,band in ((120,2.5),(80,5),(160,10)):
            args.diameter=diameter;args.date_band_width=band;args.eot_min_radius=.5
            root=fromstring(render_back(args)[0]);curve=root.find(".//s:polyline[@id='eot-curve']",ns)
            expected_inner=diameter/2-args.angle_band_width-band-2*args.ring_gap
            self.assertAlmostEqual(float(curve.attrib['data-eot-min-radius']),expected_inner*.5)
            self.assertAlmostEqual(float(curve.attrib['data-eot-max-radius']),expected_inner*.05)

    def test_svg_combinations_and_invalid_geometry(self):
        ns={'s':'http://www.w3.org/2000/svg'}
        for projection in (STEREOGRAPHIC, AZIMUTHAL_EQUIDISTANT):
            for mode in ('concentric','eccentric'):
                for layout in ('hours','hours-sincos'):
                    args=build_parser().parse_args(['--projection',projection,'--calendar-mode',mode,'--upper-layout',layout])
                    svg,_=render_back(args); root=fromstring(svg)
                    self.assertIsNotNone(root.find(".//s:polyline[@id='eot-curve']",ns))
                    self.assertEqual(root.find(".//s:polyline[@id='sin-curve-60']",ns) is not None,layout=='hours-sincos')
                    self.assertNotIn(b'nan',svg)
        args.diameter=10
        with self.assertRaises(ValueError): render_back(args)
        args.diameter=120; args.epoch_year=0
        with self.assertRaises(ValueError): render_back(args)

    def test_sincos_multiplier_uses_fixed_60_unit_radius(self):
        ns={'s':'http://www.w3.org/2000/svg'}
        widths=[]
        for k in (50,60):
            args=build_parser().parse_args(['--upper-layout','hours-sincos','--sincos-scale',str(k)])
            root=fromstring(render_back(args)[0]); curve=root.find(".//s:polyline[@id='cos-curve']",ns)
            xs=[float(pair.split(',')[0]) for pair in curve.attrib['points'].split()]
            widths.append(max(xs)-min(xs))
        self.assertAlmostEqual(widths[0]/widths[1],50/60,places=5)

    def test_shadow_ticks_are_pivot_rays_and_read_tangent_ratios(self):
        ns={'s':'http://www.w3.org/2000/svg'}
        args=build_parser().parse_args(['--shadow-divisions','12','--shadow-band-width','5'])
        root=fromstring(render_back(args)[0]);origin=float(root.attrib['viewBox'].split()[2])/2
        ticks=[e for e in root.findall('.//s:line',ns) if 'data-shadow-edge' in e.attrib]
        self.assertEqual(len(ticks),4*11)
        for tick in ticks:
            p=np.array([float(tick.attrib['x1'])-origin,origin-float(tick.attrib['y1'])])
            q=np.array([float(tick.attrib['x2'])-origin,origin-float(tick.attrib['y2'])])
            self.assertAlmostEqual(p[0]*q[1]-p[1]*q[0],0,places=9)
            self.assertLess(np.linalg.norm(q),np.linalg.norm(p))
            for v in (p,q):
                reading=12*abs(v[0]/v[1]) if tick.attrib['data-shadow-edge']=='recta' else 12*abs(v[1]/v[0])
                self.assertAlmostEqual(reading,float(tick.attrib['data-shadow-value']))

    def test_native_text_style_position_and_unmoved_geometry(self):
        ns={'s':'http://www.w3.org/2000/svg'}
        args=build_parser().parse_args([])
        before=fromstring(render_back(args)[0])
        args.month_label_font='Times New Roman';args.month_label_size=2.5
        args.month_label_radial_offset=1.25;args.month_label_angular_offset=12
        args.month_label_orientation='horizontal';args.month_label_rotation=25
        after=fromstring(render_back(args)[0])
        texts=after.findall('.//s:text',ns)
        self.assertGreater(len(texts),100)
        self.assertTrue(all(t.attrib['stroke']=='none' for t in texts))
        for a,b in zip(before.findall(".//s:g[@data-label-group='month']",ns),after.findall(".//s:g[@data-label-group='month']",ns)):
            self.assertNotEqual(a.attrib['transform'],b.attrib['transform'])
            self.assertIn('rotate(25)',b.attrib['transform']);self.assertIn('scale(0.025)',b.attrib['transform'])
            self.assertEqual(b.find('s:text',ns).attrib['font-family'],'Times New Roman')
        for tag in ('line','circle','polyline'):
            self.assertEqual([e.attrib for e in before.findall('.//s:'+tag,ns)],[e.attrib for e in after.findall('.//s:'+tag,ns)])
        self.assertEqual([e.attrib for e in before.findall(".//s:g[@data-label-group='day']",ns)],[e.attrib for e in after.findall(".//s:g[@data-label-group='day']",ns)])

    def test_new_reference_has_left_hours_right_function_curves(self):
        ns={'s':'http://www.w3.org/2000/svg'}
        args=build_parser().parse_args(['--upper-layout','hours-sincos'])
        root=fromstring(render_back(args)[0]);origin=float(root.attrib['viewBox'].split()[2])/2
        for curve in root.findall('.//s:polyline',ns):
            identifier=curve.attrib.get('id','')
            xs=[float(pair.split(',')[0])-origin for pair in curve.attrib['points'].split()]
            if identifier.startswith('hour-'):self.assertLessEqual(max(xs),1e-5)
            if identifier.startswith(('sin-curve','cos-curve')):self.assertGreaterEqual(min(xs),-1e-5)
        self.assertEqual(len([e for e in root.findall('.//s:polyline',ns) if e.attrib.get('id','').startswith(('sin-curve','cos-curve'))]),4)


class BackWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
        # The Windows offscreen platform may not enumerate installed fonts.
        from PySide6.QtGui import QFontDatabase
        if not QFontDatabase.families():
            for filename in ('arial.ttf','times.ttf'):
                path=Path('C:/Windows/Fonts')/filename
                if path.exists():QFontDatabase.addApplicationFont(str(path))

    def test_shared_parameters_config_preview_and_save(self):
        from astrolabe_gui import ProjectionWorkspace, tokenize_workspace_config
        from PySide6.QtCore import QByteArray
        for projection in (STEREOGRAPHIC,AZIMUTHAL_EQUIDISTANT):
            w=ProjectionWorkspace('draw-'+projection,projection,lambda:'zh')
            w.projection_controls.set_value('diameter',100)
            w.projection_controls.set_value('boundary_width',.33)
            w.star_chart.set_value('epoch_year',2024)
            w.back.set_value('calendar_mode','eccentric'); w.back.set_value('upper_layout','hours-sincos')
            self.assertEqual((w.back.value('eot_min_radius'),w.back.value('eot_max_radius')),(.95,.05))
            for name in ('eot_min_radius','eot_max_radius'):
                self.assertEqual((w.back.widgets[name].minimum(),w.back.widgets[name].maximum()),(0,1))
            w.back.set_value('eot_min_radius',.5);w.back.set_value('eot_max_radius',.05)
            w.back.set_value('month_label_font','Times New Roman')
            w.back.set_value('month_label_size',2.1);w.back.set_value('month_label_angular_offset',4.5)
            w.back.retranslate()
            args=w.back_namespace()
            self.assertEqual((args.diameter,args.boundary_width,args.epoch_year,args.projection),(100,.33,2024,projection))
            command=tokenize_workspace_config(w.export_config_text())[-2]
            parsed=build_parser().parse_args(command[1:])
            self.assertEqual((parsed.epoch_year,parsed.calendar_mode),(2024,'eccentric'))
            self.assertEqual((parsed.eot_min_radius,parsed.eot_max_radius),(.5,.05))
            with self.assertRaisesRegex(ValueError,'fraction'):
                w.back.import_args(['--eot-min-radius','38'])
            self.assertEqual((parsed.month_label_font,parsed.month_label_size,parsed.month_label_angular_offset),('Times New Roman',2.1,4.5))
            w.back.label_category.setCurrentIndex(w.back.label_category.findData('month'))
            self.assertFalse(w.back.rows['month_label_font'][0].isHidden())
            self.assertTrue(w.back.rows['angle_label_font'][0].isHidden())
            w.back.set_value('calendar_mode','concentric');w.import_back(command[1:])
            self.assertEqual(w.back.value('calendar_mode'),'eccentric')
            w.back.main_svg=render_back(w.back_namespace())[0];w.back.preview.load(QByteArray(w.back.main_svg))
            self.assertTrue(w.back.preview.renderer().isValid())
            w.select_index(3)
            with tempfile.TemporaryDirectory() as directory:
                for ext in ('svg','png','jpg'):
                    p=Path(directory)/('back.'+ext); w.save(p); self.assertGreater(p.stat().st_size,100)
            self.assertEqual(w.main_svg,w.back.main_svg)
            w.close()


if __name__=='__main__': unittest.main()
