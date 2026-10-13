#!/usr/bin/env python3
"""Build BETA Labs brand-guide masters from the supplied SVG and licensed fonts."""
from pathlib import Path
import copy
import hashlib
import html
import json
import shutil
import xml.etree.ElementTree as ET
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "brand/guide"
ASSETS = OUT / "assets"
C = {"cream":"#F8F6F2", "ink":"#343434", "lime":"#EDF993", "white":"#FFFFFF"}
SVG_NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('',SVG_NS)
ORIGINAL = ROOT / 'brand/assets/logos/betalabs-original.svg'
ORIGINAL_HASH = 'ca396bcfa11b576d56690536c8889ede5ca461c20e7bb0252134a781b61a4538'
FONT_URLS = {
 'Inter.ttf':'https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf',
 'Inter-OFL.txt':'https://raw.githubusercontent.com/google/fonts/main/ofl/inter/OFL.txt',
 'Newsreader-Italic.ttf':'https://raw.githubusercontent.com/google/fonts/main/ofl/newsreader/Newsreader-Italic%5Bopsz%2Cwght%5D.ttf',
 'Newsreader-OFL.txt':'https://raw.githubusercontent.com/google/fonts/main/ofl/newsreader/OFL.txt'}
fonts = {}
asset_records = []


def font(family='Inter',weight=400):
    cache=(family,weight)
    if cache not in fonts:
        f=TTFont(ASSETS/'fonts'/('Inter.ttf' if family=='Inter' else 'Newsreader-Italic.ttf'))
        settings={'wght':weight,'opsz':32 if family=='Inter' else 48}
        fonts[cache]=instantiateVariableFont(f,settings,inplace=False)
    return fonts[cache]


def measure(s,size,family='Inter',weight=400):
    f=font(family,weight);cmap=f.getBestCmap();scale=size/f['head'].unitsPerEm
    return sum(f['hmtx'].metrics[cmap.get(ord(ch),'.notdef')][0] for ch in s)*scale


def text(s,x,y,size=32,color=None,family='Inter',weight=400):
    f=font(family,weight);cmap=f.getBestCmap();glyphs=f.getGlyphSet();scale=size/f['head'].unitsPerEm
    chunks=[f'<g aria-label="{html.escape(s,quote=True)}" fill="{color or C["ink"]}">'];advance=0
    for ch in s:
        name=cmap.get(ord(ch),'.notdef');pen=SVGPathPen(glyphs);glyphs[name].draw(pen)
        d=pen.getCommands()
        if d:chunks.append(f'<path transform="translate({x+advance*scale:.3f} {y}) scale({scale:.6f} {-scale:.6f})" d="{d}"/>')
        advance+=f['hmtx'].metrics[name][0]
    return ''.join(chunks)+'</g>'


def wrap(s,x,y,width,size=28,color=None,weight=400,line=1.5):
    lines=[];current=''
    for word in s.split():
        trial=(current+' '+word).strip()
        if current and measure(trial,size,weight=weight)>width:lines.append(current);current=word
        else:current=trial
    if current:lines.append(current)
    return ''.join(text(s,x,y+i*size*line,size,color,weight=weight) for i,s in enumerate(lines))


def wordmark(x,y,width,color):
    root=ET.fromstring(ORIGINAL.read_bytes())
    for e in root.iter():
        if e.tag.endswith('path'):e.set('fill',color)
    body=''.join(ET.tostring(e,encoding='unicode') for e in root)
    return f'<g transform="translate({x} {y}) scale({width/1053:.8f})">{body}</g>'


def mark(x,y,size,color):
    p=copy.deepcopy(list(ET.fromstring(ORIGINAL.read_bytes()))[0]);p.set('fill',color)
    return f'<g transform="translate({x} {y}) scale({size/160:.8f})"><g transform="translate(9 11)">{ET.tostring(p,encoding="unicode")}</g></g>'


def line(x1,y1,x2,y2,color=None,width=2,extra=''):
    return f'<path d="M{x1} {y1}L{x2} {y2}" fill="none" stroke="{color or C["ink"]}" stroke-width="{width}" {extra}/>'


def save_svg(name,w,h,body,kind,title,bg=None):
    p=ASSETS/name;p.parent.mkdir(parents=True,exist_ok=True)
    rect=f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ''
    content=f'<svg xmlns="{SVG_NS}" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title,quote=True)}"><title>{html.escape(title)}</title>{rect}{body}</svg>\n'
    p.write_text(content)
    asset_records.append({'path':str(p.relative_to(ROOT)), 'width':w,'height':h,'kind':kind,'title':title,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    return name


def dot_field(w,h,focus=True):
    chunks=[]
    for row in range(1,int(h/45)):
        for col in range(1,int(w/45)):
            x=col*45;y=row*45
            chunks.append(f'<circle cx="{x}" cy="{y}" r="2.4" fill="{C["ink"]}" opacity=".18"/>')
    if focus:
        x=w*.66;y=h*.48
        chunks.append(f'<circle cx="{x}" cy="{y}" r="15" fill="{C["lime"]}" stroke="{C["ink"]}" stroke-width="2"/>')
        chunks.append(f'<circle cx="{x}" cy="{y}" r="37" fill="none" stroke="{C["ink"]}" stroke-width="1.5"/>')
    return ''.join(chunks)


def build():
    assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()==ORIGINAL_HASH,'Supplied original changed'
    OUT.mkdir(parents=True,exist_ok=True)
    (ASSETS/'fonts').mkdir(parents=True,exist_ok=True)
    for name,url in FONT_URLS.items():
        src=Path('/tmp')/('betalabs-'+name);dest=ASSETS/'fonts'/name
        if not dest.exists():shutil.copyfile(src,dest)
        if name.endswith('.txt'):assert 'SIL OPEN FONT LICENSE' in dest.read_text()
        else:TTFont(dest)
    (ASSETS/'logos').mkdir(parents=True,exist_ok=True)
    original_copy=ASSETS/'logos/primary-original.svg'
    shutil.copyfile(ORIGINAL,original_copy)
    asset_records.append({'path':str(original_copy.relative_to(ROOT)), 'width':1053,'height':141,'kind':'provided_original','sha256':ORIGINAL_HASH,'title':'Unmodified wordmark supplied by user'})
    for suffix,color in [('charcoal',C['ink']),('cream',C['cream']),('white','#FFFFFF'),('black','#000000')]:
        save_svg(f'logos/primary-{suffix}.svg',1053,141,wordmark(0,0,1053,color),'wordmark_variant','BETA Labs primary wordmark, geometry preserved')
        save_svg(f'logos/logomark-{suffix}.svg',160,160,mark(0,0,160,color),'derived_logomark','B monogram extracted from supplied wordmark')
    for suffix,bg,fg in [('lime',C['lime'],C['ink']),('charcoal',C['ink'],C['cream']),('cream',C['cream'],C['ink'])]:
        save_svg(f'logos/avatar-{suffix}.svg',400,400,mark(70,70,260,fg),'avatar','BETA Labs monogram avatar',bg)
    save_svg('logos/stacked-lockup.svg',600,380,mark(225,34,150,C['ink'])+wordmark(70,248,460,C['ink']),'lockup','Proposed stacked lockup',C['cream'])
    # Clearspace is based on the supplied SVG height, not an invented font glyph.
    w=900;logo_w=650;logo_h=logo_w*141/1053;x=logo_h/2;lx=(w-logo_w)/2;ly=155
    body=f'<rect x="{lx-x}" y="{ly-x}" width="{logo_w+2*x}" height="{logo_h+2*x}" fill="none" stroke="{C["ink"]}" stroke-dasharray="5 5"/>'+wordmark(lx,ly,logo_w,C['ink'])
    body+=line(lx-x,ly+logo_h+x+25,lx,ly+logo_h+x+25)+text('x',lx-x+12,ly+logo_h+x+52,22)
    body+=text('x = H / 2',65,60,25,weight=600)+text('H = full wordmark height',65,98,20)+text('Keep this zone free of type, images and edges.',65,405,20)
    save_svg('rules/logo-clearspace.svg',900,460,body,'clearspace','Wordmark clearspace specification',C['cream'])
    save_svg('rules/mark-clearspace.svg',600,460,f'<rect x="165" y="65" width="270" height="270" fill="none" stroke="{C["ink"]}" stroke-dasharray="5 5"/>'+mark(210,110,180,C['ink'])+text('Clearspace = 1/4 symbol width',60,400,22),'clearspace','Proposed symbol clearspace',C['cream'])
    save_svg('patterns/signal-field.svg',1400,850,dot_field(1400,850),'pattern','Signal field pattern',C['cream'])
    body=''
    for x,y in [(180,360),(460,150),(720,430),(1030,210),(1230,620)]:
        body+=f'<circle cx="{x}" cy="{y}" r="9" fill="{C["cream"]}" stroke="{C["ink"]}" stroke-width="2"/>'
    body+=line(180,360,460,150,width=1)+line(460,150,720,430,width=1)+line(720,430,1030,210,width=1)+line(1030,210,1230,620,width=1)
    body+=f'<circle cx="720" cy="430" r="18" fill="{C["lime"]}" stroke="{C["ink"]}" stroke-width="2"/>'
    save_svg('patterns/signal-network.svg',1400,850,body,'pattern','Signal network illustration, conceptual',C['cream'])
    body=f'<circle cx="700" cy="425" r="24" fill="{C["lime"]}" stroke="{C["ink"]}" stroke-width="2"/>'
    for x,y,sx,sy in [(450,180,1,1),(950,180,-1,1),(450,670,1,-1),(950,670,-1,-1)]:body+=line(x,y,x+sx*70,y)+line(x,y,x,y+sy*70)
    save_svg('patterns/precision-frame.svg',1400,850,body,'pattern','Precision framing pattern',C['cream'])
    steps=[('01','Define the ICP','Company, role, technology and buying signal.'),('02','Work from the list','Attendee data under an organizer agreement.'),('03','Explain the fit','Ranked profiles with a reason for each choice.'),('04','Start the conversation','Opening drafts sent by the sponsor.')]
    body=text('The work behind each match.',60,80,48,weight=600)
    for i,(n,title,desc) in enumerate(steps):
        x=60+i*345
        body+=text(n,x,190,58,C['ink'],family='Newsreader')+line(x,222,x+280,222,width=1)
        body+=wrap(title,x,278,275,26,weight=600)+wrap(desc,x,375,275,22,line=1.6)
        if i<3:body+=line(x+283,240,x+327,240,width=1.5)
    body+=text('Process illustration. No conversion or outcome metrics implied.',60,645,20)
    save_svg('diagrams/process-infographic.svg',1440,700,body,'infographic','BETA Labs four-stage process',C['cream'])
    body=text('From noise to a reason.',65,90,50,weight=600)
    body+=dot_field(630,470)
    body+=line(650,320,805,320,width=2)+line(788,309,805,320,width=2)+line(788,331,805,320,width=2)
    body+=f'<rect x="845" y="175" width="490" height="340" rx="12" fill="{C["white"]}" stroke="{C["ink"]}"/>'
    body+=text('Biron Systems',882,235,36,weight=600)+text('Illustrative, fictional profile',882,271,20)
    body+=line(880,294,1300,294,width=1)+text('Criterion',882,340,20,weight=600)+text('Multi-site retail operations',882,377,24)
    body+=text('Signal',882,428,20,weight=600)+text('Omnichannel project in preparation',882,465,21)
    body+=text('A shortlist is useful when every priority is explained.',65,615,26)
    save_svg('diagrams/signal-infographic.svg',1440,700,body,'infographic','Illustrative selection and qualifying signal',C['cream'])
    body=text('Two roles. One useful preparation.',65,85,46,weight=600)
    rows=[(210,'Organizer',['Agreement','Attendee list','Sponsor introduction']),(470,'Sponsor',['ICP brief','Shortlist & signals','Sponsor sends'])]
    for y,role,nodes in rows:
        body+=text(role,65,y+20,30,weight=600)
        for i,label in enumerate(nodes):
            x=345+i*330
            body+=f'<rect x="{x}" y="{y-40}" width="280" height="120" rx="12" fill="{C["lime"] if i==2 else C["white"]}" stroke="{C["ink"]}"/>'
            body+=wrap(label,x+22,y+12,238,23,weight=500)
            if i<2:body+=line(x+280,y+20,x+330,y+20,width=1.5)
    body+=text('The organizer is a data and distribution partner; the sponsor owns its conversations.',65,665,21)
    save_svg('diagrams/dual-motion-schema.svg',1440,740,body,'schema','Organizer and sponsor responsibilities',C['cream'])
    # Social assets: text is outlined so exports are identical across renderers.
    social=[('statement-portrait',1080,1350,['Know who matters','before you arrive.'],'Your shortlist. A reason for every priority.'),('signal-square',1080,1080,['Every match.','A reason.'],'The signal before the crowd.'),('preparation-story',1080,1920,['Your event.','Your priorities.'],'Start with the criteria that matter to your business.')]
    for name,w,h,head,caption in social:
        body=wordmark(86,75,330,C['ink'])+text('PRE-EVENT TARGETING',86,225,20,weight=600)
        for i,s in enumerate(head):body+=text(s,80,350+i*105,82,C['ink'],family='Newsreader' if i==1 else 'Inter',weight=400 if i==1 else 600)
        field_h=h-690
        if field_h>100:body+=f'<g transform="translate(40 540)">{dot_field(1000,field_h)}</g>'
        body+=line(86,h-210,w-86,h-210,width=1)+wrap(caption,86,h-155,w-172,28)+text('BETA Labs · Pre-event targeting',86,h-60,19)
        save_svg(f'social/{name}.svg',w,h,body,'social_creative',name.replace('-',' '),C['cream'])
    for i,(n,title,desc) in enumerate(steps):
        body=wordmark(86,75,330,C['ink'])+text('THE PREPARATION SERIES',86,224,20,weight=600)
        body+=text(n,75,450,210,C['ink'],family='Newsreader')+line(86,535,994,535,width=1)
        body+=wrap(title,86,655,890,72,weight=600,line=1.1)+wrap(desc,86,880,850,38,line=1.45)
        body+=f'<circle cx="935" cy="1180" r="24" fill="{C["lime"]}" stroke="{C["ink"]}" stroke-width="2"/>'+text(f'{i+1} / 4',86,1255,24)
        save_svg(f'social/carousel-{i+1:02}.svg',1080,1350,body,'carousel','Preparation carousel '+n,C['cream'])
    banners=[('linkedin-company',1128,191,{'left':45,'top':35,'copy_x':390,'copy_y':105,'size':31}),('linkedin-profile',1584,396,{'left':400,'top':46,'copy_x':400,'copy_y':230,'size':58}),('facebook-page',1640,624,{'left':140,'top':78,'copy_x':140,'copy_y':360,'size':76}),('x-profile',1500,500,{'left':340,'top':70,'copy_x':340,'copy_y':280,'size':64}),('youtube-channel',2560,1440,{'left':700,'top':550,'copy_x':700,'copy_y':760,'size':66})]
    for name,w,h,opt in banners:
        body=wordmark(opt['left'],opt['top'],270 if h<300 else 380,C['ink'])
        phrase='The signal before the crowd.' if h<300 else 'Know who matters.'
        body+=text(phrase,opt['copy_x'],opt['copy_y'],opt['size'],C['ink'],weight=600)
        if h>=300:body+=text('Before the event begins.',opt['copy_x'],opt['copy_y']+opt['size']*1.15,opt['size']*.68,C['ink'],family='Newsreader')
        if name!='youtube-channel':body+=f'<circle cx="{w-105}" cy="{h*.53}" r="{14 if h<300 else 22}" fill="{C["lime"]}" stroke="{C["ink"]}" stroke-width="2"/>'
        save_svg(f'banners/{name}.svg',w,h,body,'page_banner',name.replace('-',' ')+' export target',C['cream'])
    manifest={'version':'2.0-proposal','as_of':'2026-10-13','supplied_logo':{'path':str(ORIGINAL.relative_to(ROOT)),'sha256':ORIGINAL_HASH,'source':'user upload betalabs.svg','geometry':'1053 x 141; eight paths; original cream fill'},'fonts':[{'path':str((ASSETS/'fonts'/name).relative_to(ROOT)),'url':url,'sha256':hashlib.sha256((ASSETS/'fonts'/name).read_bytes()).hexdigest(),'license':'SIL Open Font License 1.1'} for name,url in FONT_URLS.items()],'assets':asset_records,'notes':['Wordmark geometry comes from the supplied original.','B symbol, clearspace, Newsreader accent and application rules are proposed extensions.','Black/white logo variants are monochrome production exceptions.','Banner dimensions are chosen export targets, not live-verified platform requirements.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    build_html()
    print(f'Built {len(asset_records)} SVG masters and a 16-section brand guide.')


def img(path,cls='',style=''):
    return f'<img src="assets/{path}" class="{cls}" style="{style}" alt="{html.escape(path.replace("-"," "))}">'


def build_html():
    pages=[]
    def page(title,body,chapter='',dark=False):
        n=len(pages)+1
        pages.append(f'<section class="page {"dark" if dark else ""}" id="page-{n}"><div class="running"><span>BETA Labs · Brand guide</span><span>V2 · 13 October 2026</span></div><div class="chapter">{chapter or str(n).zfill(2)}</div><h1>{title}</h1><div class="content">{body}</div><div class="folio"><span>The signal before the crowd.</span><span>{n:02d}</span></div></section>')
    page('The signal.<br><em>Before the crowd.</em>',f'<div class="cover-logo">{img("logos/primary-cream.svg")}</div><p class="cover-note">A practical identity system.<br>Logo, typography, color, imagery and applications.</p><div class="status">Proposed brand extension · Supplied wordmark preserved</div>','BETA LABS / 2026',True)
    page('Precision, made <em>visible.</em>','<div class="two"><div><p class="big">BETA Labs turns the organizer’s attendee list into a shortlist of prospects worth preparing for.</p><p>Every profile comes with a signal and an opening draft. The sponsor sends the message and keeps the relationship.</p></div><div class="principles"><div><b>Specific.</b><p>Explain the reason for each priority.</p></div><div><b>Composed.</b><p>Use restraint, space and clear hierarchy.</p></div><div><b>Useful.</b><p>Show the actual deliverable, not an outcome guarantee.</p></div></div></div>')
    page('The primary <em>logo.</em>',f'<div class="logo-stage dark-stage">{img("logos/primary-cream.svg")}</div><div class="logo-stage">{img("logos/primary-charcoal.svg")}</div><div class="two small"><p>The horizontal wordmark is the primary signature. The supplied SVG is the geometry master: eight paths, 1053 × 141.</p><p>Use cream on charcoal and charcoal on cream. Black/white variants are reserved for one-color production.</p></div>')
    page('One letter.<br>A recognizable <em>mark.</em>',f'<div class="marks"><div>{img("logos/logomark-charcoal.svg")}<label>Standalone B</label></div><div class="lime-stage">{img("logos/avatar-lime.svg")}<label>Avatar carrier</label></div><div>{img("logos/stacked-lockup.svg")}<label>Secondary stacked lockup</label></div></div><p class="small">The B symbol is extracted from the supplied wordmark. It is a proposed derivative for avatars, small formats and graphic signatures. Do not substitute it where the full name is needed.</p>')
    page('Space is part of<br>the <em>signature.</em>',f'<div class="two">{img("rules/logo-clearspace.svg")}{img("rules/mark-clearspace.svg")}</div><div class="three small"><p><b>Wordmark.</b><br>x = H/2 on every side. H is the full logo height.</p><p><b>Minimum.</b><br>Wordmark: 180 px digital / 35 mm print proposed. Symbol: 16 px minimum; 32 px+ preferred for avatars.</p><p><b>Preserve.</b><br>No stretching, rotation, outline effects, shadows or low-contrast placement. Keep all letter contours unchanged.</p></div>')
    page('Type with <em>intent.</em>','<div class="type-name">Inter</div><p class="big">The primary typeface. Precise, clear and adaptable.</p><p class="alphabet">ABCDEFGHIJKLMNOPQRSTUVWXYZ<br>abcdefghijklmnopqrstuvwxyz<br>0123456789</p><div class="serif-name">Newsreader Italic</div><p class="small">A proposed editorial accent, one expression per headline. Inter remains the primary face. Both fonts are included under SIL OFL. Newsreader replaces the unavailable Chiron accent in this proposed system; it is not a measured site font.</p>')
    page('Hierarchy creates<br><em>focus.</em>','<div class="type-table"><div><span>Display · Inter 600 · 64–88 / 1.05</span><b style="font-size:64px">Find the signal.</b></div><div><span>Section · Inter 600 · 36–48 / 1.15</span><b style="font-size:40px">Every priority, explained.</b></div><div><span>Body · Inter 400 · 16–18 / 1.6</span><p>Prepare the conversation before the event. Each shortlist profile carries a qualifying signal and an opening draft.</p></div><div><span>Label · Inter 500 · 11–13 / 1.5 · +0.06em caps</span><label>THE WORK BEHIND THE MATCH</label></div></div><p class="small">Use 400 for reading, 500 for emphasis, 600 for announcing. Limit body lines to 50–70 characters. Scale headings on mobile; do not shrink the entire desktop composition.</p>')
    swatches=''.join(f'<div class="swatch" style="background:{v};color:{C["cream"] if k=="ink" else C["ink"]}"><b>{k.title()}</b><span>{v}</span></div>' for k,v in C.items())
    page('A quiet palette.<br>A clear <em>signal.</em>',f'<div class="swatches">{swatches}</div><div class="two"><p><b>Cream + charcoal.</b><br>The identity’s atmosphere and structure. Use for backgrounds, type, rules and diagrams.</p><p><b>Lime.</b><br>Reserve for the selected signal or a primary action. Use dark text and a charcoal outline when the shape needs definition.</p></div><table><tr><th>Pair</th><th>Contrast</th><th>Use</th></tr><tr><td>Charcoal / cream</td><td>11.53:1</td><td>Body, display, controls</td></tr><tr><td>Charcoal / lime</td><td>11.01:1</td><td>Selection and action</td></tr><tr><td>Lime / cream</td><td>≈1.05:1</td><td>Decorative fill; outline required for meaningful shape</td></tr></table><p class="small">Digital masters use RGB hex values. One-color production variants are separate from the main palette. Verify print conversion against the chosen printer/profile.</p>')
    imagery=ASSETS/'imagery/brand-study.png'
    visual=img('imagery/brand-study.png','imagery-study') if imagery.exists() else img('patterns/precision-frame.svg','imagery-study')
    page('Imagery with<br>a <em>reason.</em>',f'<div class="two"><div>{visual}</div><div><p class="big">Show the shift from an indistinct field to an explained priority.</p><p>Core imagery: geometric fields, framing, one selected signal and product explanations. Keep backgrounds quiet and crops deliberate.</p><p>Editorial material studies are an optional proposed extension. Avoid stock teams, handshake clichés, generic AI glow and screenshots with real attendee data.</p><p class="small">Generated or fictional imagery illustrates the identity. It is not customer proof or a measured product result.</p></div></div>')
    page('Patterns that<br>carry the <em>idea.</em>',f'<div class="pattern-grid">{img("patterns/signal-field.svg")}{img("patterns/precision-frame.svg")}{img("patterns/signal-network.svg")}</div><div class="three small"><p><b>Signal field.</b><br>Many points, one priority. Use as a restrained environment.</p><p><b>Precision frame.</b><br>Corners and a selected point. Use for crops, section signatures and covers.</p><p><b>Signal network.</b><br>A conceptual relationship map. Never present it as actual participant data.</p></div>')
    page('Infographics,<br>without invented <em>numbers.</em>',f'{img("diagrams/process-infographic.svg","diagram")}<p class="small">Show stages, inputs and responsibilities. Numbers 01–04 identify process steps, not conversion rates. Any performance infographic requires a named dataset, unit, period and denominator.</p>')
    page('Explain the<br><em>signal.</em>',f'{img("diagrams/signal-infographic.svg","diagram")}<p class="small">A fictional example can demonstrate criteria, signal and prioritization. Label the example clearly. Avoid false precision or a guaranteed number of matches.</p>')
    page('Schemas clarify<br><em>responsibility.</em>',f'{img("diagrams/dual-motion-schema.svg","diagram")}<p class="small">Keep organizer, BETA Labs and sponsor roles distinct. The organizer enables data and distribution; BETA Labs prepares the shortlist; the sponsor sends the message and owns the relationship.</p>')
    page('Social, as a<br><em>family.</em>',f'<div class="social-gallery">{img("social/statement-portrait.svg")}{img("social/signal-square.svg")}{img("social/preparation-story.svg")}</div><div class="three small"><p><b>Feed portrait.</b><br>1080 × 1350. One thought, one focal move.</p><p><b>Square.</b><br>1080 × 1080. Use for a sharp statement or simple mechanism.</p><p><b>Story.</b><br>1080 × 1920. Keep essential content away from interface overlays.</p></div>')
    page('Build a useful<br><em>sequence.</em>',f'<div class="carousel-gallery">'+''.join(img(f'social/carousel-{i:02}.svg') for i in range(1,5))+'</div><p class="small">Four editable vector masters: ICP, list, signal and opening. Each slide owns one idea. Preserve the rhythm, generous margins and footer orientation. Change copy through the source recipe rather than scaling text until it becomes unreadable.</p>')
    page('Banners with<br><em>breathing room.</em>',f'<div class="banners-gallery">{img("banners/linkedin-company.svg")}{img("banners/linkedin-profile.svg")}{img("banners/facebook-page.svg")}{img("banners/x-profile.svg")}{img("banners/youtube-channel.svg")}</div><p class="small">Export targets: LinkedIn company 1128×191; LinkedIn profile 1584×396; Facebook page 1640×624; X 1500×500; YouTube 2560×1440. Composition reserves avatar/center-safe areas. Platform crops and requirements should be checked at upload; these are not newly verified platform specs.</p>')
    css='''@font-face{font-family:Inter;src:url(assets/fonts/Inter.ttf);font-weight:100 900}@font-face{font-family:Newsreader;src:url(assets/fonts/Newsreader-Italic.ttf);font-weight:200 800;font-style:italic}*{box-sizing:border-box}body{margin:0;padding:32px;background:#dedcd7;color:#343434;font-family:Inter,Arial,sans-serif}.page{position:relative;width:1280px;height:905px;margin:0 auto 32px;padding:58px 68px 66px;background:#F8F6F2;overflow:hidden;break-after:page}.running,.folio{display:flex;justify-content:space-between;font-size:11px;letter-spacing:.04em}.running{border-bottom:1px solid #34343444;padding-bottom:15px}.folio{position:absolute;bottom:30px;left:68px;right:68px;border-top:1px solid #34343444;padding-top:13px}.chapter{font-size:11px;letter-spacing:.12em;margin-top:32px}.page h1{font-size:54px;line-height:1.1;letter-spacing:-.04em;font-weight:600;margin:14px 0 30px;max-width:1050px}em{font-family:Newsreader,Georgia,serif;font-weight:400}.content p{font-size:18px;line-height:1.55;margin:12px 0 20px}.content p.big{font-size:30px;line-height:1.4;letter-spacing:-.02em}.content p.small,.small p{font-size:13px;line-height:1.65}.two,.three{display:grid;grid-template-columns:repeat(2,1fr);gap:40px}.three{grid-template-columns:repeat(3,1fr);gap:26px}.two img{width:100%;max-height:440px;object-fit:contain}.dark{background:#343434;color:#F8F6F2}.dark .running,.dark .folio{border-color:#f8f6f244}.dark h1{font-size:84px;line-height:1.05;max-width:960px}.cover-logo{position:absolute;right:68px;bottom:115px;width:400px}.cover-logo img{width:100%}.cover-note{margin-top:85px!important}.status{font-size:11px;letter-spacing:.03em;margin-top:50px}.principles div{padding:18px 0;border-bottom:1px solid #34343444}.principles b{font-size:28px}.principles p{font-size:16px;margin-bottom:10px}.logo-stage{height:155px;display:flex;align-items:center;justify-content:center;border:1px solid #34343433;margin-bottom:18px;padding:45px 100px}.logo-stage img{max-width:100%;height:100%}.dark-stage{background:#343434}.marks{display:grid;grid-template-columns:1fr 1fr 1.4fr;gap:30px;height:340px;margin-bottom:36px}.marks>div{padding:25px;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#FFFFFF}.marks img{max-width:100%;max-height:230px}.marks label{font-size:12px;margin-top:25px}.marks .lime-stage{background:#EDF993}.type-name{font-size:86px;line-height:1;font-weight:600;letter-spacing:-.055em}.alphabet{font-size:29px!important;line-height:1.5!important;letter-spacing:.01em}.serif-name{font-family:Newsreader,Georgia,serif;font-style:italic;font-size:58px;line-height:1.2;margin-top:35px}.type-table>div{padding:12px 0;border-top:1px solid #34343433}.type-table span{display:block;font-size:11px;color:#65635f;margin-bottom:9px}.type-table b{font-weight:600;letter-spacing:-.03em;line-height:1.15}.type-table p{max-width:790px;font-size:18px}.type-table label{font-size:12px;letter-spacing:.08em;font-weight:500}.swatches{display:flex;height:190px;margin-bottom:25px}.swatch{width:25%;display:flex;flex-direction:column;justify-content:space-between;padding:24px;border:1px solid #34343444}.swatch b{font-size:25px}.swatch span{font-size:14px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;border-bottom:1px solid #34343433;padding:11px}.imagery-study{width:100%;height:420px;object-fit:cover;border:1px solid #34343433}.pattern-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-bottom:25px}.pattern-grid img{width:100%;height:290px;object-fit:cover;border:1px solid #34343433}.diagram{display:block;width:100%;height:440px;object-fit:contain}.social-gallery{display:grid;grid-template-columns:1fr 1fr .72fr;gap:28px;height:355px;margin-bottom:26px}.social-gallery img{width:100%;height:355px;object-fit:contain}.carousel-gallery{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;height:390px;margin-bottom:20px}.carousel-gallery img{width:100%;height:100%;object-fit:contain}.banners-gallery{display:grid;grid-template-columns:1fr 1fr;gap:14px;height:415px}.banners-gallery img{width:100%;height:115px;object-fit:contain;border:1px solid #34343422}.banners-gallery img:first-child{grid-column:span 2;height:88px}.banners-gallery img:last-child{height:110px}@page{size:A4 landscape;margin:0}@media print{body{padding:0;background:white}.page{width:297mm;height:210mm;margin:0;padding:13.5mm 15.8mm 15mm}.running,.folio{font-size:8px}.running{padding-bottom:8px}.folio{left:15.8mm;right:15.8mm;bottom:7mm;padding-top:8px}.chapter{margin-top:15px;font-size:8px}.page h1{font-size:37px;margin:9px 0 18px}.dark h1{font-size:64px}.content p{font-size:13px;margin:8px 0 13px}.content p.big{font-size:21px}.content p.small,.small p{font-size:10px}.two,.three{gap:23px}.two img{max-height:310px}.logo-stage{height:104px;margin-bottom:10px;padding:30px 75px}.marks{height:240px;margin-bottom:20px}.marks img{max-height:160px}.marks label{font-size:10px;margin-top:15px}.type-name{font-size:64px}.alphabet{font-size:22px!important;line-height:1.4!important}.serif-name{font-size:42px;margin-top:22px}.type-table>div{padding:7px 0}.type-table span{font-size:9px;margin-bottom:6px}.type-table b{font-size:36px!important}.type-table>div:nth-child(2) b{font-size:28px!important}.type-table p{font-size:14px}.swatches{height:120px;margin-bottom:16px}.swatch{padding:16px}.swatch b{font-size:19px}.swatch span{font-size:10px}table{font-size:10px}th,td{padding:7px}.imagery-study{height:285px}.pattern-grid{margin-bottom:16px}.pattern-grid img{height:195px}.diagram{height:300px}.social-gallery{height:250px;margin-bottom:15px}.social-gallery img{height:250px}.carousel-gallery{height:285px;margin-bottom:12px}.banners-gallery{height:288px;gap:9px}.banners-gallery img{height:75px}.banners-gallery img:first-child{height:60px}.banners-gallery img:last-child{height:75px}.cover-logo{right:15.8mm;bottom:27mm;width:95mm}.cover-note{margin-top:50px!important}.status{font-size:9px;margin-top:32px}}
'''
    content=f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>BETA Labs — Brand guide v2</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>{css}</style></head><body>'+''.join(pages)+'</body></html>'
    (OUT/'index.html').write_text(content)


if __name__=='__main__':build()
