from playwright.sync_api import sync_playwright
import pandas as pd


def scrape_scorecard(url):
    with sync_playwright() as p:
        # Launch browser in headless mode
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Go to the scorecard URL
        page.goto(url)

        # Wait for scorecard content to load (adjust selector based on actual HTML)
        page.wait_for_selector(".scorecard-container", timeout=10000)  # Hypothetical class

        # Extract batting data for both innings (assuming two innings tables)
        innings_1 = page.query_selector(".innings-1")  # Adjust selector
        innings_2 = page.query_selector(".innings-2")  # Adjust selector

        # Parse batting tables (example assumes tables with rows for players)
        batting_1 = parse_batting_table(innings_1)
        batting_2 = parse_batting_table(innings_2)

        # Extract bowling data (similar approach)
        bowling_1 = parse_bowling_table(innings_1)
        bowling_2 = parse_bowling_table(innings_2)

        # Close browser
        browser.close()

        return {
            "Team 1 (SACA)": {"Batting": batting_1, "Bowling": bowling_1},
            "Team 2 (VIC)": {"Batting": batting_2, "Bowling": bowling_2}
        }


def parse_batting_table(innings):
    # Extract rows from batting table
    rows = innings.query_selector_all("tr")  # Adjust based on HTML structure
    batting_data = []
    for row in rows[1:]:  # Skip header row
        cols = row.query_selector_all("td")
        if len(cols) >= 5:  # Name, Runs, Balls, 4s, 6s (example)
            batting_data.append({
                "Player": cols[0].inner_text(),
                "Runs": cols[1].inner_text(),
                "Balls": cols[2].inner_text(),
                "4s": cols[3].inner_text(),
                "6s": cols[4].inner_text()
            })
    return batting_data


def parse_bowling_table(innings):
    # Similar logic for bowling table
    rows = innings.query_selector_all(".bowling-table tr")  # Adjust selector
    bowling_data = []
    for row in rows[1:]:
        cols = row.query_selector_all("td")
        if len(cols) >= 5:  # Name, Overs, Runs, Wickets, Economy
            bowling_data.append({
                "Bowler": cols[0].inner_text(),
                "Overs": cols[1].inner_text(),
                "Runs": cols[2].inner_text(),
                "Wickets": cols[3].inner_text(),
                "Economy": cols[4].inner_text()
            })
    return bowling_data


# Run the scraper
url = "https://crex.live/scoreboard/QI6/1N6/Final/3J/3M/saca-vs-vic-final-australia-domestic-oneday-cup-2024-25/scorecard"
scorecard = scrape_scorecard(url)

# Print or save the result
import json

print(json.dumps(scorecard, indent=2))