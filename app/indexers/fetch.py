"""HTTP fetching for native indexers, with a FlareSolverr / Byparr escape hatch.

Public trackers often sit behind Cloudflare's browser check, which a plain HTTP client
cannot pass. FlareSolverr (and Byparr, which speaks the same `/v1` API) runs a real
browser and hands back the page. When Settings -> Indexers has a solver URL, any fetch
that trips a Cloudflare challenge -- or any indexer flagged `cloudflare=True` up front --
goes through it.
"""

import json
import re

import httpx

UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
_CF_MARKERS = ("Just a moment", "cf-browser-verification", "challenge-platform", "_cf_chl_opt", "cf_chl_")
_PRE = re.compile(r"^\s*<html>.*?<pre[^>]*>(.*)</pre>.*</html>\s*$", re.S)


class FetchError(Exception):
    pass


class NeedsSolver(FetchError):
    """The site answered with a Cloudflare challenge and no solver is configured."""


def looks_like_cloudflare(status: int, text: str, headers: httpx.Headers | None = None) -> bool:
    if headers is not None and headers.get("cf-mitigated") == "challenge":
        return True
    return status in (403, 503) and any(m in text for m in _CF_MARKERS)


def _unwrap_pre(text: str) -> str:
    """A browser renders a JSON response as <html><body><pre>...</pre></body></html>; undo that."""
    m = _PRE.match(text)
    return m.group(1) if m else text


class Fetcher:
    """One per search; carries the solver URL and a shared client."""

    def __init__(self, solver_url: str = "", timeout: float = 20):
        self.solver_url = solver_url.strip().rstrip("/")
        self.timeout = timeout

    @property
    def can_solve(self) -> bool:
        if self.solver_url:
            return True
        from app.indexers import solver

        return solver.available()

    async def get_text(self, url: str, params: dict | None = None, *, cloudflare: bool = False, headers: dict | None = None) -> str:
        if cloudflare and self.can_solve:
            return await self.solve(url, params)
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers={**UA, **(headers or {})}) as client:
            resp = await client.get(url, params=params)
        if looks_like_cloudflare(resp.status_code, resp.text, resp.headers):
            if self.can_solve:
                return await self.solve(url, params)
            raise NeedsSolver(f"{httpx.URL(url).host} is behind a Cloudflare check; install Chromium on the server for the built-in solver, or set a FlareSolverr/Byparr URL in Settings → Indexers")
        resp.raise_for_status()
        return resp.text

    async def get_json(self, url: str, params: dict | None = None, *, cloudflare: bool = False):
        return json.loads(_unwrap_pre(await self.get_text(url, params, cloudflare=cloudflare, headers={"Accept": "application/json"})))

    async def post_json(self, url: str, body: dict):
        async with httpx.AsyncClient(timeout=self.timeout, headers=UA) as client:
            resp = await client.post(url, json=body)
        resp.raise_for_status()
        return resp.json()

    async def solve(self, url: str, params: dict | None = None) -> str:
        """The built-in Chromium solver when no external URL is set (app/indexers/solver.py),
        else FlareSolverr / Byparr: POST {solver}/v1 {"cmd": "request.get", "url": ...}."""
        full = str(httpx.URL(url, params=params or {}))
        if not self.solver_url:
            from app.indexers import solver

            return await solver.fetch(full, timeout=max(self.timeout, 60))
        payload = {"cmd": "request.get", "url": full, "maxTimeout": int(max(self.timeout, 30) * 1000)}
        async with httpx.AsyncClient(timeout=self.timeout + 45) as client:
            resp = await client.post(f"{self.solver_url}/v1", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "ok":
            raise FetchError(f"solver: {data.get('message') or data.get('status')}")
        solution = data.get("solution") or {}
        if int(solution.get("status") or 0) >= 400:
            raise FetchError(f"solver fetched {full} but got HTTP {solution.get('status')}")
        return solution.get("response") or ""


async def test_solver(solver_url: str) -> dict:
    """Confirm a FlareSolverr/Byparr instance answers. FlareSolverr's root returns
    {"msg": "FlareSolverr is ready!", "version": ...}; Byparr's root is a docs page and
    its `/health` answers instead. Either way a valid `/v1` sessions.list call proves it."""
    base = solver_url.strip().rstrip("/")
    async with httpx.AsyncClient(timeout=15) as client:
        info = {}
        try:
            root = await client.get(base + "/")
            if root.headers.get("content-type", "").startswith("application/json"):
                info = root.json()
        except httpx.HTTPError:
            pass
        resp = await client.post(base + "/v1", json={"cmd": "sessions.list"})
        resp.raise_for_status()
        data = resp.json()
    if data.get("status") != "ok":
        raise FetchError(data.get("message") or "solver did not answer with status ok")
    return {"ok": True, "solver": info.get("msg") or "ready", "version": info.get("version")}
