"""Vector renderer adapted from the original isometric night city.

All inputs are resolved before rendering. No scripts, network fetches, raster
images or external fonts are embedded in the output SVG.
"""
import json
import random
from html import escape


def render_city(stats: dict, params: dict) -> str:
    seed=params["seed"]
    def local_rng(label):
        return random.Random(f"{seed}:{label}")
    def choose_accent(index):
        if params.get("accent"):
            return params["accent"]
        languages=sorted(stats.get("languages",[]),key=lambda x:x["name"])
        if not languages:
            return "#62dce8"
        rng=local_rng(f"language:{index}")
        lang=rng.choices(languages,weights=[x["repositories"] for x in languages],k=1)[0]
        rgb=[int(lang["color"][i:i+2],16) for i in (1,3,5)]
        # Lift dark GitHub language colors so they remain legible as neon.
        return '#'+''.join(f'{round(v*.55+255*.45):02x}' for v in rgb)
    rng=local_rng("city")
    out=[]
    def emit(s):out.append(s)
    def p(u,v,z=0):return (700+(u-v)*0.8660254,352+(u+v)*0.5-z)
    def pts(vertices):return ' '.join(f'{x:.2f},{y:.2f}' for x,y in vertices)
    def poly(vertices,fill,stroke=None,sw=1,extra=''):
        emit(f'<polygon points="{pts(vertices)}" fill="{fill}"'+(f' stroke="{stroke}" stroke-width="{sw}"' if stroke else '')+f' {extra}/>')
    def line(a,b,color,width=1,extra=''):
        emit(f'<path d="M {a[0]:.2f} {a[1]:.2f} L {b[0]:.2f} {b[1]:.2f}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" {extra}/>')
    def flat(u,v,w,d,z,color,stroke=None):poly([p(u,v,z),p(u+w,v,z),p(u+w,v+d,z),p(u,v+d,z)],color,stroke)
    def box(u,v,w,d,z,h,top,left,right,stroke='#223654'):
        poly([p(u,v+d,z),p(u+w,v+d,z),p(u+w,v+d,z+h),p(u,v+d,z+h)],left,stroke,.7)
        poly([p(u+w,v,z),p(u+w,v+d,z),p(u+w,v+d,z+h),p(u+w,v,z+h)],right,stroke,.7)
        flat(u,v,w,d,z+h,top,stroke)
    def circle(x,y,r,fill,extra=''):emit(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="{fill}" {extra}/>')

    emit('''<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1200" viewBox="0 0 1400 1200" role="img" aria-labelledby="title description">
    <title id="title">Isometric midnight city</title>
    <desc id="description">An original vector illustration of a floating isometric city at night. Indigo skyscrapers, warm apartment windows, turquoise neon, cars, trees and streetlights beneath a crescent moon.</desc>
    <defs>
     <radialGradient id="sky"><stop stop-color="#172449"/><stop offset=".65" stop-color="#0b132d"/><stop offset="1" stop-color="#050a1a"/></radialGradient>
     <linearGradient id="glass" x1="0" y1="0" x2=".6" y2="1"><stop stop-color="#29466b"/><stop offset="1" stop-color="#111d38"/></linearGradient>
     <radialGradient id="halo"><stop stop-color="#65e5ff" stop-opacity=".35"/><stop offset="1" stop-color="#65e5ff" stop-opacity="0"/></radialGradient>
     <filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
     <filter id="soft" x="-40%" y="-100%" width="180%" height="300%"><feGaussianBlur stdDeviation="22"/></filter>
    </defs>
    <rect width="1400" height="1200" fill="url(#sky)"/>
    <ellipse cx="700" cy="660" rx="650" ry="430" fill="url(#halo)" opacity=".35"/>
    ''')
    rng = local_rng("sky")
    for _ in range(params["star_count"]):
        x=rng.uniform(70,1330);y=rng.uniform(60,790)
        circle(x,y,rng.choice([.6,.9,1.1]),'#cce5ff',f'opacity="{rng.uniform(.12,.65):.2f}"')
    circle(1145,148,57,'#233353', 'opacity=".35" filter="url(#soft)"')
    emit('<path d="M 1158 109 A 41 41 0 1 0 1176 171 A 36 36 0 0 1 1158 109" fill="#d7e6f4" opacity=".9"/>')
    emit('<ellipse cx="700" cy="974" rx="440" ry="84" fill="#000616" opacity=".8" filter="url(#soft)"/>')
    box(0,0,580,580,-27,27,'#18253b','#0e182d','#0b1327')
    line(p(0,580,-14),p(580,580,-14),'#213957',1.5)
    line(p(580,0,-14),p(580,580,-14),'#172947',1.5)
    flat(8,8,564,564,1,'#1b2c43')
    # The road network sits between three rows and three columns of blocks.
    for c in [0,184,368,552]:
        flat(c,0,28,580,2,'#101c30')
        flat(0,c,580,28,2,'#101c30')
        for t in range(42,550,28):
            flat(c+13,t,1.7,12,2.1,'#76819a')
            flat(t,c+13,12,1.7,2.1,'#76819a')
    for u in [34,218,402]:
        for v in [34,218,402]:
            box(u,v,144,144,2,3,'#33435a','#22334a','#1c2c43')
            flat(u+3,v+3,138,138,5.1,'#263950')
            for i in range(6):
                flat(u-5,v+47+i*6,4,3,2.2,'#8490a3')
                flat(u+47+i*6,v-5,3,4,2.2,'#8490a3')

    objects=[]
    def add(depth,fn):objects.append((depth,fn))
    def tree(u,v):
        box(u-5,v-5,10,10,5,4,'#2c4251','#233445','#172b3b')
        a=p(u,v,9);b=p(u,v,30);line(a,b,'#577176',3)
        x,y=p(u,v,35)
        emit(f'<path d="M {x} {y-19} C {x+24} {y-16} {x+25} {y+12} {x} {y+15} C {x-25} {y+12} {x-23} {y-17} {x} {y-19}" fill="#164750"/>')
        emit(f'<path d="M {x} {y-19} C {x+22} {y-15} {x+23} {y+8} {x} {y+15} Z" fill="#10333e"/>')
        line((x-12,y-6),(x-3,y-13),'#296977',2)

    def building(u,v,w,d,h,kind=0,accent="#62dce8",neon=False,beacon=False):
        z=6
        rng = local_rng(f"building:{u}:{v}")
        emit(f'<g data-kind="building" data-height="{h}" data-neon="{str(neon).lower()}">')
        # A crisp projected shadow connects each building to its block.
        poly([p(u,v+d,z),p(u+w,v+d,z),p(u+w+37,v+d+24,z),p(u+32,v+d+24,z)],'#0c1729',extra='opacity=".55"')
        box(u,v,w,d,z,h,['#3a5473','#34435f','#405271'][kind%3],['url(#glass)','#23304a','#243b56'][kind%3],['#13253f','#18233c','#172e47'][kind%3])
        # Recessed glass windows are mapped directly into each isometric facade.
        for face in [0,1]:
            span=w if face==0 else d
            cols=max(3,int(span/14)); rows=int((h-20)/18)
            gap=span/(cols+1)
            for row in range(rows):
                zz=z+12+row*18
                for col in range(cols):
                    t=gap*(col+1)
                    window_rng = local_rng(f"window:{u}:{v}:{face}:{row}:{col}")
                    on=window_rng.random()<params["window_light_rate"]
                    color=window_rng.choice(['#ffd898','#ffbc79','#ffe8ae',accent]) if on else '#29405a'
                    if face==1 and on and window_rng.random()<.35:color='#529bab'
                    if face==0:
                        verts=[p(u+t-3,v+d+.05,zz),p(u+t+3,v+d+.05,zz),p(u+t+3,v+d+.05,zz+9),p(u+t-3,v+d+.05,zz+9)]
                    else:
                        verts=[p(u+w+.05,v+t-3,zz),p(u+w+.05,v+t+3,zz),p(u+w+.05,v+t+3,zz+9),p(u+w+.05,v+t-3,zz+9)]
                    poly(verts,color,extra=f'opacity="{.9 if on else .4}" data-window="{u}-{v}-{face}-{row}-{col}" data-lit="{str(on).lower()}"')
            for row in range(1,rows+1):
                zz=z+row*18+8
                line(p(u,v+d,zz) if face==0 else p(u+w,v,zz),p(u+w,v+d,zz),'#476078',.55,extra='opacity=".42"')
        # Roof parapet, mechanical plant and antenna.
        flat(u+5,v+5,w-10,d-10,z+h+.4,'#23374f','#58718a')
        box(u+w*.25,v+d*.26,w*.35,d*.30,z+h+1,12,'#617085','#334761','#293c55')
        for j in range(4):
            line(p(u+w*.25+3,v+d*.26+3+j*4,z+h+13),p(u+w*.60-3,v+d*.26+3+j*4,z+h+13),'#2c4159',1)
        box(u+w*.68,v+d*.5,11,14,z+h+1,7,'#506780','#2a4058','#20334d')
        if neon:
            for aa,bb in [(p(u,v+d,z+h),p(u+w,v+d,z+h)),(p(u+w,v,z+h),p(u+w,v+d,z+h))]:
                line(aa,bb,accent,2,extra='filter="url(#glow)"')
        if beacon:
            line(p(u+w*.53,v+d*.45,z+h+13),p(u+w*.53,v+d*.45,z+h+52),'#7189a1',1.6)
            x,y=p(u+w*.53,v+d*.45,z+h+52);circle(x,y,2,'#ff7995','filter="url(#glow)"')
        # Street-level lobby.
        flat(u+w*.35,v+d+.7,w*.3,0.6,z+1,'#edbe80')
        poly([p(u+w*.35,v+d+.1,z+1),p(u+w*.65,v+d+.1,z+1),p(u+w*.65,v+d+.1,z+14),p(u+w*.35,v+d+.1,z+14)],'#92d4de')
        box(u+w*.3,v+d-2,w*.4,9,z+14,3,'#3e6481','#213b58','#1a3048')
        emit('</g>')

    # Stable lot order: existing buildings keep their positions as the city grows.
    slots=[(236,51,104,103),(234,233,101,103),(52,53,97,88),
           (422,51,115,106),(417,238,112,103),(51,419,109,104),
           (241,420,91,105),(49,235,56,109),(114,239,47,100)]
    occupied=set()
    for index,(u,v,w,d) in enumerate(slots[:params["building_count"]]):
        shape_rng=local_rng(f"shape:{index}")
        w=max(36,round(w*shape_rng.uniform(.82,1.04)))
        d=max(36,round(d*shape_rng.uniform(.82,1.04)))
        # The back tower reaches the skyline cap; foreground towers stay lower.
        factor=1.0 if index==0 else shape_rng.uniform(.55,.86)
        h=max(32,int(params["skyline_height"]*factor/6)*6)
        kind=shape_rng.randrange(3)
        accent=choose_accent(index)
        neon=index<params["neon_buildings"]
        beacon=index<params["rooftop_beacons"]
        add(u+v+w+d,lambda u=u,v=v,w=w,d=d,h=h,kind=kind,accent=accent,neon=neon,beacon=beacon:building(u,v,w,d,h,kind,accent,neon,beacon))
        occupied.add((int((u-34)//184),int((v-34)//184)))
    for col,u in enumerate([34,218,402]):
        for row,v in enumerate([34,218,402]):
            if (col,row) not in occupied and (col,row)!=(2,2):
                flat(u+13,v+13,118,118,5.2,'#203f46','#355862')
                flat(u+58,v+13,12,118,5.3,'#3c515f')
                flat(u+13,v+58,118,12,5.3,'#3c515f')
    # A small public square occupies the front right block.
    flat(410,410,128,128,5.2,'#263c4c')
    for t in range(416,538,12):
        line(p(410,t,5.3),p(538,t,5.3),'#45606a',.6)
        line(p(t,410,5.3),p(t,538,5.3),'#45606a',.6)
    def fountain():
        box(446,450,47,47,5.4,6,'#648196','#3b5a70','#2b475b')
        flat(449,453,41,41,11.5,'#31788c','#7dbfc9')
        box(463,467,13,13,11.5,17,'#9de6e5','#4b9eae','#317b94')
        x,y=p(469,473,37);circle(x,y,6,'#a9f5ed','filter="url(#glow)"')
    add(950,fountain)
    for u,v in [(43,165),(170,160),(231,167),(353,164),(412,169),(542,164),(43,352),(172,350),(228,352),(353,351),(410,352),(542,350),(43,540),(171,538),(231,540),(349,540),(418,426),(528,427),(418,531),(532,530)][:params["tree_count"]]:
        add(u+v+10,lambda u=u,v=v:tree(u,v))
    def lamp(u,v):
        flat(u-6,v-6,12,12,2.4,'#476477')
        line(p(u,v,3),p(u,v,47),'#7393a4',1.7)
        line(p(u,v,47),p(u+8,v,49),'#93acb7',1.5)
        x,y=p(u+8,v,48);circle(x,y,3,'#ffe5b1','filter="url(#glow)"')
        flat(u-10,v-10,28,22,2.6,'#ffc77b',None)
        # This light pool has its own opacity; the pole remains sharp.
        out[-1]=out[-1].replace('/>','opacity=".07"/>')
    for u,v in [(31,180),(211,180),(396,180),(549,180),(31,364),(211,364),(396,364),(549,364),(31,549),(211,549),(396,549),(549,549)]:
        add(u+v+5,lambda u=u,v=v:lamp(u,v))
    def car(u,v,axis,color):
        w,d=(24,11) if axis==0 else (11,24)
        flat(u-3,v-3,w+6,d+6,2.3,'#080f20')
        box(u,v,w,d,3,7,color,'#294355','#152839')
        box(u+w*.25,v+d*.2,w*.5,d*.6,10,5,color,'#142b40','#17384c')
        flat(u+w*.3,v+d*.25,w*.4,d*.5,15.2,'#7fb4c7')
        for t in [.18,.8]:
            x,y=p(u+w if axis==0 else u+w*t,v+d*t if axis==0 else v+d,6)
            circle(x,y,1.8,'#fff0ba','filter="url(#glow)"')
        line(p(u+w+2,v+d*.5,2.5),p(u+w+18,v+d*.5,2.5),'#b3d8d8',2,extra='opacity=".2"')
    car_slots=[(111,190,0),(293,375,0),(458,559,0),(191,281,1),(376,468,1),
               (560,112,1),(8,458,1),(63,559,0),(438,7,0),(190,72,1),
               (376,114,1),(190,470,1),(499,190,0),(104,375,0),(559,454,1),(281,7,0)]
    for index,(u,v,axis) in enumerate(car_slots[:params["car_count"]]):
        col=local_rng(f"car:{index}").choice(['#c6937b','#e6d1a8','#7ac3c4','#b26688','#96aabe'])
        add(u+v+30,lambda u=u,v=v,axis=axis,col=col:car(u,v,axis,col))
    for _,fn in sorted(objects,key=lambda item:item[0]):fn()
    # Subtle platform edge illumination.
    line(p(0,580,0),p(580,580,0),'#4595a5',1.1,extra='opacity=".5"')
    line(p(580,0,0),p(580,580,0),'#355277',1.1,extra='opacity=".6"')
    metadata={"schema_version":1,"statistics":stats,"parameters":params}
    # JSON is inert metadata, useful for inspecting the exact inputs and variables.
    meta=escape(json.dumps(metadata,ensure_ascii=False,sort_keys=True,separators=(',',':')))
    svg='\n'.join(out)
    svg=svg.replace('<title id="title">Isometric midnight city</title>', '<title id="title">'+escape(stats['username'])+' GitHub City</title>')
    description=(f"A generated isometric night city for {stats['username']}. "
                 f"{stats['commits']} commit contributions and {stats['pull_requests']} opened pull requests "
                 f"in the reporting period; {params['building_count']} buildings. "
                 f"Source: {stats.get('source','offline')}. Exact inputs are recorded in city-data metadata.")
    old_desc='An original vector illustration of a floating isometric city at night. Indigo skyscrapers, warm apartment windows, turquoise neon, cars, trees and streetlights beneath a crescent moon.'
    svg=svg.replace(old_desc,escape(description),1)
    svg=svg.replace('<defs>', '<metadata id="city-data">'+meta+'</metadata>\n<defs>',1)
    svg=svg.replace('role="img"',f'role="img" data-buildings="{params["building_count"]}" data-commits="{stats["commits"]}" data-pull-requests="{stats["pull_requests"]}"',1)
    return svg+'\n</svg>\n' 
