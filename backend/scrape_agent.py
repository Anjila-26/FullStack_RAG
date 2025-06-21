import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, Any

async def scrape_url(url: str) -> Dict[Any, Any]:
    """
    Scrape content from a given URL using aiohttp and BeautifulSoup
    Returns the scraped content in markdown format
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return {
                        "success": False,
                        "error": f"Failed to fetch URL. Status code: {response.status}"
                    }
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text content
                text = soup.get_text()
                
                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                return {
                    "success": True,
                    "content": text,
                    "metadata": {"source": url}
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }