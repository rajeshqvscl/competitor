"""Shared HTTP client: retries, timeout, rate limiting, robots.txt respect."""
import time
import urllib.robotparser
from urllib.parse import urlparse, urljoin

import httpx

DEFAULT_UA = (
    "DairyCompetitorIngest/0.1 (+internal competitive-intelligence; contact: admin@localhost)"
)
DEFAULT_TIMEOUT = 20.0
DEFAULT_RATE_MS = 1000  # 1 req/sec per host by default


class RateLimiter:
    def __init__(self, rate_ms: int = DEFAULT_RATE_MS):
        self.rate_s = max(rate_ms, 0) / 1000.0
        self._last: dict[str, float] = {}

    def wait(self, host: str) -> None:
        if self.rate_s <= 0:
            return
        now = time.monotonic()
        last = self._last.get(host)
        if last is not None:
            elapsed = now - last
            if elapsed < self.rate_s:
                time.sleep(self.rate_s - elapsed)
        self._last[host] = time.monotonic()


class RobotsCache:
    def __init__(self, user_agent: str = DEFAULT_UA):
        self.user_agent = user_agent
        self._parsers: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def allowed(self, url: str) -> bool:
        origin = "{0.scheme}://{0.netloc}".format(urlparse(url))
        if origin not in self._parsers:
            rp = urllib.robotparser.RobotFileParser()
            try:
                rp.set_url(urljoin(origin, "/robots.txt"))
                rp.read()
                self._parsers[origin] = rp
            except Exception:
                # Fail open if robots.txt unreachable — but log via None sentinel.
                self._parsers[origin] = None
        rp = self._parsers[origin]
        if rp is None:
            return True
        try:
            return rp.can_fetch(self.user_agent, url)
        except Exception:
            return True


class FetchError(Exception):
    pass


class HttpClient:
    def __init__(
        self,
        rate_ms: int = DEFAULT_RATE_MS,
        timeout: float = DEFAULT_TIMEOUT,
        respect_robots: bool = True,
        max_retries: int = 2,
        ssl_fallback: bool = True,
    ):
        self.limiter = RateLimiter(rate_ms)
        self.robots = RobotsCache(DEFAULT_UA)
        self.respect_robots = respect_robots
        self.max_retries = max_retries
        self.ssl_fallback = ssl_fallback
        self._client = httpx.Client(
            headers={"User-Agent": DEFAULT_UA, "Accept": "*/*"},
            timeout=timeout,
            follow_redirects=True,
        )
        self._insecure_client: httpx.Client | None = None

    def close(self) -> None:
        self._client.close()
        if self._insecure_client is not None:
            self._insecure_client.close()

    def _get_insecure(self) -> httpx.Client:
        """Lazily create a verify=False client for sites with broken cert chains."""
        if self._insecure_client is None:
            self._insecure_client = httpx.Client(
                headers={"User-Agent": DEFAULT_UA, "Accept": "*/*"},
                timeout=self._client.timeout,
                follow_redirects=True,
                verify=False,
            )
        return self._insecure_client

    @staticmethod
    def _is_ssl_error(e: Exception) -> bool:
        return "CERTIFICATE" in str(e).upper() or "SSL" in type(e).__name__.upper()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def get(self, url: str) -> httpx.Response:
        if self.respect_robots and not self.robots.allowed(url):
            raise FetchError(f"Blocked by robots.txt: {url}")
        host = urlparse(url).netloc
        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self.limiter.wait(host)
            try:
                resp = self._client.get(url)
                if resp.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                if resp.status_code >= 500:
                    last_err = FetchError(f"HTTP {resp.status_code} for {url}")
                    time.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                return resp
            except httpx.HTTPError as e:
                last_err = e
                # Broken certificate chain? Retry once without verification.
                if self.ssl_fallback and self._is_ssl_error(e):
                    try:
                        resp = self._get_insecure().get(url)
                        resp.raise_for_status()
                        return resp
                    except httpx.HTTPError as e2:
                        last_err = e2
                time.sleep(2 ** attempt)
        raise FetchError(f"GET failed after retries: {url}: {last_err}")

    def get_text(self, url: str) -> str:
        return self.get(url).text

    def get_bytes(self, url: str) -> bytes:
        return self.get(url).content

    def get_json(self, url: str):
        return self.get(url).json()
