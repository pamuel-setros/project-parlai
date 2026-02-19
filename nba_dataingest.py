import time
import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.library.http import NBAStatsHTTP
from db_connect import get_supabase

# --- STEALTH MODE CONFIGURATION ---
# We must override the default headers to look like a real browser
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
        from nba_api.stats.static import teams
        nba_teams = teams.get_teams()
        team = [t for t in nba_teams if t['full_name'] == team_name][0]
        
        # Pass headers explicitly
        gamefinder = leaguegamefinder.LeagueGameFinder(
            team_id_nullable=team['id'],
            headers=custom_headers,  # <--- The Disguise
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
        print(f"Successfully uploaded {len(records)} games for {team_name}!")
        
    except Exception as e:
        print(f"Error fetching {team_name}: {e}")

# 2. Update Player Props Function
def fetch_player_stats(team_id):
    print(f"Fetching PLAYER stats for Team ID {team_id}...")
    
    try:
        # Pass headers explicitly
        gamefinder = leaguegamefinder.LeagueGameFinder(
            team_id_nullable=team_id,
            player_or_team_abbreviation='P',
            headers=custom_headers,  # <--- The Disguise
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
        print(f"✅ Uploaded {len(records)} player logs!")
        
    except Exception as e:
        print(f"Error fetching players: {e}")

if __name__ == "__main__":
    # 1. Update Team Games
    fetch_and_upload_games("Cleveland Cavaliers")
    time.sleep(5) # Increased sleep to 5s to be safer
    fetch_and_upload_games("Los Angeles Lakers")
    time.sleep(5)
    
    # 2. Update Player Props
    fetch_player_stats("1610612739") # Cavaliers ID
    time.sleep(5)
    fetch_player_stats("1610612747") # Lakers ID