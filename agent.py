import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Try to import Groq safely
try:
    from groq import Groq
except ImportError:
    Groq = None

# Initialize the Groq Client
api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if (api_key and Groq) else None

def get_betting_recommendation(team_name, stats_df, sentiment_label, live_odds):
    """
    Sends the data, context, and odds to Groq (Llama 3) to get a betting recommendation.
    """
    
    if not client:
        return "Error: Groq client not initialized. Check API Key or run 'pip install groq'."

    # 1. Format the Data into a string the LLM can read
    stats_string = stats_df.to_string(index=False)
    
    # 2. Build the Prompt (Retrieval-Augmented Generation)
    prompt = f"""
    You are an expert NBA sports betting analyst.
    
    TEAM TO ANALYZE: {team_name}
    
    LIVE FANDUEL ODDS: 
    {live_odds}
    
    RECENT PERFORMANCE (Last 10 Games):
    {stats_string}
    
    LATEST NEWS SENTIMENT: 
    {sentiment_label}
    
    TASK:
    Based strictly on the stats, the sentiment, and the live spread provided above, should I bet on this team tonight? 
    Give me a single recommendation (BET, FADE, or STAY AWAY) followed by a strict 3-sentence explanation of your reasoning.
    """

    # 3. Call the API
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a direct, concise sports analyst."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile", # This model is incredibly fast and smart enough for this task
            temperature=0.7 
        )
        
        # 4. Return the text
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        return f"Agent Error: {str(e)}"