"""Astrolabe back: solar calendar, temporal hours, shadow square and EOT.

All lengths are millimetres. The back is a measuring instrument in its own
plane; the front projection selects its workspace, not a distortion of scales.
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import math
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

import numpy as np

from draw_projection import AZIMUTHAL_EQUIDISTANT, STEREOGRAPHIC, true_solar_ecliptic_longitude


LABEL_GROUPS = ('angle', 'zodiac_degree', 'zodiac_name', 'day', 'month',
                'hour', 'sincos', 'shadow_number', 'shadow_name')


def build_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--projection', choices=(AZIMUTHAL_EQUIDISTANT, STEREOGRAPHIC), default=STEREOGRAPHIC)
    p.add_argument('--diameter', type=float, default=120.0, help='Shared front boundary diameter (mm).')
    p.add_argument('--boundary-width', type=float, default=0.2, help='Shared front outline stroke (mm).')
    p.add_argument('--epoch-year', type=int, default=dt.date.today().year, help='Star-chart year; proleptic Gregorian calendar, noon UT each day (1–3000).')
    p.add_argument('--calendar-mode', choices=('concentric', 'eccentric'), default='concentric', help='Exact daily longitude or equal daily spacing on a fitted eccentric circle (approximate).')
    p.add_argument('--rotation-direction', choices=('counterclockwise', 'clockwise'), default='counterclockwise')
    p.add_argument('--zodiac-zero', type=float, default=0.0, help='Aries zero angle, counterclockwise from the right horizontal (degrees).')
    p.add_argument('--angle-band-width', type=float, default=2.5, help='Combined altitude and zodiac ring width (mm).')
    p.add_argument('--date-band-width', type=float, default=2.5, help='Calendar ring width (mm).')
    p.add_argument('--ring-gap', type=float, default=0.5, help='Gap between rings (mm).')
    p.add_argument('--line-width', type=float, default=0.12, help='Main scale stroke (mm).')
    p.add_argument('--minor-width', type=float, default=0.06, help='Minor scale stroke (mm).')
    p.add_argument('--label-size', type=float, default=0.85, help='Scale lettering size (mm).')
    for group in LABEL_GROUPS:
        prefix=group.replace('_','-')+'-label'
        p.add_argument(f'--{prefix}-font', default='Arial', help=f'{group} text font family.')
        p.add_argument(f'--{prefix}-size', type=float, default=0.0, help='Text size (mm); 0 inherits the default size for this label category.')
        p.add_argument(f'--{prefix}-radial-offset', type=float, default=0.0, help='Move label radially (mm), positive outward. Calendar labels use the calendar circle centre.')
        p.add_argument(f'--{prefix}-angular-offset', type=float, default=0.0, help='Move label around its circle (degrees), positive counterclockwise; does not move ticks.')
        p.add_argument(f'--{prefix}-orientation', choices=('auto','tangent','radial','horizontal'), default='auto', help='Automatic readable alignment, tangent, radial, or horizontal.')
        p.add_argument(f'--{prefix}-rotation', type=float, default=0.0, help='Additional text rotation (degrees), positive clockwise; 180 flips text.')
    p.add_argument('--upper-layout', choices=('hours', 'hours-sincos'), default='hours')
    p.add_argument('--sincos-scale', choices=('50', '60', 'both'), default='both', help='Function multiplier K: 50, 60, or both; inner radius ALWAYS equals 60 units.')
    p.add_argument('--sincos-zero-radius', type=float, default=0.0, help='Inner-radius fraction for sin/cos reading 0; reading 60 stays at the inner circle. Range 0 to less than 1.')
    p.add_argument('--shadow-divisions', type=int, default=12, help='Units on each side of the shadow square (1–100).')
    p.add_argument('--shadow-band-width', type=float, default=1.5, help='Shadow square scale width (mm).')
    p.add_argument('--shadow-label-band-width', type=float, default=1.5, help='Separate shadow square name band width (mm).')
    p.add_argument('--shadow-numbers', action=argparse.BooleanOptionalAction, default=False, help='Show shadow square numerical readings in the outer tick band.')
    p.add_argument('--eot', action=argparse.BooleanOptionalAction, default=True)
    p.add_argument('--eot-min-radius', type=float, default=0.95, help='Inner-radius fraction at minimum EOT (slowest apparent solar time), 0 to 1; 0.5 means half the inner radius. Default 0.95 matches the reference direction.')
    p.add_argument('--eot-max-radius', type=float, default=0.05, help='Inner-radius fraction at maximum EOT (fastest apparent solar time), 0 to 1. Default 0.05 matches the reference direction.')
    p.add_argument('--eot-band-width', type=float, default=None, help=argparse.SUPPRESS)  # Read legacy configs; no longer used.
    p.add_argument('--eot-width', type=float, default=0.16, help='EOT curve stroke (mm).')
    p.add_argument('--output', type=Path, default=Path('astrolabe_back.svg'))
    return p


def equation_of_time(date):
    """Meeus/NOAA expression, minutes apparent solar time minus mean time."""
    t = (date.toordinal() - dt.date(2000, 1, 1).toordinal()) / 36525.0
    l = math.radians((280.46646 + t * (36000.76983 + .0003032*t)) % 360)
    m = math.radians((357.52911 + t * (35999.05029 - .0001537*t)) % 360)
    e = .016708634 - t * (.000042037 + .0000001267*t)
    eps = 23 + (26 + (21.448 - t*(46.815 + t*(.00059 - .001813*t)))/60)/60
    eps += .00256 * math.cos(math.radians(125.04 - 1934.136*t))
    y = math.tan(math.radians(eps)/2)**2
    return math.degrees(y*math.sin(2*l) - 2*e*math.sin(m) +
                        4*e*y*math.sin(m)*math.cos(2*l) -
                        .5*y*y*math.sin(4*l) - 1.25*e*e*math.sin(2*m))*4


def calendar_geometry(year, mode, available_radius, direction=1, zero=0):
    """Return dates, circle centre/radius, uniform or solar angles, fit error."""
    start = dt.date(year, 1, 1)
    dates = [start + dt.timedelta(days=i) for i in range(366 if calendar.isleap(year) else 365)]
    solar = np.unwrap(np.radians([true_solar_ecliptic_longitude(d) for d in dates]))
    if mode == 'concentric':
        return dates, np.zeros(2), available_radius, zero + direction*solar, 0.0
    # Fit a unit circle's translation and phase to the daily solar rays.
    # Uniform spacing is retained, including Feb 29. No claim of exact Kepler motion.
    base = np.arange(len(dates))*2*math.pi/len(dates)
    phase = float(np.mean(solar-base)); center = np.zeros(2)
    normal = np.column_stack((-np.sin(solar), np.cos(solar)))
    for _ in range(15):
        a = base + phase
        q = np.column_stack((np.cos(a), np.sin(a)))
        tangent = np.column_stack((-np.sin(a), np.cos(a)))
        residual = np.sum(normal*(q+center), axis=1)
        jac = np.column_stack((normal, np.sum(normal*tangent, axis=1)))
        delta = np.linalg.lstsq(jac, -residual, rcond=None)[0]
        center += delta[:2]; phase += delta[2]
        if np.linalg.norm(delta) < 1e-12: break
    angles = base + phase
    points = center + np.column_stack((np.cos(angles), np.sin(angles)))
    errors = np.angle(np.exp(1j*(np.arctan2(points[:, 1], points[:, 0])-solar)))
    radius = available_radius/(1+np.linalg.norm(center))
    transform = np.array([[math.cos(zero), -direction*math.sin(zero)],
                          [math.sin(zero), direction*math.cos(zero)]])
    return dates, transform @ center * radius, radius, zero+direction*angles, float(np.max(np.abs(np.degrees(errors))))


def validate(args):
    if not 1 <= args.epoch_year <= 3000: raise ValueError('Calendar year must be between 1 and 3000.')
    for name in ('diameter', 'angle_band_width', 'date_band_width', 'label_size', 'shadow_band_width', 'shadow_label_band_width'):
        if not math.isfinite(getattr(args, name)) or getattr(args, name) <= 0:
            raise ValueError(f'{name} must be finite and positive.')
    for name in ('boundary_width', 'line_width', 'minor_width', 'ring_gap', 'eot_width'):
        if not math.isfinite(getattr(args, name)) or getattr(args, name) < 0:
            raise ValueError(f'{name} must be finite and nonnegative.')
    if not math.isfinite(args.zodiac_zero): raise ValueError('zodiac-zero must be finite.')
    for name in ('eot_min_radius', 'eot_max_radius'):
        value = getattr(args, name)
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f'{name} must be an inner-radius fraction between 0 and 1 (not millimetres).')
    if not 1 <= args.shadow_divisions <= 100: raise ValueError('Shadow divisions must be between 1 and 100.')
    if not math.isfinite(args.sincos_zero_radius) or not 0 <= args.sincos_zero_radius < 1:
        raise ValueError('sincos-zero-radius must be between 0 and 1, excluding 1.')
    for category in LABEL_GROUPS:
        if not getattr(args,category+'_label_font').strip(): raise ValueError('Label font must not be empty.')
        for suffix in ('size','radial_offset','angular_offset','rotation'):
            value=getattr(args,category+'_label_'+suffix)
            if not math.isfinite(value) or (suffix=='size' and value<0):
                raise ValueError(f'Invalid {category} label {suffix}.')


def back_geometry(args):
    """Shared calendar and inner measuring circle for back and ruler."""
    validate(args)
    radius = args.diameter/2
    sign = 1 if args.rotation_direction == 'counterclockwise' else -1
    zero = math.radians(args.zodiac_zero)
    available = radius-args.angle_band_width-args.ring_gap
    dates, offset, date_radius, date_angles, error = calendar_geometry(args.epoch_year, args.calendar_mode, available, sign, zero)
    inside = date_radius-args.date_band_width-float(np.linalg.norm(offset))-args.ring_gap
    inner = inside
    if inner <= max(3*args.label_size, 3*args.shadow_band_width):
        raise ValueError('Rings leave insufficient room: reduce band widths or increase the shared diameter.')
    if args.shadow_band_width+args.shadow_label_band_width >= inner/math.sqrt(2):
        raise ValueError('Shadow tick and label bands leave no room inside the square.')
    return dates, offset, date_radius, date_angles, error, inner


def sincos_radius(args, inner, value):
    return inner*(args.sincos_zero_radius+(1-args.sincos_zero_radius)*value/60)


def eot_extrema(dates):
    values=np.array([equation_of_time(d) for d in dates])
    return float(values.min()),float(values.max())


def eot_radius(args, inner, minutes, extrema):
    lo,hi=extrema
    return inner*(args.eot_min_radius+(minutes-lo)/(hi-lo)*(args.eot_max_radius-args.eot_min_radius))


def render_back(args):
    dates, offset, date_radius, date_angles, error, inner = back_geometry(args)
    radius=args.diameter/2
    sign=1 if args.rotation_direction=='counterclockwise' else -1
    zero=math.radians(args.zodiac_zero)
    margin = max(2.0, args.boundary_width)
    size = args.diameter+2*margin; origin = size/2
    root = Element('svg', xmlns='http://www.w3.org/2000/svg', width=f'{size:.4f}mm', height=f'{size:.4f}mm', viewBox=f'0 0 {size:.4f} {size:.4f}')
    SubElement(root, 'title').text = f'Astrolabe back {args.epoch_year} ({args.projection})'
    SubElement(root, 'desc').text = f'Gregorian noon UT; EOT=apparent-minus-mean minutes; eccentric max error={error:.6f} deg; inner radius=60 units.'
    group = SubElement(root, 'g', fill='none', stroke='black', **{'stroke-width':str(args.line_width)})
    def xy(p): return (origin+float(p[0]), origin-float(p[1]))
    def polar(r, a, c=(0, 0)): return (c[0]+r*math.cos(a), c[1]+r*math.sin(a))
    def line(a, b, width=None, **attrs):
        x,y=xy(a); u,v=xy(b)
        SubElement(group,'line',x1=str(x),y1=str(y),x2=str(u),y2=str(v), **{'stroke-width':str(args.line_width if width is None else width), **attrs})
    def circle(r, c=(0,0), width=None):
        x,y=xy(c)
        SubElement(group,'circle',cx=str(x),cy=str(y),r=str(r), **{'stroke-width':str(args.line_width if width is None else width)})
    def curve(points, width=None, **attrs):
        SubElement(group,'polyline',points=' '.join(f'{x:.5f},{y:.5f}' for x,y in map(xy,points)), **{'stroke-width':str(args.line_width if width is None else width), **attrs})
    def label(p, text, angle=None, size=None, category='angle', center=(0,0)):
        # Label transforms do not change the underlying scale geometry.
        r=math.hypot(p[0]-center[0],p[1]-center[1])
        a=math.atan2(p[1]-center[1],p[0]-center[0])
        da=math.radians(getattr(args,category+'_label_angular_offset'))
        r+=getattr(args,category+'_label_radial_offset')
        a+=da
        x,y=xy(polar(r,a,center))
        orientation=getattr(args,category+'_label_orientation')
        deg=0
        if orientation in ('tangent','radial'):
            deg=(90 if orientation=='tangent' else 0)-math.degrees(a)
        elif orientation=='auto' and angle is not None:
            deg=90-math.degrees(angle+da)
            while deg>90:deg-=180
            while deg<-90:deg+=180
        deg+=getattr(args,category+'_label_rotation')
        font_size=getattr(args,category+'_label_size') or size or args.label_size
        # Large local text coordinates avoid Qt's small-font rounding. Keeping
        # the transform on a parent group also preserves native editable text.
        holder=SubElement(group,'g',transform=f'translate({x} {y}) rotate({deg}) scale({font_size/100})',
                          **{'data-label-group':category})
        SubElement(holder,'text',x='0',y='32',fill='#000000',stroke='none',
                   **{'font-family':getattr(args,category+'_label_font'), 'font-size':'100',
                      'text-anchor':'middle'}).text=str(text)
    # Outer altitude quadrants, ecliptic degrees within each 30-degree sign.
    w=args.angle_band_width
    circle(radius,width=args.boundary_width); circle(radius-w); circle(radius-w*.48)
    names=('Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces')
    for deg in range(360):
        a=zero+sign*math.radians(deg)
        length=w*(.20 if deg%10==0 else .12 if deg%5==0 else .07)
        line(polar(radius,a),polar(radius-length,a),args.minor_width)
        line(polar(radius-w*.48,a),polar(radius-w*.48-length*.55,a),args.minor_width)
        if deg%10==0:
            altitude=round(math.degrees(math.asin(abs(math.sin(a)))))
            label(polar(radius-w*.32,a),altitude,a,size=args.label_size*.8)
            label(polar(radius-w*.65,a),deg%30,a,size=args.label_size*.65,category='zodiac_degree')
        if deg%30==0: line(polar(radius-w*.48,a),polar(radius-w,a))
    for i,name in enumerate(names):
        a=zero+sign*math.radians(i*30+15)
        label(polar(radius-w*.85,a),name,a,size=args.label_size*.8,category='zodiac_name')
    # Date ticks are normal to their own circle; compare outer endpoints by pivot rays.
    circle(date_radius,offset); circle(date_radius-args.date_band_width,offset)
    for date,a in zip(dates,date_angles):
        major=date.day==1
        length=args.date_band_width*(1 if major else .38 if date.day%5==0 else .16)
        line(polar(date_radius,a,offset),polar(date_radius-length,a,offset),args.line_width if major else args.minor_width)
        if date.day%5==0: label(polar(date_radius-args.date_band_width*.48,a,offset),date.day,a,size=args.label_size*.65,category='day',center=offset)
        if date.day==15: label(polar(date_radius-args.date_band_width*.78,a,offset),calendar.month_name[date.month],a,category='month',center=offset)
    # EOT overlays the measuring field, with no ruler or annular scale.
    # The chosen year's extrema anchor a linear radial readout; longitude
    # remains the angular coordinate even when the calendar is eccentric.
    if args.eot:
        r_min = inner*args.eot_min_radius
        r_max = inner*args.eot_max_radius
        e_min,e_max=eot_extrema(dates)
        radii = [eot_radius(args,inner,equation_of_time(d),(e_min,e_max)) for d in dates]
        points = [polar(float(r),zero+sign*math.radians(true_solar_ecliptic_longitude(d))) for d,r in zip(dates,radii)]
        curve(points+[points[0]],args.eot_width, id='eot-curve', **{
            'data-eot-min-minutes':str(e_min), 'data-eot-max-minutes':str(e_max),
            'data-eot-min-radius':str(r_min), 'data-eot-max-radius':str(r_max),
            'data-inner-radius':str(inner), 'data-eot-min-radius-ratio':str(args.eot_min_radius),
            'data-eot-max-radius-ratio':str(args.eot_max_radius)})
    circle(inner); line((-inner,0),(inner,0)); line((0,0),(0,inner))
    # Traditional temporal-hour circles: through pivot and the 15-degree marks.
    # r(theta)=R*sin(theta)/sin(h*15 degrees), clipped at the inner semicircle.
    half=args.upper_layout=='hours-sincos'
    for h in range(1,7):
        alpha=math.radians(h*15)
        for left in (False,True):
            if half and not left: continue
            angles=np.linspace(0,alpha,101)
            points=[polar(inner*math.sin(a)/math.sin(alpha),math.pi-a if left else a) for a in angles]
            curve(points, id=f'hour-{h if left else 12-h}-{"left" if left else "right"}')
            a=math.pi-alpha if left else alpha
            if not (h==6 and not left and not half):
                anchor=polar(inner-args.label_size,a)
                if half and h==6: anchor=(-args.label_size,inner-args.label_size)
                label(anchor,f'{h}/{12-h}' if half and h<6 else h if left else 12-h,category='hour')
    if half:
        # Polar function curves: the ruler reads K*sin(theta), K*cos(theta).
        # 60 is the radius in ruler units regardless of the selected K.
        scales=(50,60) if args.sincos_scale=='both' else (int(args.sincos_scale),)
        for k in scales:
            for fn,name in ((math.sin,'sin'),(math.cos,'cos')):
                identifier=f'{name}-curve-{k}' if len(scales)>1 else f'{name}-curve'
                curve([polar(sincos_radius(args,inner,k*fn(a)),a) for a in np.linspace(0,math.pi/2,181)],id=identifier)
                peak=sincos_radius(args,inner,k)
                anchor=(args.label_size*2,peak-args.label_size) if name=='sin' else (peak-args.label_size*2,args.label_size)
                label(anchor,f'{k} {name}',size=args.label_size*.85,category='sincos')
    # Two shadow squares: horizontal readings N*cot(alt), vertical N*tan(alt).
    side=inner/math.sqrt(2); band=args.shadow_band_width; n=args.shadow_divisions
    tick_side=side-band; label_side=tick_side-args.shadow_label_band_width
    name_side=(tick_side+label_side)/2
    for s in (-1,1):
        curve([(0,0),(s*side,0),(s*side,-side),(0,-side),(0,0)])
        curve([(s*tick_side,0),(s*tick_side,-tick_side),(0,-tick_side)])
        curve([(s*label_side,0),(s*label_side,-label_side),(0,-label_side)])
        line((0,0),(s*side,-side),args.minor_width)
        for i in range(1,n):
            d=side*i/n
            # Both endpoints lie on the same pivot ray. Perpendicular ticks
            # would give different readings at the two edges of the band.
            line((s*d,-side),(s*tick_side*i/n,-tick_side),args.minor_width,
                 **{'data-shadow-edge':'recta','data-shadow-value':str(i)})
            line((s*side,-d),(s*tick_side,-tick_side*i/n),args.minor_width,
                 **{'data-shadow-edge':'versa','data-shadow-value':str(i)})
        if args.shadow_numbers:
            middle=side-band/2
            for i in range(1,n+1):
                if i%3==0 or i==n:
                    label((s*middle*i/n,-middle),i,size=args.label_size*.7,category='shadow_number')
                    if i<n:label((s*middle,-middle*i/n),i,size=args.label_size*.7,category='shadow_number')
        label((s*label_side*.5,-name_side),'Umbra Recta',size=args.label_size*.8,category='shadow_name')
        label((s*name_side,-label_side*.5),'Umbra Versa',0,size=args.label_size*.8,category='shadow_name')
    circle(args.label_size*.5)
    return tostring(root,encoding='utf-8',xml_declaration=True), error


def main():
    parser=build_parser(); args=parser.parse_args()
    try: svg,error=render_back(args)
    except ValueError as exc: parser.error(str(exc))
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_bytes(svg)
    print(f'{args.output}; calendar max angular error: {error:.6f} deg')


if __name__=='__main__': main()
