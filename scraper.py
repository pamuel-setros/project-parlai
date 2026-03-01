import requests

TEAM_SUBREDDITS = {
    "Cleveland Cavaliers": "clevelandcavs",
    "Los Angeles Lakers": "lakers",
    "Golden State Warriors": "warriors",
    "Boston Celtics": "bostonceltics",
    "Milwaukee Bucks": "mkebucks",
    # Teammates can add the rest later
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