from agent import get_betting_recommendation
from odds import get_live_spread
import streamlit as st
import pandas as pd
from nba_api.stats.static import teams
from transformers import pipeline
from db_connect import get_supabase
from scraper import get_reddit_headlines, TEAM_SUBREDDITS

try:
    from team_logos.logo_fetcher import get_team_logo_url
except ImportError:
    def get_team_logo_url(team_name):
        return None

# --- CONFIG & CACHING ---
st.set_page_config(page_title="ParlAI MVP", layout="wide")

@st.cache_resource
def load_sentiment_pipeline():
    """Loads the heavy NLP model only once. MODEL Distilbert"""
    return pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

@st.cache_data(ttl=60) # Cache for 1 min so we see live database updates
def get_recent_games_from_db(team_name):
    """Queries OUR Supabase database, not the NBA API."""
    supabase = get_supabase()
    
    # Select * from nba_games where team_name = X order by date desc limit 10
    response = supabase.table("nba_games")\
        .select("*")\
        .eq("team_name", team_name)\
        .order("game_date", desc=True)\
        .limit(10)\
        .execute()
        
    # Convert back to DataFrame for Streamlit to display
    data = response.data
    if data:
        return pd.DataFrame(data)
    return pd.DataFrame()

# --- MAIN APP UI ---
st.title("🏀 ParlAI: The Sentiment-Driven Sports Agent")

nba_teams = teams.get_teams()
team_names = [team['full_name'] for team in nba_teams]
selected_team_name = st.sidebar.selectbox("Select a Team", team_names, index=team_names.index("Cleveland Cavaliers"))

# Clear analysis text when switching teams
if st.session_state.get('last_team') != selected_team_name:
    st.session_state['analyzed_text'] = ""
    st.session_state['headlines'] = []
    st.session_state['removed_headlines'] = []
    st.session_state['last_team'] = selected_team_name

# 2. COLUMN 1: HARD DATA (The "Quant" Side)
col1, col2 = st.columns(2)

with col1:
    # Display team logo
    logo_url = get_team_logo_url(selected_team_name)
    if logo_url:
        st.image(logo_url, width=120)
    st.subheader(f"{selected_team_name} Recent Performance")
    
    # Fetch Data
    with st.spinner('Fetching stats from Database...'):
        df = get_recent_games_from_db(selected_team_name)
    
    # CRITICAL CHECK: Did we actually find data?
    if not df.empty:
        # Clean up display and rename columns
        display_df = df[['game_date', 'matchup', 'wl', 'pts', 'plus_minus']].copy()
        display_df.columns = ["Game Date", "Matchup", "W/L", "Points Scored", "Point Difference"]
        st.dataframe(display_df, use_container_width=True)
        
        # Calculate simple momentum
        wins = display_df[display_df["W/L"] == 'W'].shape[0]
        losses = len(display_df) - wins
        st.metric(label="Last 10 Games Record", value=f"{wins}-{losses}")
    else:
        # Graceful failure if data is missing
        st.warning(f"No data found for {selected_team_name}!")
        st.info("💡 Tip: Run 'python nba_dataingest.py' to populate the database.")
        wins = 0 # Default to 0 so the logic below doesn't break 

# 3. COLUMN 2: SOFT DATA (The "Vibes" Side)
with col2:
    st.subheader("🧠 News & Sentiment Analysis")
    # Toggle between Auto-Scrape and Manual Input
    input_method = st.radio("Data Source:", ["Live Reddit Scrape", "Manual Input"], horizontal=True)
    show_analyze_button = False
    show_scraped_content = False
    if input_method == "Live Reddit Scrape":
        if st.button("Pull Subreddit Data"):
            with st.spinner("Scraping Reddit..."):
                raw_headlines = get_reddit_headlines(selected_team_name)
                
            # --- NLP FILTERING PIPELINE ---
            sentiment_pipe = load_sentiment_pipeline()
            filtered_headlines = []
            removed_headlines = []
            removed_count = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, headline in enumerate(raw_headlines):
                # Update Progress
                progress_bar.progress((i + 1) / len(raw_headlines))
                
                # 1. Heuristic Filter: Remove very short "low effort" posts (often trolls)
                if len(headline.split()) < 4:
                    removed_count += 1
                    removed_headlines.append({'text': headline, 'reason': "Too Short (< 4 words)"})
                    continue
                    
                # 2. NLP Filter: Check Confidence
                # We only keep headlines where the model is confident (> 0.75)
                # Trolls/Sarcasm often result in low confidence/ambiguous scores
                result = sentiment_pipe(headline[:512])[0]
                if result['score'] < 0.75:
                    removed_count += 1
                    removed_headlines.append({'text': headline, 'reason': f"Low Confidence ({result['score']:.2f})"})
                    continue
                
                filtered_headlines.append(headline)
            
            status_text.empty()
            progress_bar.empty()
            
            # Update State
            st.session_state['headlines'] = filtered_headlines
            st.session_state['removed_headlines'] = removed_headlines
            st.session_state['analyzed_text'] = " ".join(filtered_headlines)
            st.session_state['subreddit_pulled'] = True
            
            # Show Stats
            st.success(f"Scraped {len(raw_headlines)} posts. Removed {removed_count} low-quality/troll posts using NLP.")
            
        st.session_state.setdefault('subreddit_pulled', False)
        show_analyze_button = st.session_state.get('subreddit_pulled', False)
        show_scraped_content = st.session_state.get('subreddit_pulled', False)
        if show_scraped_content:
            # Use Tabs for a cleaner look
            tab_clean, tab_raw = st.tabs(["✨ Headlines", "📝 Raw Text"])
            
            with tab_clean:
                headlines = st.session_state.get('headlines', [])
                with st.expander(f"✅ View {len(headlines)} Accepted Headlines", expanded=True):
                    for h in headlines:
                        st.markdown(f"- {h}")
                
                # Show the filtered out posts in an expander
                removed_data = st.session_state.get('removed_headlines', [])
                if removed_data:
                    with st.expander(f"🗑️ View {len(removed_data)} Filtered Posts (Algorithm Rejections)"):
                        st.markdown("_**Filtering Logic:** We remove posts that are **Too Short** (< 4 words) or where the AI has **Low Confidence** (< 75%) to avoid sarcasm and noise._")
                        for item in removed_data:
                            st.markdown(f"**{item['reason']}**: _{item['text']}_")
            
            with tab_raw:
                st.text_area("Raw Content", st.session_state.get('analyzed_text', ''), height=150)
    else:
        st.session_state['analyzed_text'] = st.text_area(
            "Enter news headlines, fan sentiment, or any relevant text about the team here...",
        )
        show_analyze_button = True
        show_scraped_content = True
    # The Analysis Button (Runs on whatever text is in the state)
    if show_analyze_button and st.button("Analyze Sentiment"):
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
            # 1. Fetch live odds right before analyzing
            with st.spinner("Fetching live FanDuel spreads..."):
                live_odds = get_live_spread(selected_team_name)
                st.info(f"📈 **Market Data:** {live_odds}")
            # 2. Ask the AI
            with st.spinner("Groq Agent is thinking..."):
                # Notice we pass the DataFrame, the DistilBERT label, and the Odds
                ai_response = get_betting_recommendation(selected_team_name, display_df, label, live_odds)
            # 3. Display the result
            st.write(ai_response)