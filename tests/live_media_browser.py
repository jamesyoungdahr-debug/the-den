"""M49 browser check: drive the watch page in headless Chromium (Playwright) against the server that `python tests/live_media.py <jpegs> --keep` left running.

Run in WSL from the repo root with the server venv: python tests/live_media_browser.py
The test admin token is read from /root/the-den-test/e2e-token.txt and sent as the X-Api-Key header; it is never printed. Screenshots go to M49_WORK."""

import json
import os
import sys
import time
from playwright.sync_api import sync_playwright

WORK = os.environ.get("M49_WORK", "/root/m49-live")
PORT = int(os.environ.get("M49_PORT", "40292"))
BASE = f"http://127.0.0.1:{PORT}"
TOKEN = open("/root/the-den-test/e2e-token.txt").read().strip()
IDS = json.load(open(os.path.join(WORK, "ids.json")))

failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ("" if ok else f"  got={got!r} want={want!r}"))
    if not ok:
        failures.append(name)


VIDEO = "document.querySelector('video.den-video')"


def hidden(page, selector):
    return page.evaluate("s => document.querySelector(s).hidden", selector)


def wait_js(page, expression, timeout=20000):
    page.wait_for_function(expression, timeout=timeout)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    context = browser.new_context(extra_http_headers={"X-Api-Key": TOKEN}, viewport={"width": 1280, "height": 800})
    page = context.new_page()

    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" and "Failed to load resource" not in msg.text and "fonts.gstatic.com" not in msg.text else None)  # the test's X-Api-Key header trips CORS on Google Fonts

    clip, old, e1, e2 = IDS["clip"], IDS["old"], IDS["e1"], IDS["e2"]

    def api_state(kind, item_id):
        r = context.request.get(f"{BASE}/api/play/{kind}/{item_id}")
        return r.json()["state"]

    # Case A: the playable movie
    try:
        context.request.post(f"{BASE}/api/play/movie/{clip}/watched", data={"played": False})
        page.goto(f"{BASE}/watch/movie/{clip}")
        wait_js(page, f"{VIDEO} && {VIDEO}.readyState >= 1")

        check("clip duration about 90 s", abs(page.evaluate(f"{VIDEO}.duration") - 90) < 1.5, True)
        check("one subtitle track", page.evaluate(f"{VIDEO}.textTracks.length"), 1)
        check("no resume offer at start", hidden(page, "[data-resume-box]"), True)
        check("tech line names vp8", "vp8" in page.inner_text("[data-tech]"), True)
        check("no playback notes", hidden(page, "[data-notes]"), True)

        page.evaluate(f"(() => {{ const v = {VIDEO}; v.muted = true; v.currentTime = 62; return v.play(); }})()")  # stays under the 90% mark of the 90 s clip
        wait_js(page, f"{VIDEO}.currentTime > 63", 20000)
        time.sleep(11.5)

        check("progress saved past a minute", api_state("movie", clip)["position_ms"] >= 60000, True)
        page.screenshot(path=os.path.join(WORK, "watch-playing.png"))

        page.evaluate(f"{VIDEO}.pause()")
        time.sleep(1)
        page.reload()
        wait_js(page, f"{VIDEO} && {VIDEO}.readyState >= 1")

        check("resume offered after reload", hidden(page, "[data-resume-box]"), False)
        check("resume time shown", page.inner_text("[data-resume-time]").startswith("1:1"), True)

        try:
            page.click("[data-resume]")
            wait_js(page, f"{VIDEO}.currentTime >= 60", 15000)
            check("resume seeks to the saved point", True, True)
        except Exception as exc:
            failures.append(f"case A crashed: {str(exc)[:200]}")

        page.evaluate(f"(() => {{ const v = {VIDEO}; v.pause(); v.textTracks[0].mode = 'showing'; v.currentTime = 5; }})()")
        wait_js(page, f"{VIDEO}.textTracks[0].cues && {VIDEO}.textTracks[0].cues.length > 0", 15000)

        check("subtitle cues loaded", page.evaluate(f"{VIDEO}.textTracks[0].cues.length"), 2)

        page.click("[data-toggle-watched]")
        wait_js(page, "document.querySelector('[data-toggle-watched]').textContent.indexOf('unwatched') >= 0", 10000)

        check("marked watched through the button", api_state("movie", clip)["played"], True)

        page.click("[data-toggle-watched]")
        wait_js(page, "document.querySelector('[data-toggle-watched]').textContent === 'Mark as watched'", 10000)

        context.request.post(f"{BASE}/api/play/movie/{clip}/progress", data={"position_ms": 1500000, "duration_ms": 3000000, "event": "pause"})
    except Exception as exc:
        failures.append(f"case A crashed: {str(exc)[:200]}")

    # Case B: the file the browser can't play
    try:
        page.goto(f"{BASE}/watch/movie/{old}")
        wait_js(page, "!document.querySelector('[data-message]').hidden", 20000)

        check("unplayable message title", page.inner_text("[data-message-title]"), "Your browser can't play this file directly")
        check("try anyway offered", hidden(page, "[data-try-anyway]"), False)
        check("notes mention the container", "avi container" in page.inner_text("[data-notes]"), True)

        page.screenshot(path=os.path.join(WORK, "watch-unplayable.png"))
    except Exception as exc:
        failures.append(f"case B crashed: {str(exc)[:200]}")

    # Case C: next episode
    try:
        page.goto(f"{BASE}/watch/episode/{e1}")
        wait_js(page, f"{VIDEO} && {VIDEO}.readyState >= 1")

        page.evaluate(f"(() => {{ const v = {VIDEO}; v.muted = true; v.currentTime = v.duration - 1; return v.play(); }})()")
        wait_js(page, "!document.querySelector('[data-next-box]').hidden", 20000)

        check("next episode link", page.get_attribute("[data-next-link]", "href").endswith(f"/watch/episode/{e2}"), True)
    except Exception as exc:
        failures.append(f"case C crashed: {str(exc)[:200]}")

    # Case D: pages
    try:
        page.goto(f"{BASE}/")
        check("Continue watching rail links the clip", page.locator(f'a[href="/watch/movie/{clip}"]').count() >= 1, True)
        page.screenshot(path=os.path.join(WORK, "discover.png"), full_page=False)

        page.goto(f"{BASE}/library")
        check("Movies page has a play form", page.locator(f'form[action="/watch/movie/{clip}"]').count() >= 1, True)
        page.screenshot(path=os.path.join(WORK, "library.png"))

        page.goto(f"{BASE}/ui/series/{IDS['series']}")
        check("series page has a play link", page.locator(f'a[href="/watch/episode/{e1}"]').count() >= 1, True)
    except Exception as exc:
        failures.append(f"case D crashed: {str(exc)[:200]}")

    # Final checks
    check("no page errors", errors, [])

    browser.close()

# Summary
print()
if failures:
    print(f"FAILURES ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
else:
    print("All checks passed.")

sys.exit(1 if failures else 0)
