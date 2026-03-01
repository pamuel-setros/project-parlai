import os
import requests
from dotenv import load_dotenv

# Load the API key
load_dotenv()
API_KEY = os.environ.get("ODDS_API_KEY")

def get_live_spread(team_name):
    """
    Fetches the live FanDuel spread for the specified NBA team.
    """
    if not API_KEY:
        return "Error: ODDS_API_KEY not found in .env file."

    # The Odds API endpoint for NBA games
    sport = 'basketball_nba'
    regions = 'us'
    markets = 'spreads'
    bookmakers = 'fanduel' # We can specifically target FanDuel

    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
    params = {
        'apiKey': API_KEY,
        'regions': regions,
        'markets': markets,
        'bookmakers': bookmakers,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        games = response.json()

        # Search through today's games for our team
        for game in games:
            if team_name in game['home_team'] or team_name in game['away_team']:
                
                # Check if FanDuel has lines posted for this game
                for bookmaker in game.get('bookmakers', []):
                    if bookmaker['key'] == 'fanduel':
                        for market in bookmaker.get('markets', []):
                            if market['key'] == 'spreads':
                                # Find the specific outcome for our team
                                for outcome in market['outcomes']:
                                    if outcome['name'] == team_name:
                                        spread = outcome.get('point')
                                        return f"Live FanDuel Spread: {team_name} {spread}"
                                        
        return f"No live FanDuel spread found for {team_name} today. They might not be playing."

    except Exception as e:
        return f"Error fetching odds: {e}"

# Quick test block
if __name__ == "__main__":
    # Test with a team playing today
    print(get_live_spread("Cleveland Cavaliers"))