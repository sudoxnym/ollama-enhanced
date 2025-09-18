"""Web search functionality for Ollama integration."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import aiohttp
import requests
from urllib.parse import urlparse, urlunparse

try:
    from bs4 import BeautifulSoup
    HAS_BEAUTIFULSOUP = True
except ImportError:
    HAS_BEAUTIFULSOUP = False
    BeautifulSoup = None

from homeassistant.core import HomeAssistant

from .const import (
    CONF_SEARCH_PROVIDER,
    CONF_SEARCH_RESULTS_COUNT,
    CONF_SEARCH_URL,
    DEFAULT_SEARCH_RESULTS_COUNT,
)

_LOGGER = logging.getLogger(__name__)


class WebSearchClient:
    """Web search client supporting multiple providers."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the web search client."""
        self.hass = hass
        self.provider = config.get(CONF_SEARCH_PROVIDER, "searxng")
        self.base_url = self._normalize_url(config.get(CONF_SEARCH_URL, "http://localhost:8080"))
        self.results_count = int(config.get(CONF_SEARCH_RESULTS_COUNT, DEFAULT_SEARCH_RESULTS_COUNT))

    def _normalize_url(self, url: str) -> str:
        """Normalize URL to ensure it has proper protocol."""
        if not url:
            return "http://localhost:8080"

        # Remove trailing slashes
        url = url.rstrip('/')

        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            # Default to http for local addresses, https for external
            if any(local in url for local in ['localhost', '127.0.0.1', '192.168.', '10.', '172.']):
                url = f"http://{url}"
            else:
                url = f"https://{url}"

        return url

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Perform a web search and return results."""
        try:
            if self.provider == "searxng":
                return await self._search_searxng(query)
            elif self.provider == "duckduckgo":
                return await self._search_duckduckgo(query)
            elif self.provider == "wikipedia":
                return await self._search_wikipedia(query)
            elif self.provider == "google":
                return await self._search_google(query)
            elif self.provider == "bing":
                return await self._search_bing(query)
            elif self.provider == "custom":
                return await self._search_custom(query)
            else:
                _LOGGER.error("Unknown search provider: %s", self.provider)
                return []
        except Exception as e:
            _LOGGER.error("Search failed: %s", e)
            return []

    async def _search_searxng(self, query: str) -> list[dict[str, Any]]:
        """Search SearXNG mirroring OpenWebUI's integration."""
        search_url = self.base_url.rstrip("/")

        # Support legacy URLs that embed the query placeholder
        if "<query>" in search_url:
            search_url = search_url.split("?")[0]

        # Preserve any supplied query string when normalizing the path
        parsed_url = urlparse(search_url)
        path = parsed_url.path or ""

        if not path.endswith("/search"):
            normalized_path = path.rstrip("/")
            if normalized_path:
                normalized_path = f"{normalized_path}/search"
            else:
                normalized_path = "/search"
            parsed_url = parsed_url._replace(path=normalized_path)

        search_url = urlunparse(parsed_url)

        params: dict[str, Any] = {
            "q": query,
            "format": "json",
            "pageno": 1,
            "safesearch": "1",
            "language": "en-US",
            "time_range": "",
            "categories": "",
            "theme": "simple",
            "image_proxy": 0,
        }

        headers = {
            "User-Agent": "Open WebUI (https://github.com/open-webui/open-webui) RAG Bot",
            "Accept": "text/html",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

        _LOGGER.debug("Executing SearXNG search at %s", search_url)

        def _perform_request() -> tuple[int, Any]:
            try:
                response = requests.get(
                    search_url,
                    headers=headers,
                    params=params,
                    timeout=15,
                )
            except requests.RequestException as err:
                raise RuntimeError(f"Request error: {err}") from err

            return response.status_code, response

        try:
            status, response = await self.hass.async_add_executor_job(_perform_request)
        except RuntimeError as err:
            _LOGGER.error("SearXNG request failed: %s", err)
            return []
        except Exception as err:  # pragma: no cover - safety net
            _LOGGER.exception("Unexpected error during SearXNG search: %s", err)
            return []

        if status != 200:
            body_preview = response.text[:500]
            _LOGGER.error(
                "SearXNG search failed with status %s: %s",
                status,
                body_preview,
            )
            return []

        try:
            data = response.json()
        except ValueError:
            html_content = response.text
            _LOGGER.debug("Falling back to HTML parsing for SearXNG response")
            return self._parse_searxng_html(html_content)

        results = data.get("results", []) if isinstance(data, dict) else []
        if not isinstance(results, list):
            _LOGGER.error("SearXNG results field missing or invalid")
            return []

        sorted_results = sorted(
            results,
            key=lambda item: item.get("score", 0) or 0,
            reverse=True,
        )

        limited_results = []
        for item in sorted_results[: int(self.results_count)]:
            content = item.get("content", "") or ""
            snippet = content[:300] + "..." if len(content) > 300 else content
            limited_results.append(
                {
                    "title": item.get("title", "") or "",
                    "url": item.get("url", "") or "",
                    "content": content,
                    "snippet": snippet,
                }
            )

        if not limited_results:
            _LOGGER.debug("SearXNG returned no usable results")

        return limited_results

    def _parse_searxng_html(self, html_content: str) -> list[dict[str, Any]]:
        """Parse search results from SearXNG HTML."""
        if not HAS_BEAUTIFULSOUP:
            _LOGGER.warning("BeautifulSoup not available, using regex parsing fallback")
            return self._parse_searxng_html_regex(html_content)

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []

            # Find all search result articles - try multiple selectors
            articles = soup.find_all('article', class_='result')
            if not articles:
                # Fallback selectors for different SearXNG versions
                articles = soup.find_all('div', class_='result')
                if not articles:
                    articles = soup.select('.result')

            _LOGGER.info(f"Found {len(articles)} article elements")

            # Limit articles to process
            max_articles = int(min(len(articles), self.results_count))
            for i in range(max_articles):
                article = articles[i]
                try:
                    # Extract title and URL
                    title = ""
                    url = ""

                    # Try different title selectors
                    title_elem = article.find('h3')
                    if not title_elem:
                        title_elem = article.find('h2')
                    if not title_elem:
                        title_elem = article.find('a')

                    if title_elem:
                        link_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
                        if link_elem:
                            title = link_elem.get_text(strip=True)
                            url = link_elem.get('href', '')
                        else:
                            title = title_elem.get_text(strip=True)

                    if not title:
                        continue

                    # Extract content/snippet
                    content = ""
                    content_elem = article.find('p', class_='content')
                    if not content_elem:
                        content_elem = article.find('p')
                    if not content_elem:
                        content_elem = article.find('span')

                    if content_elem:
                        content = content_elem.get_text(strip=True)

                    # Create snippet safely
                    if content and len(content) > 300:
                        snippet = content[:300] + "..."
                    else:
                        snippet = content

                    if title:  # Only add if we have at least a title
                        results.append({
                            "title": title,
                            "url": url,
                            "content": content,
                            "snippet": snippet,
                        })

                except Exception as e:
                    _LOGGER.debug(f"Error parsing individual search result {i}: {e}")
                    continue

            _LOGGER.info(f"Successfully parsed {len(results)} results")
            return results

        except Exception as e:
            _LOGGER.error(f"Error parsing SearXNG HTML: {e}")
            import traceback
            _LOGGER.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _parse_searxng_html_regex(self, html_content: str) -> list[dict[str, Any]]:
        """Parse search results from SearXNG HTML using regex as fallback."""
        try:
            results = []

            # Look for result articles or divs
            result_pattern = r'<(?:article|div)[^>]*class="[^"]*result[^"]*"[^>]*>(.*?)</(?:article|div)>'
            result_matches = re.findall(result_pattern, html_content, re.DOTALL | re.IGNORECASE)

            _LOGGER.info(f"Found {len(result_matches)} result blocks with regex")

            count = 0
            for match in result_matches:
                if count >= int(self.results_count):
                    break

                try:
                    # Extract title and URL from h3/h2/a tags
                    title = ""
                    url = ""

                    # Look for title in h3 or h2 with link
                    title_patterns = [
                        r'<h[23][^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>.*?</h[23]>',
                        r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*title[^"]*"[^>]*>([^<]*)</a>',
                        r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
                    ]

                    for pattern in title_patterns:
                        title_match = re.search(pattern, match, re.DOTALL | re.IGNORECASE)
                        if title_match:
                            url = title_match.group(1).strip()
                            title = re.sub(r'<[^>]*>', '', title_match.group(2)).strip()
                            break

                    if not title:
                        continue

                    # Extract content/snippet
                    content = ""
                    content_patterns = [
                        r'<p[^>]*class="[^"]*content[^"]*"[^>]*>([^<]*)</p>',
                        r'<p[^>]*>([^<]*)</p>',
                        r'<span[^>]*>([^<]*)</span>'
                    ]

                    for pattern in content_patterns:
                        content_match = re.search(pattern, match, re.DOTALL | re.IGNORECASE)
                        if content_match:
                            content = re.sub(r'<[^>]*>', '', content_match.group(1)).strip()
                            break

                    # Create snippet safely
                    if content and len(content) > 300:
                        snippet = content[:300] + "..."
                    else:
                        snippet = content

                    results.append({
                        "title": title,
                        "url": url,
                        "content": content,
                        "snippet": snippet,
                    })
                    count += 1

                except Exception as e:
                    _LOGGER.debug(f"Error parsing result with regex: {e}")
                    continue

            _LOGGER.info(f"Successfully parsed {len(results)} results with regex")
            return results

        except Exception as e:
            _LOGGER.error(f"Error parsing SearXNG HTML with regex: {e}")
            return []

    async def _search_duckduckgo(self, query: str) -> list[dict[str, Any]]:
        """Search using DuckDuckGo Instant Answer API."""
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
            "no_redirect": "1",
        }

        headers = {
            "User-Agent": "HomeAssistant/1.0",
            "Accept": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        # Handle both JSON and JSONP responses
                        content_type = response.headers.get('content-type', '')
                        text_response = await response.text()

                        # If it's JSONP (JavaScript), extract the JSON part
                        if 'javascript' in content_type or text_response.strip().startswith('ddg_spice_'):
                            # Extract JSON from JSONP callback
                            import re
                            json_match = re.search(r'ddg_spice_\w+\((.*)\);?$', text_response.strip())
                            if json_match:
                                json_str = json_match.group(1)
                                data = json.loads(json_str)
                            else:
                                _LOGGER.warning("Could not extract JSON from JSONP response")
                                return self._create_fallback_result(query)
                        else:
                            # Regular JSON response
                            data = json.loads(text_response)

                        results = []

                        # Extract results from various DuckDuckGo response fields
                        if data.get("Abstract"):
                            results.append({
                                "title": data.get("Heading", query),
                                "url": data.get("AbstractURL", ""),
                                "content": data.get("Abstract", ""),
                                "snippet": data.get("Abstract", "")[:300] + "..." if len(data.get("Abstract", "")) > 300 else data.get("Abstract", ""),
                            })

                        # Add related topics
                        for topic in data.get("RelatedTopics", [])[:self.results_count-1]:
                            if isinstance(topic, dict) and topic.get("Text"):
                                results.append({
                                    "title": topic.get("Text", "").split(" - ")[0] if " - " in topic.get("Text", "") else topic.get("Text", ""),
                                    "url": topic.get("FirstURL", ""),
                                    "content": topic.get("Text", ""),
                                    "snippet": topic.get("Text", "")[:300] + "..." if len(topic.get("Text", "")) > 300 else topic.get("Text", ""),
                                })

                        # If no results from DDG API, create a synthetic result
                        if not results:
                            return self._create_fallback_result(query)

                        return results[:self.results_count]
                    else:
                        _LOGGER.error("DuckDuckGo search failed with status: %s", response.status)
                        return self._create_fallback_result(query)
        except Exception as e:
            _LOGGER.error("DuckDuckGo search error: %s", e)
            return self._create_fallback_result(query)

    async def _search_wikipedia(self, query: str) -> list[dict[str, Any]]:
        """Search using Wikipedia API."""
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/"

        # First, search for the page
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srlimit": self.results_count,
        }

        headers = {
            "User-Agent": "HomeAssistant/1.0 (https://home-assistant.io/)",
        }

        try:
            async with aiohttp.ClientSession() as session:
                # Search for relevant pages
                async with session.get(search_url, params=search_params, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        search_data = await response.json()
                        results = []

                        for item in search_data.get("query", {}).get("search", [])[:self.results_count]:
                            title = item.get("title", "")
                            snippet = item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")

                            results.append({
                                "title": title,
                                "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                                "content": snippet,
                                "snippet": snippet[:300] + "..." if len(snippet) > 300 else snippet,
                            })

                        if results:
                            return results
                        else:
                            return self._create_fallback_result(query)
                    else:
                        _LOGGER.error("Wikipedia search failed with status: %s", response.status)
                        return self._create_fallback_result(query)
        except Exception as e:
            _LOGGER.error("Wikipedia search error: %s", e)
            return self._create_fallback_result(query)

    async def _search_google(self, query: str) -> list[dict[str, Any]]:
        """Search using Google Custom Search API (requires API key)."""
        # This is a placeholder - requires Google Custom Search API setup
        _LOGGER.warning("Google Custom Search requires API key configuration")
        return []

    async def _search_bing(self, query: str) -> list[dict[str, Any]]:
        """Search using Bing Web Search API (requires API key)."""
        # This is a placeholder - requires Bing Search API setup
        _LOGGER.warning("Bing Search requires API key configuration")
        return []

    async def _search_custom(self, query: str) -> list[dict[str, Any]]:
        """Search using custom provider URL."""
        # Generic implementation for custom search APIs
        url = f"{self.base_url}/search"
        params = {
            "q": query,
            "count": self.results_count,
            "format": "json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []

                    # Try to parse common response formats
                    items = data.get("results", data.get("items", data.get("data", [])))

                    for item in items[:self.results_count]:
                        results.append({
                            "title": item.get("title", item.get("name", "")),
                            "url": item.get("url", item.get("link", "")),
                            "content": item.get("content", item.get("snippet", item.get("description", ""))),
                            "snippet": (item.get("content", item.get("snippet", item.get("description", "")))[:300] + "...")
                                      if len(item.get("content", item.get("snippet", item.get("description", "")))) > 300
                                      else item.get("content", item.get("snippet", item.get("description", ""))),
                        })
                    return results
                else:
                    _LOGGER.error("Custom search failed with status: %s", response.status)
                    return []

    def _create_fallback_result(self, query: str) -> list[dict[str, Any]]:
        """Create a fallback result when search APIs fail."""
        return [{
            "title": f"Web search attempted for: {query}",
            "url": "",
            "content": f"I attempted to search for '{query}' but the search APIs are currently unavailable. I can still help with general knowledge about this topic based on my training data.",
            "snippet": f"Search attempted for: {query} (APIs unavailable)",
        }]


def format_search_results(results: list[dict[str, Any]]) -> str:
    """Format search results for inclusion in the conversation."""
    if not results:
        return "No search results found."

    formatted = ["Here are some relevant search results:\n"]

    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        snippet = result.get("snippet", "No description available.")

        formatted.append(f"{i}. **{title}**")
        if url:
            formatted.append(f"   URL: {url}")
        formatted.append(f"   {snippet}\n")

    return "\n".join(formatted)


def should_trigger_search(message: str) -> bool:
    """Determine if a message should trigger a web search."""
    search_triggers = [
        "search for",
        "look up",
        "find information about",
        "what is",
        "what are",
        "tell me about",
        "latest news",
        "current events",
        "recent",
        "news",
        "updates",
        "today",
        "this week",
        "this month",
        "this year",
        "2024",
        "2025",
        "latest",
        "current",
        "new",
        "happening",
    ]

    message_lower = message.lower()
    triggered = any(trigger in message_lower for trigger in search_triggers)

    # Log for debugging
    import logging
    _LOGGER = logging.getLogger(__name__)
    _LOGGER.info(f"Search trigger check for '{message}': {triggered}")

    return triggered
