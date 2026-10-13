#!/usr/bin/env python3
"""Render brand guide and all vector masters, preserving transparent logo exports."""
import asyncio
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from PIL import Image
import hashlib

ROOT=Path(__file__).resolve().parents[1]
GUIDE=ROOT/'brand/guide'


async def main():
    from playwright.async_api import async_playwright
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    output=GUIDE/'exports';output.mkdir(exist_ok=True);pngdir=output/'png';pngdir.mkdir(exist_ok=True)
    manifest=json.loads((GUIDE/'manifest.json').read_text())
    report={'version':manifest['version'],'as_of':'2026-10-13','svg_assets':len(manifest['assets']),'exports':[],'guide_pages':16,'observed_website':False,'status':'pass'}
    try:
        async with async_playwright() as p:
            browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            guide=await browser.new_page(viewport={'width':1400,'height':1000},device_scale_factor=1)
            errors=[];guide.on('pageerror',lambda err:errors.append(str(err)))
            await guide.goto(base+'/brand/guide/index.html')
            await guide.evaluate('document.fonts.ready')
            assert await guide.locator('.page').count()==16
            assert await guide.evaluate("Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)"),'Guide image failed'
            assert not errors,errors
            for number in (1,3,4,5,6,8,9,14,16):
                await guide.locator(f'#page-{number}').screenshot(path=str(output/f'guide-page-{number:02}.png'))
            await guide.pdf(path=str(output/'BETA-Labs-Brand-Guide-v2.pdf'),print_background=True,prefer_css_page_size=True)
            await guide.emulate_media(media='print')
            page_overflows=await guide.locator('.page').evaluate_all("els=>els.map((e,i)=>({page:i+1,overflow:e.scrollHeight>e.clientHeight+1}))")
            assert not any(x['overflow'] for x in page_overflows),page_overflows
            report['page_overflows']=page_overflows
            await guide.close()
            for asset in manifest['assets']:
                src=ROOT/asset['path'];assert hashlib.sha256(src.read_bytes()).hexdigest()==asset['sha256']
                w,h=asset['width'],asset['height'];page=await browser.new_page(viewport={'width':w,'height':h},device_scale_factor=1)
                await page.set_content(f'<html><head><style>html,body{{margin:0;width:100%;height:100%;background:transparent}}img{{display:block;width:100%;height:100%;object-fit:contain}}</style></head><body><img src="{base}/{asset["path"]}" alt="brand asset"></body></html>')
                await page.locator('img').evaluate('(i)=>i.decode()')
                dest=pngdir/(src.parent.name+'--'+src.stem+'.png')
                await page.screenshot(path=str(dest),omit_background=True)
                with Image.open(dest) as image:
                    assert image.size==(w,h)
                    if asset['kind'] in ['provided_original','wordmark_variant','derived_logomark']:
                        assert image.mode=='RGBA' and image.getchannel('A').getextrema()[0]==0,'Logo PNG lost transparency'
                report['exports'].append({'path':str(dest.relative_to(ROOT)),'width':w,'height':h,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
                await page.close()
            await browser.close()
        (GUIDE/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
        print(f'PASS: {len(report["exports"])} PNG exports, 16 guide pages, image loading, original hashes, print overflow and transparent logos checked.')
    finally:
        server.shutdown();server.server_close()


if __name__=='__main__':asyncio.run(main())
