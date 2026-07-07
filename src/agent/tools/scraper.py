"""
Enhanced web scraper with advanced extraction capabilities.
Supports Tavily search, raw content extraction, and metadata enrichment.
"""

import os
import asyncio
import aiohttp
import hashlib
import time
import logging
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from tavily import TavilyClient
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

load_dotenv()

logger = logging.getLogger(__name__)

# SSRF protection: block private/internal IP ranges
_BLOCKED_HOSTS = (
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "169.254.169.254",
    "100.64.0.0",
)
_BLOCKED_PREFIXES = ("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                      "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                      "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                      "172.30.", "172.31.", "192.168.", "169.254.")

_CONTENT_LIMIT = 10000


def _is_safe_url(url: str) -> bool:
    """Reject internal/private URLs to prevent SSRF."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if hostname in _BLOCKED_HOSTS:
            return False
        if any(hostname.startswith(p) for p in _BLOCKED_PREFIXES):
            return False
        if parsed.scheme not in ("http", "https"):
            return False
        return True
    except Exception:
        return False


class AdvancedWebScraper:
    _executor: Optional[ThreadPoolExecutor] = None

    def __init__(self) -> None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError(
                "TAVILY_API_KEY environment variable is not set. "
                "Add it to your .env file."
            )
        self.tavily_client = TavilyClient(api_key=api_key)
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_delay = 0.1
        self.max_retries = 3
        self._semaphore = asyncio.Semaphore(5)

    @classmethod
    def _get_executor(cls) -> ThreadPoolExecutor:
        if cls._executor is None:
            cls._executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="tavily")
        return cls._executor

    async def __aenter__(self) -> "AdvancedWebScraper":
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session:
            await self.session.close()
            self.session = None

    def search_tavily(
        self,
        query: str,
        max_results: int = 35,
        search_depth: str = "advanced",
    ) -> Dict:
        """Search the web using Tavily API (blocking I/O — run in executor)."""
        try:
            response = self.tavily_client.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
                auto_parameters=True,
                timeout=60,
            )

            results = response.get("results", [])

            for idx, result in enumerate(results):
                result["index"] = idx
                result["query"] = query
                result["content_hash"] = hashlib.sha256(
                    result.get("content", "").encode()
                ).hexdigest()
                result["timestamp"] = time.time()

            return {
                "query": query,
                "answer": response.get("answer", ""),
                "results": results,
                "total_results": len(results),
            }
        except Exception as e:
            logger.error("Error in Tavily search for '%s': %s", query, e)
            return {"query": query, "results": [], "answer": "", "total_results": 0}

    async def search_tavily_async(self, query: str, max_results: int = 35) -> Dict:
        """Run Tavily search in thread executor (non-blocking to event loop)."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._get_executor(),
            self.search_tavily,
            query,
            max_results,
        )

    async def fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch and extract clean text content from a webpage."""
        if not _is_safe_url(url):
            logger.warning("Blocked unsafe URL: %s", url)
            return None

        should_close = False
        if self.session is None:
            self.session = aiohttp.ClientSession()
            should_close = True

        try:
            for attempt in range(self.max_retries):
                try:
                    await asyncio.sleep(self.request_delay)
                    timeout = aiohttp.ClientTimeout(total=30)
                    async with self.session.get(url, timeout=timeout) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, "html.parser")

                            for tag in soup(["script", "style", "nav", "footer", "header"]):
                                tag.extract()

                            text = soup.get_text(separator=" ", strip=True)

                            lines = (line.strip() for line in text.splitlines())
                            chunks = (
                                phrase.strip()
                                for line in lines
                                for phrase in line.split("  ")
                            )
                            text = " ".join(chunk for chunk in chunks if chunk)

                            return text[:_CONTENT_LIMIT]
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        logger.warning("Failed to fetch %s: %s", url, e)
                        return None
                    await asyncio.sleep(2**attempt)
        finally:
            if should_close and self.session:
                await self.session.close()
                self.session = None

        return None

    async def batch_search(self, queries: List[str], max_results: int = 35) -> List[Dict]:
        """Execute multiple search queries concurrently with rate limiting."""
        tasks = []
        for idx, query in enumerate(queries):
            logger.info("[%d/%d] Searching: %s", idx + 1, len(queries), query)
            tasks.append(self._bounded_search(query, max_results))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        valid_results = []
        for r in results:
            if isinstance(r, Exception):
                logger.error("Search task failed: %s", r)
            else:
                valid_results.append(r)

        return valid_results

    async def _bounded_search(self, query: str, max_results: int) -> Dict:
        """Run a single search with semaphore rate limiting."""
        async with self._semaphore:
            return await self.search_tavily_async(query, max_results)


def get_raw_web_data(query: str, max_results: int = 35, search_depth: str = "advanced") -> Dict:
    """Legacy function - use AdvancedWebScraper for new code."""
    scraper = AdvancedWebScraper()
    return scraper.search_tavily(query, max_results, search_depth)
