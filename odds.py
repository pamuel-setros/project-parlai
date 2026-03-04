import os
import requests
from dotenv import load_dotenv
from datetime import datetime

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

    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
    params = {
        'apiKey': API_KEY,
        'regions': regions,
        'markets': markets,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        games = response.json()

        # Search through today's games for our team
        for game in games:
            if team_name in game['home_team'] or team_name in game['away_team']:
                
                # Parse the date so we know when the game is
                commence_time = game.get('commence_time', '')
                date_label = ""
                try:
                    # Parse ISO8601 string (e.g. 2023-10-24T23:30:00Z)
                    dt = datetime.strptime(commence_time, "%Y-%m-%dT%H:%M:%SZ")
                    date_label = f" ({dt.strftime('%m/%d')})"
                except Exception:
                    pass
                
                # Check if FanDuel has lines posted for this game
                # LOGIC: Try FanDuel first, but fallback to ANY bookmaker if FanDuel is missing
                target_bookmaker = None
                
                # 1. Try to find FanDuel
                for bookmaker in game.get('bookmakers', []):
                    if bookmaker['key'] == 'fanduel':
                        target_bookmaker = bookmaker
                        break
                
                # 2. Fallback: Take the first available bookmaker if FanDuel isn't there
                if not target_bookmaker and game.get('bookmakers'):
                    target_bookmaker = game['bookmakers'][0]
                
                if target_bookmaker:
                    book_name = target_bookmaker['title']
                    for market in target_bookmaker.get('markets', []):
                        if market['key'] == 'spreads':
                            for outcome in market['outcomes']:
                                if outcome['name'] == team_name:
                                    spread = outcome.get('point')
                                    spread_fmt = f"+{spread}" if spread > 0 else str(spread)
                                    return f"{book_name} Spread{date_label}: {team_name} {spread_fmt}"
                                        
        return f"No upcoming odds found for {team_name}."

    except Exception as e:
        return f"Error fetching odds: {e}"

# Quick test block
if __name__ == "__main__":
    # Test with a team playing today
    print(get_live_spread("Cleveland Cavaliers"))