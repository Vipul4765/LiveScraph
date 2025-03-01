# noinspection PyCompatibility
import asyncio
import aiohttp
from lxml import etree


# noinspection PyCompatibility
class MatchScraper:
    def __init__(self):
        self.base_url = 'https://crex.live/fixtures/match-list'
        self.match_list = []

    async def scrape_match(self, match):
        """
        Main match scraping controller.
        Handles different match states.
        """
        print(f"Scraping match: {match}")

    async def fetch_html(self, session, url):
        async with session.get(url) as response:
            return await response.text()

    async def scrape_static_data(self):
        async with aiohttp.ClientSession() as session:
            html = await self.fetch_html(session, self.base_url)
            if html:
                tree = etree.HTML(html)

                # XPath to find match containers under today's date
                matches_xpath = "(//div[@class='date'])[1]/following-sibling::div[contains(@class, 'matches-card-space')]//li[@class='match-card-container']"
                match_elements = tree.xpath(matches_xpath)

                for match in match_elements:
                    team1_name = match.xpath(".//div[@class='team-info'][1]//span[@class='team-name']/text()")
                    team1_score = match.xpath(".//div[@class='team-info'][1]//span[@class='team-score']/text()")

                    team2_name = match.xpath(".//div[@class='team-info'][2]//span[@class='team-name']/text()")
                    team2_score = match.xpath(".//div[@class='team-info'][2]//span[@class='team-score']/text()")

                    match_status = match.xpath(
                        ".//div[@class='result']//span/text() | .//div[@class='live-info']//span/text()"
                    )
                    match_href = match.xpath(".//a[@class='match-card-wrapper']/@href")

                    match_dict = {
                        "team1": team1_name[0] if team1_name else "Unknown",
                        "team1_score": team1_score[0] if team1_score else "Yet to bat",
                        "team2": team2_name[0] if team2_name else "Unknown",
                        "team2_score": team2_score[0] if team2_score else "Yet to bat",
                        "status": match_status[0] if match_status else "Not Started",
                        "link": f"https://crex.live{match_href[0]}" if match_href else "N/A",
                    }

                    self.match_list.append(match_dict)

    async def scrape_live_data(self, href_of_the_match):
        pass

    def extract_scorecard(self, html_content):
        pass

    async def scrape_completed_matches(self):
        for match in self.match_list:
            match_status = match["status"].strip().lower()
            href_of_match = match["link"]
            async with aiohttp.ClientSession() as session:
                html = await self.fetch_html(session, href_of_match)
                if html:
                    if match_status not in ('live', 'rain delay'):
                        self.extract_scorecard(html)
                    elif match_status == 'live':
                        await self.scrape_live_data(href_of_match)


# Create an instance of the class
scraper = MatchScraper()


# Run an async method
# noinspection PyCompatibility
async def main():
    await scraper.scrape_static_data()
    await scraper.scrape_completed_matches()


# Run the event loop
asyncio.run(main())
