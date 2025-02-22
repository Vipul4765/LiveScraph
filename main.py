# noinspection PyCompatibility
import asyncio
import requests


# noinspection PyCompatibility
class MatchScraper:
    def __init__(self):
        """
        Initialize storage paths and setup rate limiter.
        """
        pass

    # noinspection PyCompatibility
    async def scrape_match(self, session, match):
        """
        Main match scraping controller.
        Handles different match states.
        """
        print(f"Scraping match: {match}")

    async def scrape_static_data(self, session, url):
        """
        Scrape pre-match data.
        """
        print(f"Scraping static data from: {url}")

    async def scrape_live_data(self, session, url):
        """
        Handle real-time updates.
        Implement diff checking.
        """
        print(f"Scraping live data from: {url}")

# Create an instance of the class
scraper = MatchScraper()

# Run an async method
async def main():
    # Here, 'None' is passed as a session just for demonstration.
    await scraper.scrape_match(None, "Match_123")
    await scraper.scrape_static_data(None, "https://example.com/static")
    await scraper.scrape_live_data(None, "https://example.com/live")

# Run the event loop
asyncio.run(main())
