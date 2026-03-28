import requests
from langchain_core.tools import tool


FIREFOX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def create_web_tools() -> list:

    @tool
    def open_link(url: str) -> str:
        """Open a URL and return its text content. Use this to fetch web pages."""
        response = requests.get(url, headers=FIREFOX_HEADERS, timeout=15)
        response.raise_for_status()
        return response.text[:50000]

    return [open_link]
