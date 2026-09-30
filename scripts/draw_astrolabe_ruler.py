"""Matching two-arm astrolabe rule, drawn horizontally at physical scale."""
from __future__ import annotations

import math
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from draw_astrolabe_back import build_parser as build_back_parser, back_geometry, sincos_radius, eot_radius, eot_extrema


def build_parser():
    p=build_back_parser();p.description=__doc__;p.set_defaults(output=Path('astrolabe_ruler.svg'))
    p.add_argument('--ruler-symmetry',choices=('rotational','axial'),default='rotational',help='Half-turn symmetric opposite-side arms, or mirror symmetry across the perpendicular centre axis with both arms and scales on the same side of the diameter.')
    p.add_argument('--ruler-length-ratio',type=float,default=1.0,help='Tip-to-tip length / global outer diameter. Short rules omit out-of-body ticks without rescaling.')
    p.add_argument('--ruler-arm-width',type=float,default=3.0,help='Material width from the diameter reading edge into each arm (mm), for either symmetry mode.')
    p.add_argument('--ruler-hub-radius',type=float,default=4.0,help='Central circular hub radius (mm).')
    p.add_argument('--ruler-hole-radius',type=float,default=0.0,help='Pivot hole radius (mm); 0 hides the hole and keeps the central zero tick.')
    p.add_argument('--ruler-tip-length',type=float,default=3.0,help='Decorative curved tip length (mm).')
    p.add_argument('--ruler-outline-width',type=float,default=0.2,help='Rule outline stroke (mm); outer circle uses global boundary width.')
    p.add_argument('--ruler-tick-width',type=float,default=0.10,help='Scale tick stroke (mm).')
    p.add_argument('--ruler-tick-length',type=float,default=1.0,help='Major tick length (mm). Minor ticks are 60 percent as long.')
    p.add_argument('--ruler-eot-step',type=float,default=1.0,help='EOT tick spacing in minutes (0.1 to 5); labelled multiples of 5 are always included.')
    for category in ('sin','eot'):
        p.add_argument(f'--ruler-{category}-font',default='Arial',help='Scale number font family.')
        p.add_argument(f'--ruler-{category}-size',type=float,default=1.0,help='Scale number font size (mm).')
        p.add_argument(f'--ruler-{category}-label-offset',type=float,default=0.0,help='Extra label distance from the reading edge (mm), positive into the arm.')
    return p


def validate_ruler(args):
    for name in ('ruler_length_ratio','ruler_arm_width','ruler_hub_radius','ruler_tip_length','ruler_tick_length','ruler_sin_size','ruler_eot_size'):
        value=getattr(args,name)
        if not math.isfinite(value) or value<=0:raise ValueError(f'{name} must be finite and positive.')
    for name in ('ruler_hole_radius','ruler_outline_width','ruler_tick_width'):
        value=getattr(args,name)
        if not math.isfinite(value) or value<0:raise ValueError(f'{name} must be finite and nonnegative.')
    if not math.isfinite(args.ruler_eot_step) or not .1<=args.ruler_eot_step<=5:
        raise ValueError('ruler-eot-step must be between 0.1 and 5 minutes.')
    for category in ('sin','eot'):
        if not getattr(args,f'ruler_{category}_font').strip():raise ValueError('Ruler font cannot be empty.')
        if not math.isfinite(getattr(args,f'ruler_{category}_label_offset')):raise ValueError('Ruler label offset must be finite.')
    half=args.diameter*args.ruler_length_ratio/2
    if args.ruler_hub_radius<args.ruler_arm_width:
        raise ValueError('Hub radius must be at least the arm width.')
    if args.ruler_hole_radius>=args.ruler_hub_radius:raise ValueError('Pivot hole must be smaller than the hub.')
    if half<=args.ruler_hub_radius+args.ruler_tip_length:
        raise ValueError('Ruler is too short for the hub and decorative tips.')
    room=args.ruler_arm_width
    if args.ruler_tick_length>room:raise ValueError('Tick length exceeds the available arm width.')


def ruler_outline(args):
    """Closed union of two arms and a circular hub; centre is (0,0)."""
    h=args.diameter*args.ruler_length_ratio/2;w=args.ruler_arm_width
    r=args.ruler_hub_radius;t=args.ruler_tip_length
    if args.ruler_symmetry=='rotational':
        join=math.sqrt(r*r-w*w)
        # Trace half of the outline, then its half-turn counterpart.
        return (f'M {-h} 0 Q {-h+t*.25} 0 {-h+t*.4} {-w*.4} '
                f'Q {-h+t*.8} {-w*.5} {-h+t} {-w} L {-join} {-w} '
                f'A {r} {r} 0 0 1 {r} 0 L {h} 0 '
                f'Q {h-t*.25} 0 {h-t*.4} {w*.4} Q {h-t*.8} {w*.5} {h-t} {w} '
                f'L {join} {w} A {r} {r} 0 0 1 {-r} 0 Z')
    join=math.sqrt(r*r-w*w)
    return (f'M {-h} 0 Q {-h+t*.25} 0 {-h+t*.4} {-w*.4} Q {-h+t*.8} {-w*.5} {-h+t} {-w} '
            f'L {-join} {-w} A {r} {r} 0 0 1 {join} {-w} L {h-t} {-w} '
            f'Q {h-t*.8} {-w*.5} {h-t*.4} {-w*.4} Q {h-t*.25} 0 {h} 0 '
            f'L {r} 0 A {r} {r} 0 0 1 {-r} 0 Z')


def render_ruler(args):
    dates,_,_,_,_,inner=back_geometry(args);validate_ruler(args)
    lo,hi=eot_extrema(dates)
    if args.eot_min_radius==args.eot_max_radius:
        raise ValueError('EOT endpoint ratios must differ to produce a readable ruler.')
    half=args.diameter*args.ruler_length_ratio/2
    extent=max(args.diameter/2,half,args.ruler_hub_radius)+max(2,args.boundary_width,args.ruler_outline_width)
    size=extent*2
    root=Element('svg',xmlns='http://www.w3.org/2000/svg',width=f'{size:.4f}mm',height=f'{size:.4f}mm',viewBox=f'0 0 {size:.4f} {size:.4f}')
    SubElement(root,'title').text=f'Astrolabe ruler {args.epoch_year} ({args.projection})'
    SubElement(root,'desc').text=f'Inner radius {inner} mm; EOT {lo} to {hi} minutes; scale readings retain physical back-plate radii.'
    g=SubElement(root,'g',transform=f'translate({extent} {extent})',fill='none',stroke='black')
    SubElement(g,'circle',id='global-outline',cx='0',cy='0',r=str(args.diameter/2),**{'stroke-width':str(args.boundary_width)})
    SubElement(g,'path',id='ruler-outline',d=ruler_outline(args),**{'stroke-width':str(args.ruler_outline_width)})
    if args.ruler_hole_radius:
        SubElement(g,'circle',id='pivot-hole',cx='0',cy='0',r=str(args.ruler_hole_radius),**{'stroke-width':str(args.ruler_outline_width)})
    skipped=0
    def tick(category,value,radius,major):
        nonlocal skipped
        if radius<0 or radius>half-args.ruler_tip_length:
            skipped+=1;return
        # The hole interrupts the physical reading edge near the pivot.
        if radius<args.ruler_hole_radius:
            skipped+=1;return
        s=-1 if category=='sin' else 1;x=s*radius
        reading_side=-1 if args.ruler_symmetry=='axial' else s
        length=args.ruler_tick_length*(1 if major else .6)
        SubElement(g,'line',x1=str(x),y1='0',x2=str(x),y2=str(reading_side*length),
                   **{'stroke-width':str(args.ruler_tick_width),'data-scale':category,'data-value':str(value),'data-radius':str(radius)})
        if major:
            font_size=getattr(args,f'ruler_{category}_size')
            y=reading_side*(args.ruler_tick_length+font_size*.75+getattr(args,f'ruler_{category}_label_offset'))
            holder=SubElement(g,'g',transform=f'translate({x} {y}) scale({font_size/100})',**{'data-label-scale':category})
            SubElement(holder,'text',x='0',y='32',fill='black',stroke='none',**{
                'font-family':getattr(args,f'ruler_{category}_font'),'font-size':'100','text-anchor':'middle'}).text=f'{value:g}'
    for value in range(61):tick('sin',value,sincos_radius(args,inner,value),value%5==0)
    step=args.ruler_eot_step
    # Round outward so the scale covers the entire annual curve. The same
    # linear calibration remains valid for these slightly extrapolated ticks.
    values={round(i*step,9) for i in range(math.floor(lo/step),math.ceil(hi/step)+1)}
    values.update(range(math.ceil(lo/5)*5,math.floor(hi/5)*5+1,5))
    for value in sorted(values):tick('eot',value,eot_radius(args,inner,value,(lo,hi)),abs(value/5-round(value/5))<1e-8)
    return tostring(root,encoding='utf-8',xml_declaration=True),skipped


def main():
    p=build_parser();args=p.parse_args()
    try:svg,skipped=render_ruler(args)
    except ValueError as exc:p.error(str(exc))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(svg)
    print(f'{args.output}; omitted ticks outside usable arm / inside pivot hole: {skipped}')


if __name__=='__main__':main()
