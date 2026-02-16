import os
from google import genai
from openai import AsyncOpenAI
from googleapiclient.discovery import build
from dotenv import load_dotenv
from supabase import create_client, Client 

load_dotenv()

# Gemini Setup
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"), http_options={'api_version': 'v1alpha'})

# SiliconFlow & Groq Setup (OpenAI SDK သုံးထားသည်)
sf_client = AsyncOpenAI(
    api_key=os.getenv("SILICONFLOW_API_KEY"), 
    base_url="https://api.siliconflow.com/v1"
)
groq_client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"), 
    base_url="https://api.groq.com/openai/v1"
)

# YouTube API Setup
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube_service = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def get_youtube_videos(query: str):

    # YouTube library က sync ဖြစ်နေလို့ သူ့ကို function သီးသန့်ထုတ်ထားတာပါ

    try:

        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            q=query, part='snippet', 
            type='video', maxResults=3
        )
        response = request.execute()

        return [{"title": v['snippet']['title'], "link": f"https://youtu.be/{v['id']['videoId']}"} for v in response['items']]

    except:

        return []
    
# --- Database Setup (Supabase) ---
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Chat သိမ်းမယ့် Function (Async မလိုပါ, Supabase lib က sync ပေမယ့် thread နဲ့ run မယ်)
def save_chat_to_db(user_id: str, role: str, message: str, agent_type: str):
    try:
        supabase.table("chat_history").insert({
            "user_id": user_id,
            "role": role,
            "message": message,
            "agent_type": agent_type
        }).execute()
    except Exception as e:
        print(f"Error saving to DB: {e}")