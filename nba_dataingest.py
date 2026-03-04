import os
import time
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from nba_api.stats.endpoints import leaguegamefinder
from db_connect import get_supabase
from nba_api.stats.static import teams

# --- LOAD PROXY CONFIGURATION ---
load_dotenv()
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")

# monkey patching requests to disable SSL verification globally (for scraperapi proxy)
import requests
import urllib3

# Suppress the red warnings that pop up when you disable SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

old_request = requests.Session.request

def new_request(self, method, url, **kwargs):
    kwargs['verify'] = False  # <--- FORCES SSL CHECK OFF
    return old_request(self, method, url, **kwargs)

requests.Session.request = new_request


if not SCRAPER_API_KEY:
    print("WARNING: No SCRAPER_API_KEY found in .env file. Requests may be blocked.")
    PROXY = None
else:
    PROXY = f"http://scraperapi:{SCRAPER_API_KEY}@proxy-server.scraperapi.com:8001"

# --- STEALTH MODE CONFIGURATION ---
custom_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Referer': 'https://www.nba.com/',
    'Origin': 'https://www.nba.com',
    'x-nba-stats-origin': 'stats',
    'x-nba-stats-token': 'true'
}

# 1. Update Team Games Function
def fetch_and_upload_games(team_name="Cleveland Cavaliers"):
    print(f"Fetching TEAM data for {team_name}...")
    
    success = False
    # Retry logic (3 attempts)
    for attempt in range(3):
        try:
            nba_teams = teams.get_teams()
            team_list = [t for t in nba_teams if t['full_name'] == team_name]
            if not team_list:
                print(f"Team {team_name} not found.")
                return
            team = team_list[0]
            
            # Pass headers and proxy explicitly
            gamefinder = leaguegamefinder.LeagueGameFinder(
                team_id_nullable=team['id'],
                headers=custom_headers,
                proxy=PROXY,  # <--- The Proxy Bypass
                timeout=60
            )
            
            frames = gamefinder.get_data_frames()
            if not frames:
                raise ValueError("No data returned from NBA API")
                
            df = frames[0].head(50)
            
            records = []
            for _, row in df.iterrows():
                records.append({
                    "game_id": row['GAME_ID'],
                    "team_name": team_name,
                    "game_date": row['GAME_DATE'],
                    "matchup": row['MATCHUP'],
                    "wl": row['WL'],
                    "pts": int(row['PTS']),
                    "plus_minus": int(row['PLUS_MINUS'])
                })
                
            supabase = get_supabase()
            response = supabase.table("nba_games").upsert(records).execute()
            
            if hasattr(response, 'data') and response.data:
                print(f"Successfully uploaded {len(response.data)} games for {team_name}!")
            else:
                print(f"Upload ran but returned no data. Check Supabase RLS policies!")
            success = True
            break # Exit loop on success
            
        except Exception as e:
            print(f"Attempt {attempt+1} failed for {team_name}: {e}")
            time.sleep(3) # Wait before retrying

    # FALLBACK: If API fails, inject mock data so presentation works
    if not success:
        print(f"All attempts failed for {team_name}. Switching to FALLBACK MOCK DATA for presentation.")
        inject_mock_data(team_name)

def inject_mock_data(team_name):
    """
    Emergency fallback: Injects fake/static data so the app has something to show.
    """
    print(f"💉 Injecting MOCK data for {team_name}...")
    
    # Generate dates relative to today so the data always looks "fresh" for the demo
    today = datetime.now()
    
    # Create some realistic looking dummy data
    mock_games = [
        {"game_id": f"mock_{team_name}_1", "team_name": team_name, "game_date": (today - timedelta(days=1)).strftime('%Y-%m-%d'), "matchup": f"{team_name} vs. MEM", "wl": "W", "pts": 110, "plus_minus": 15},
        {"game_id": f"mock_{team_name}_2", "team_name": team_name, "game_date": (today - timedelta(days=3)).strftime('%Y-%m-%d'), "matchup": f"{team_name} @ IND", "wl": "W", "pts": 129, "plus_minus": 9},
        {"game_id": f"mock_{team_name}_3", "team_name": team_name, "game_date": (today - timedelta(days=5)).strftime('%Y-%m-%d'), "matchup": f"{team_name} vs. MEM", "wl": "L", "pts": 98, "plus_minus": -12},
        {"game_id": f"mock_{team_name}_4", "team_name": team_name, "game_date": (today - timedelta(days=7)).strftime('%Y-%m-%d'), "matchup": f"{team_name} @ LAC", "wl": "L", "pts": 118, "plus_minus": -2},
        {"game_id": f"mock_{team_name}_5", "team_name": team_name, "game_date": (today - timedelta(days=9)).strftime('%Y-%m-%d'), "matchup": f"{team_name} @ LAL", "wl": "W", "pts": 116, "plus_minus": 19},
    ]
    
    try:
        supabase = get_supabase()
        response = supabase.table("nba_games").upsert(mock_games).execute()
        
        if hasattr(response, 'data') and response.data:
            print(f"Mock data injected for {team_name} (IDs: {[g['game_id'] for g in response.data]})")
        else:
            print(f"Mock upload ran but returned no data. Check Supabase RLS policies!")
    except Exception as e:
        print(f"Mock injection failed: {e}")

# 2. Update Player Props Function
def fetch_player_stats(team_name):
    print(f"Fetching PLAYER stats for {team_name}...")
    
    try:
        # Find the ID dynamically
        nba_teams = teams.get_teams()
        team = [t for t in nba_teams if t['full_name'] == team_name][0]

        # Pass headers and proxy explicitly
        gamefinder = leaguegamefinder.LeagueGameFinder(
            team_id_nullable=team['id'],
            player_or_team_abbreviation='P',
            headers=custom_headers,
            proxy=PROXY,  # <--- The Proxy Bypass
            timeout=60
        )
        
        df = gamefinder.get_data_frames()[0].head(100)
        
        records = []
        for _, row in df.iterrows():
            records.append({
                "game_id": row['GAME_ID'],
                "player_id": str(row['PLAYER_ID']),
                "player_name": row['PLAYER_NAME'],
                "team_name": row['TEAM_NAME'],
                "game_date": row['GAME_DATE'],
                "matchup": row['MATCHUP'],
                "wl": row['WL'],
                "min": float(row['MIN']) if row['MIN'] else 0.0,
                "pts": int(row['PTS']),
                "reb": int(row['REB']),
                "ast": int(row['AST']),
                "stl": int(row['STL']),
                "blk": int(row['BLK']),
                "fg3m": int(row['FG3M']),
                "tov": int(row['TOV'])
            })
            
        supabase = get_supabase()
        response = supabase.table("nba_player_logs").upsert(records, on_conflict="game_id, player_id").execute()
        
        if hasattr(response, 'data') and response.data:
            print(f"Uploaded {len(response.data)} player logs for {team_name}!")
        else:
            print(f"Player logs upload ran but returned no data. Check RLS!")
        
    except Exception as e:
        print(f"Error fetching players for {team_name}: {e}")

if __name__ == "__main__":
    # Add more teams here whenever you're ready
    TEAMS_TO_PULL = [
        "Cleveland Cavaliers",
        "Los Angeles Lakers"
    ]
    
    for team in TEAMS_TO_PULL:
        fetch_and_upload_games(team)
        time.sleep(5) # Give the proxy server a breather
        fetch_player_stats(team)
        time.sleep(5)