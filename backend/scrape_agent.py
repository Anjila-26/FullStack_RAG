import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, Any
from agent_communication import SimpleAgent
from loguru import logger

class ScrapingAgent(SimpleAgent):
    """Simple web scraping agent"""
    
    def __init__(self):
        super().__init__("scraping_agent")
    
    async def handle_message(self, message):
        """Handle incoming messages"""
        if message["type"] == "scrape_url":
            data = message["data"]
            result = await self.scrape_url(data["url"])
            
            # Store result in shared memory
            self.set_shared_data(f"scrape_result_{data['url']}", result)
            
            # Notify sender
            await self.send_message(
                message["from"], 
                "url_scraped", 
                {"url": data["url"], "success": result["success"]}
            )
    
    async def scrape_url(self, url: str) -> Dict[Any, Any]:
        """Scrape content from a URL"""
        self.set_status("scraping")
        
        # Simple status notification
        await self.send_message("system", "status_update", {
            "agent": self.name,
            "activity": "scraping_url",
            "url": url
        })
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        result = {
                            "success": False,
                            "error": f"Failed to fetch URL. Status code: {response.status}"
                        }
                        self.set_status("idle")
                        return result
                    
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
                    
                    result = {
                        "success": True,
                        "content": text,
                        "metadata": {"source": url}
                    }
                    
                    # Log completion
                    await self.send_message("system", "status_update", {
                        "agent": self.name,
                        "activity": "scraping_completed",
                        "url": url,
                        "content_length": len(text)
                    })
                    
                    self.set_status("idle")
                    return result
                    
        except Exception as e:
            result = {
                "success": False,
                "error": str(e)
            }
            
            # Log error
            await self.send_message("system", "status_update", {
                "agent": self.name,
                "activity": "scraping_error",
                "url": url,
                "error": str(e)
            })
            
            self.set_status("idle")
            return result

# Global instance
scraping_agent = ScrapingAgent()

# Legacy function for compatibility
async def scrape_url(url: str) -> Dict[Any, Any]:
    """Scrape URL using the scraping agent"""
    return await scraping_agent.scrape_url(url)