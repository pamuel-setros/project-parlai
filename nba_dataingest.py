import os
import time
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
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Referer': 'https://www.nba.com/',
    'Origin': 'https://www.nba.com'
}

# 1. Update Team Games Function
def fetch_and_upload_games(team_name="Cleveland Cavaliers"):
    print(f"Fetching TEAM data for {team_name}...")
    
    try:
        nba_teams = teams.get_teams()
        team = [t for t in nba_teams if t['full_name'] == team_name][0]
        
        # Pass headers and proxy explicitly
        gamefinder = leaguegamefinder.LeagueGameFinder(
            team_id_nullable=team['id'],
            headers=custom_headers,
            proxy=PROXY,  # <--- The Proxy Bypass
            timeout=60
        )
        
        df = gamefinder.get_data_frames()[0].head(50)
        
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
        supabase.table("nba_games").upsert(records).execute()
        print(f"✅ Successfully uploaded {len(records)} games for {team_name}!")
        
    except Exception as e:
        print(f"❌ Error fetching {team_name}: {e}")

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
        supabase.table("nba_player_logs").upsert(records, on_conflict="game_id, player_id").execute()
        print(f"✅ Uploaded {len(records)} player logs for {team_name}!")
        
    except Exception as e:
        print(f"❌ Error fetching players for {team_name}: {e}")

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