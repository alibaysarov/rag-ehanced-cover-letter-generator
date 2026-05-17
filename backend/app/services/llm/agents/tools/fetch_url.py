import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from playwright.async_api import async_playwright
import asyncio

async def parse_hh(url: str):
    """
    Parses hh.ru vacancy page and retrieves text data
    """
    browser = None
    print("parsing with browser")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            html = await page.locator('[data-qa="vacancy-description"]').inner_text()
            
            await browser.close()
            return html

    except Exception as e:
        raise RuntimeError(f"Ошибка при парсинге {url}: {e}") from e
@tool
def fetch_webpage(url: str) -> str:
    """
    Fetches and parses content from a given URL.
    Use this to read job postings, articles, or any web page by its URL.
    
    Args:
        url: The full URL of the webpage to fetch
    
    Returns:
        Cleaned text content of the webpage
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    
    try:
        with httpx.Client(follow_redirects=True, timeout=15) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Убираем мусор
        for tag in soup(["script", "style", "nav", "footer", "header", "ads"]):
            tag.decompose()
        
        # Извлекаем текст
        text = soup.get_text(separator="\n", strip=True)
        
        # Убираем пустые строки
        lines = [line for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)
        
        # Ограничиваем размер (токены)
        return clean_text
    
    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code} fetching {url}"
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"