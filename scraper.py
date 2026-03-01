import requests

TEAM_SUBREDDITS = {
    "Cleveland Cavaliers": "clevelandcavs",
    "Los Angeles Lakers": "lakers",
    "Golden State Warriors": "warriors",
    "Boston Celtics": "bostonceltics",
    "Milwaukee Bucks": "mkebucks",
    "Atlanta Hawks" : "atlantahawks",
    "Brooklyn Nets": "gonets",
    "Charlotte Hornets": "charlottehornets",
    "Chicago Bulls": "chicagobulls",
    "Detroit Pistons": "detroitpistons",
    "Indiana Pacers": "pacers",
    "Miami Heat": "heat",
    "New York Knicks": "NYKnicks",
    "Orlando Magic": "orlandomagic",
    "Philadelphia 76ers": "sixers",
    "Toronto Raptors": "torontoraptors",
    "Washington Wizards": "washingtonwizards",
    "Dallas Mavericks": "mavericks",
    "Denver Nuggets": "denvernuggets",
    "Houston Rockets": "rockets",
    "Los Angeles Clippers": "laclippers",
    "Memphis Grizzlies": "memphisgrizzlies",
    "Minnesota Timberwolves": "timberwolves",
    "New Orleans Pelicans": "nolapelicans",
    "Oklahoma City Thunder": "thunder",
    "Phoenix Suns": "suns",
    "Portland Trail Blazers": "ripcity",
    "Sacramento Kings": "kings",
    "San Antonio Spurs": "nbaspurs",
    "Utah Jazz": "utahjazz"
}

def get_reddit_headlines(team_name):
    """
    Scrapes the top 10 headlines from the team's subreddit.
    """
    subreddit = TEAM_SUBREDDITS.get(team_name, "nba")
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=10"
    
    headers = {'User-Agent': 'ParlAI-Student-Project-v1.0'}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        posts = data['data']['children']
        headlines = [post['data']['title'] for post in posts]
        
        return " ".join(headlines)
        
    except Exception as e:
        return f"Error scraping Reddit: {str(e)}"