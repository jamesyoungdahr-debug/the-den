"""Built-in Cloudflare solver: what FlareSolverr / Byparr do, inside The Den.

Both of those are a real Chromium driven by a small Python layer that loads the page,
waits for Cloudflare's "Just a moment..." interstitial to clear, and hands back the HTML.
`nodriver` (the library Byparr is built on) talks to Chromium over its DevTools protocol
without chromedriver, and is hard for the challenge to tell apart from a person's browser.

All The Den needs is a Chromium binary: `chromium` from the distro (the PKGBUILD depends
on it), or CHROME_BIN pointing at one. One browser is kept per process and reused; pages
are closed after each fetch. If nodriver or Chromium is missing, `available()` is False and
the fetch layer falls back to an external FlareSolverr/Byparr URL, or fails with a hint.
"""

import asyncio
import os
import shutil

_CANDIDATES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome", "brave-browser")
_CHALLENGE_TITLES = ("just a moment", "attention required", "verify you are human", "checking your browser")

_browser = None
_lock = asyncio.Lock()


def chrome_path() -> str | None:
    env = os.environ.get("CHROME_BIN", "").strip()
    if env and os.path.exists(env):
        return env
    for name in _CANDIDATES:
        found = shutil.which(name)
        if found:
            return found
    return None


def available() -> bool:
    try:
        import nodriver  # noqa: F401
    except ImportError:
        return False
    return chrome_path() is not None


def status() -> dict:
    try:
        import nodriver
        version = getattr(nodriver, "__version__", "?")
    except ImportError:
        version = None
    return {"builtin": available(), "chrome": chrome_path(), "nodriver": version}


async def _get_browser():
    global _browser
    import nodriver as uc

    if _browser is not None and not getattr(_browser, "stopped", False):
        return _browser
    _browser = await uc.start(
        browser_executable_path=chrome_path(),
        # headless=False on purpose: nodriver 0.46's own headless setup recurses forever
        # (_prepare_headless -> send -> _prepare_headless). Chromium's "new" headless mode
        # via the flag gives a windowless browser that Cloudflare treats like a real one.
        headless=False,
        sandbox=os.geteuid() != 0 if hasattr(os, "geteuid") else True,
        # With a display (a desktop, or Xvfb via the systemd unit) the browser runs headed,
        # which Cloudflare clears far more reliably than any headless mode.
        # DEN_SOLVER_HEADLESS=1 forces the windowless mode anyway (dev boxes with WSLg, where a headed browser pops up on the desktop).
        browser_args=([] if os.environ.get("DISPLAY") and os.environ.get("DEN_SOLVER_HEADLESS", "").lower() not in ("1", "true", "yes") else ["--headless=new"]) + ["--disable-gpu", "--no-first-run", "--window-size=1280,900", "--lang=en-US"],
    )
    return _browser


async def close() -> None:
    global _browser
    if _browser is not None:
        try:
            _browser.stop()
        except Exception:
            pass
        _browser = None


async def _click_turnstile(page) -> bool:
    """Cloudflare's interactive challenge wants a click on the Turnstile checkbox; the
    passive one clears on its own. Try the checkbox by its label, then by element."""
    for finder in (lambda: page.find("Verify you are human", best_match=True, timeout=1),
                   lambda: page.select("input[type=checkbox]", timeout=1)):
        try:
            elem = await finder()
            if elem:
                await elem.mouse_click()
                return True
        except Exception:
            continue
    return False


async def fetch(url: str, timeout: float = 60) -> str:
    """Load `url` in the shared Chromium, wait out a Cloudflare challenge (clicking the
    Turnstile checkbox if one appears), return the HTML. Serialised: one page at a time
    keeps the browser cheap and the challenge cookies stable."""
    async with _lock:
        browser = await _get_browser()
        page = await browser.get(url, new_tab=True)
        try:
            loop = asyncio.get_event_loop()
            deadline = loop.time() + timeout
            tick = 0
            while True:
                await asyncio.sleep(1.0)
                tick += 1
                title = ((await page.evaluate("document.title")) or "").lower()
                html = await page.get_content()
                # "challenge-platform" is deliberately not a marker: Cloudflare injects that
                # script on ordinary pages too, so it would read as "still challenged".
                if not any(t in title for t in _CHALLENGE_TITLES) and "cf_chl_" not in html[:20000]:
                    return html
                if loop.time() > deadline:
                    raise TimeoutError(f"Cloudflare challenge on {url} did not clear within {int(timeout)}s")
                if tick % 3 == 0 and await _click_turnstile(page):
                    await asyncio.sleep(2.0)
        finally:
            try:
                await page.close()
            except Exception:
                pass
