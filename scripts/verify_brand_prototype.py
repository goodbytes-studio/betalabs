#!/usr/bin/env python3
"""Render the local exploration and verify its interaction, layout and provenance."""
import asyncio
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "brand/prototypes/brand-direction-v1"


def luminance(rgb):
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in rgb]
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(front, back, alpha=1):
    def parse(value):
        return [int(value[i:i+2], 16)/255 for i in (1, 3, 5)]
    fg, bg = parse(front), parse(back)
    fg = [a*alpha + b*(1-alpha) for a,b in zip(fg,bg)]
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05)/(l2 + 0.05)


async def main():
    from playwright.async_api import async_playwright
    manifests = json.loads((ROOT / "brand/assets/manifest.json").read_text())
    for item in manifests["assets"]:
        assert hashlib.sha256((ROOT/item["path"]).read_bytes()).hexdigest() == item["sha256"]
    results = []
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/brand/prototypes/brand-direction-v1/index.html'
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/usr/bin/chromium", headless=True,
                                          args=["--no-sandbox", "--disable-dev-shm-usage"])
        for width in (1440, 390, 320):
            page = await browser.new_page(viewport={"width":width,"height":1000}, device_scale_factor=1)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(url)
            await page.evaluate("document.fonts.ready")
            assert await page.evaluate("document.fonts.check('16px Inter')"), "Inter failed to load"
            for lang in ("fr", "en"):
                await page.locator(f'[data-lang="{lang}"]').click()
                for audience in ("sponsor", "organizer"):
                    await page.locator(f'[data-audience="{audience}"]').click()
                    assert await page.locator('html').get_attribute('lang') == lang
                    assert await page.locator(f'[data-audience="{audience}"]').get_attribute('aria-pressed') == 'true'
                    assert await page.locator('#hero-title').inner_text()
                    assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Horizontal overflow at {width}/{lang}/{audience}"
                    assert not errors, errors
                    results.append({"width":width,"language":lang,"audience":audience,"overflow":False,"page_errors":0})
            await page.locator('[data-lang="fr"]').click()
            await page.locator('[data-audience="sponsor"]').click()
            await page.locator('#event-input').fill('Événement de démonstration')
            await page.locator('#target-input').fill('<script>alert("test")</script> Décideurs retail multisite')
            await page.locator('#brief-submit').click()
            assert await page.locator('#brief-result').is_visible()
            assert '<script>' in await page.locator('#brief-result').inner_text()
            assert await page.locator('#brief-result script').count() == 0
            await page.locator('[data-lang="en"]').click()
            assert not await page.locator('#brief-result').is_visible()
            await page.locator('[data-lang="fr"]').click()
            await page.locator('#event-input').fill('')
            await page.locator('#target-input').fill('')
            await page.evaluate("window.scrollTo(0,0)")
            if width in (1440,390):
                name='desktop.png' if width==1440 else 'mobile.png'
                await page.screenshot(path=str(OUT/name),full_page=True)
            await page.close()
        keyboard = await browser.new_page(viewport={"width":390,"height":900})
        await keyboard.goto(url)
        await keyboard.keyboard.press('Tab')
        assert await keyboard.evaluate("document.activeElement.classList.contains('wordmark')")
        await keyboard.keyboard.press('Tab')
        assert await keyboard.evaluate("document.activeElement.dataset.audience === 'sponsor'")
        await keyboard.keyboard.press('Tab')
        await keyboard.keyboard.press('Enter')
        assert await keyboard.locator('[data-audience="organizer"]').get_attribute('aria-pressed') == 'true'
        await keyboard.close()
        await browser.close()
    server.shutdown()
    server.server_close()
    ratios = {
        "ink_on_canvas":round(contrast('#343434','#F8F6F2'),2),
        "ink_on_signal":round(contrast('#343434','#EDF993'),2),
        "muted_ink_on_canvas":round(contrast('#343434','#F8F6F2',.76),2),
        "ink_72_percent_on_canvas":round(contrast('#343434','#F8F6F2',.72),2)
    }
    assert min(ratios.values()) >= 4.5, ratios
    report={"as_of":"2026-10-13","artifact":"local_brand_exploration_not_live_website", "status":"pass",
            "rendered_variants":results,"interaction_checks":["language_switch","audience_switch","brief_output","user_input_as_text","result_reset_on_switch","keyboard_navigation"],
            "contrast_ratios":ratios,"font_assets_integrity":"pass","website_audit_status":"blocked_by_egress_policy",
            "limitations":["Contrast checks cover specified token pairs, not a full WCAG audit.","No live-site screenshot or business conversion test."]}
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f"PASS: {len(results)} responsive language/audience variants, 6 interaction checks, token contrasts and font integrity.")


if __name__=='__main__':
    asyncio.run(main())
