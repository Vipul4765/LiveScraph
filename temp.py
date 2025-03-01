

import requests
from bs4 import BeautifulSoup
import json

class CricketScorecard:
    def __init__(self, url):
        """Initialize with the scorecard URL and fetch data."""
        self.url = url
        self.data = self._fetch_and_parse_data()
        self.team1_data = None
        self.team2_data = None
        if self.data:
            self._assign_team_data()

    def _fetch_and_parse_data(self):
        """Fetch HTML content and parse the JSON data."""
        response = requests.get(self.url)
        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")
        script_tag = soup.find("script", id="app-root-state")

        if not script_tag:
            print("Could not find app-root-state script tag.")
            return None

        json_str = script_tag.string.strip().replace('&q;', '"')
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return None

    def _assign_team_data(self):
        """Assign team data based on team IDs."""
        scorecard_data = self.data.get("https://api-v1.com/w/sC4.php", [])
        if not scorecard_data or len(scorecard_data) < 2:
            print("Scorecard data not found or incomplete.")
            return

        self.team1_data = next((item for item in scorecard_data if item["c"] == "122"), None)  # Hornchurch
        self.team2_data = next((item for item in scorecard_data if item["c"] == "123"), None)  # Byron

        if not self.team1_data or not self.team2_data:
            print("Could not find data for both teams.")

    def get_player_name(self, player_id):
        """Get player name from player ID."""
        players = self.data.get("https://oc.crickapi.com/mapping/getHomeMapData", {}).get("p", [])
        player = next((p for p in players if p["f_key"] == player_id), None)
        return player["n"] if player else f"Player {player_id}"

    def format_total(self, total_str):
        """Format the total score with overs instead of balls."""
        # Clean the string (e.g., "189/2(60" -> remove any trailing quote)
        total_str = total_str.strip()
        if total_str.endswith('"'):
            total_str = total_str[:-1]

        # Split by "(" to separate score and balls
        parts = total_str.split("(")
        if len(parts) == 2:
            score = parts[0].strip()  # e.g., "189/2"
            balls_str = parts[1].replace(")", "").strip()  # e.g., "60"
            try:
                balls = int(balls_str)
                overs = balls // 6
                remainder = balls % 6
                overs_str = f"{overs}.{remainder}"
                return f"{score} ({overs_str})"
            except ValueError:
                return total_str  # Return original if parsing fails
        return total_str

    def print_batting_stats(self, team_name, batting_data):
        """Print batting statistics, including yet-to-bat players."""
        print(f"\n{team_name} Batting Scorecard:")
        print("Player Name            | Runs | Balls | 4s | 6s | SR")
        print("-" * 60)

        yet_to_bat = []
        for player in batting_data:
            stats = player.split(".")
            if len(stats) >= 5:
                # Batted player
                player_id, runs, balls, fours, sixes = stats[:5]
                player_name = self.get_player_name(player_id)
                strike_rate = f"{(int(runs) / int(balls) * 100):.2f}" if int(balls) > 0 else "0.00"
                print(f"{player_name:<22} | {runs:<4} | {balls:<5} | {fours:<2} | {sixes:<2} | {strike_rate}")
            elif len(stats) == 2 and stats[1] == "-":
                # Yet-to-bat player
                player_id = stats[0]
                player_name = self.get_player_name(player_id)
                yet_to_bat.append(player_name)

        if yet_to_bat:
            print("\nYet to Bat: " + ", ".join(yet_to_bat))

    def print_bowling_stats(self, team_name, bowling_data):
        """Print bowling statistics for a team."""
        print(f"\n{team_name} Bowling Scorecard:")
        print("Player Name            | Overs | Maidens | Runs | Wickets | ER")
        print("-" * 60)
        for player in bowling_data:
            stats = player.split(".")
            if len(stats) >= 5:
                player_id, runs, balls, maidens, wickets = stats[:5]
                overs = f"{int(balls) // 6}.{int(balls) % 6}"
                player_name = self.get_player_name(player_id)
                economy_rate = f"{(int(runs) / (int(balls) / 6)):.2f}" if int(balls) > 0 else "0.00"
                print(f"{player_name:<22} | {overs:<5} | {maidens:<7} | {runs:<4} | {wickets:<7} | {economy_rate}")

    def display_scorecard(self):
        """Display the full scorecard for both teams."""
        if not self.team1_data or not self.team2_data:
            print("Cannot display scorecard due to missing team data.")
            return

        # Hornchurch Scorecard
        print(f"\nHornchurch (HOR) Total: {self.format_total(self.team1_data['d'])}")
        self.print_batting_stats("Hornchurch (HOR)", self.team1_data["b"])
        self.print_bowling_stats("Hornchurch (HOR)", self.team1_data["a"])

        # Byron Scorecard
        print(f"\nByron (BYR) Total: {self.format_total(self.team2_data['d'])}")
        self.print_batting_stats("Byron (BYR)", self.team2_data["b"])
        self.print_bowling_stats("Byron (BYR)", self.team2_data["a"])

# Usage
if __name__ == "__main__":
    url = "https://crex.live/scoreboard/T7A/1R4/16th-Match/122/123/byr-vs-hor-16th-match-european-cricketleague-2025/scorecard"
    scorecard = CricketScorecard(url)
    scorecard.display_scorecard()