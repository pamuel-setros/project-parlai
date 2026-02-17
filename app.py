import streamlit as st
import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.static import teams
from transformers import pipeline
import requests # Make sure this is imported at the top

# Map full team names to their subreddit names
TEAM_SUBREDDITS = {
    "Cleveland Cavaliers": "clevelandcavs",
    "Los Angeles Lakers": "lakers",
    "Golden State Warriors": "warriors",
    "Boston Celtics": "bostonceltics",
    "Milwaukee Bucks": "mkebucks",
    # Add more as needed
}

@st.cache_data(ttl=600) # Cache this for 10 minutes to avoid getting banned
def scrape_reddit(team_name):
    """
    Scrapes the top 10 headlines from the team's subreddit.
    Returns a single string of text for the AI to analyze.
    """
    subreddit = TEAM_SUBREDDITS.get(team_name, "nba") # Default to r/nba if unknown
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=10"
    
    # CRITICAL: You must use a custom User-Agent or Reddit will block you (429 Error)
    headers = {'User-Agent': 'ParlAI-Student-Project-v1.0'}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # Parse the JSON structure to get titles
        posts = data['data']['children']
        headlines = [post['data']['title'] for post in posts]
        
        # Join them into one big block of text
        return " ".join(headlines)
        
    except Exception as e:
        return f"Error scraping Reddit: {str(e)}"
# --- CONFIG & CACHING ---
st.set_page_config(page_title="ParlAI MVP", layout="wide")

@st.cache_resource
def load_sentiment_pipeline():
    """Loads the heavy NLP model only once."""
    return pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

@st.cache_data
def get_recent_games(team_id):
    """Pulls the last 10 games for a specific team."""
    gamefinder = leaguegamefinder.LeagueGameFinder(team_id_nullable=team_id)
    games = gamefinder.get_data_frames()[0]
    # Filter for this season (approximate logic for MVP) and sort by date
    games = games.head(10) 
    return games

# --- MAIN APP UI ---
st.title("🏀 ParlAI: The Sentiment-Driven Sports Agent")

# 1. SIDEBAR: TEAM SELECTION
nba_teams = teams.get_teams()
team_names = [team['full_name'] for team in nba_teams]
selected_team_name = st.sidebar.selectbox("Select a Team", team_names, index=team_names.index("Cleveland Cavaliers"))

# Find the ID for the selected team
selected_team_obj = [team for team in nba_teams if team['full_name'] == selected_team_name][0]
team_id = selected_team_obj['id']

# 2. COLUMN 1: HARD DATA (The "Quant" Side)
col1, col2 = st.columns(2)

with col1:
    st.subheader(f"📊 {selected_team_name} Recent Performance")
    
    # Fetch Data
    with st.spinner('Fetching stats from NBA API...'):
        df = get_recent_games(team_id)
    
    # Clean up display
    display_df = df[['GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'PLUS_MINUS']]
    st.dataframe(display_df, use_container_width=True)
    
    # Calculate simple momentum
    wins = display_df[display_df['WL'] == 'W'].shape[0]
    st.metric(label="Last 10 Games Record", value=f"{wins}-10")

# 3. COLUMN 2: SOFT DATA (The "Vibes" Side)
with col2:
    st.subheader("🧠 News & Sentiment Analysis")
    
    # Toggle between Auto-Scrape and Manual Input
    input_method = st.radio("Data Source:", ["Live Reddit Scrape", "Manual Input"], horizontal=True)
    
    if input_method == "Live Reddit Scrape":
        if st.button(f"Pull r/{TEAM_SUBREDDITS.get(selected_team_name, 'nba')} Data"):
            with st.spinner("Scraping Reddit..."):
                scraped_text = scrape_reddit(selected_team_name)
                # Store it in session state so it doesn't disappear on click
                st.session_state['analyzed_text'] = scraped_text
            st.success("Data Pulled!")
            st.text_area("Scraped Content", st.session_state.get('analyzed_text', ''), height=150)
    else:
        st.session_state['analyzed_text'] = st.text_area(
            "Context Source", 
            "Donovan Mitchell looks explosive in practice, ready to return tonight."
        )

    # The Analysis Button (Runs on whatever text is in the state)
    if st.button("Analyze Sentiment"):
        text_to_analyze = st.session_state.get('analyzed_text', "")
        
        if text_to_analyze:
            sentiment_pipe = load_sentiment_pipeline()
            # DistilBERT has a 512 token limit, so we truncate the text safely
            result = sentiment_pipe(text_to_analyze[:512])[0]
            
            label = result['label']
            score = result['score']
            
            if label == 'POSITIVE':
                st.success(f"**Sentiment:** {label} (Confidence: {score:.2f})")
            else:
                st.error(f"**Sentiment:** {label} (Confidence: {score:.2f})")
                
            # --- THE LOGIC GATE ---
            st.divider()
            st.subheader("🤖 Agent Recommendation")
            
            # Simple Heuristic: Wins > 5 AND Positive Sentiment
            if wins >= 5 and label == 'POSITIVE':
                st.write("### ✅ Recommendation: **BET**")
                st.write("_Reasoning: Strong Momentum + Positive Community Sentiment._")
            elif wins < 5 and label == 'NEGATIVE':
                st.write("### ❌ Recommendation: **FADE**")
                st.write("_Reasoning: Poor Form + Negative Vibes._")
            else:
                st.write("### ⚠️ Recommendation: **STAY AWAY**")
                st.write("_Reasoning: Conflicting signals. Data and Sentiment do not agree._")