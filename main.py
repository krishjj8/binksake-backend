from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
import base64
from supabase import create_client
from fastapi.middleware.cors import CORSMiddleware

# Supabase credentials
SUPABASE_URL = "https://nhyttadsfggjusqlmjfv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5oeXR0YWRzZmdnanVzcWxtamZ2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTYxMzMzNCwiZXhwIjoyMDY3MTg5MzM0fQ.VVyorVOhmkrnfgLxfo7BY7Cr7VAfYrBO1zx6c2ApZ1U"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Spotify credentials
SPOTIFY_CLIENT_ID = "ce8f5f7b5f694663b2b96dbab4445f28"
SPOTIFY_CLIENT_SECRET = "bc1d9dee1eec4455a825f7277f833951"

# FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ MODELS ------------------

class PlaylistSubmission(BaseModel):
    username: str
    playlist_url: str

class UserProfile(BaseModel):
    username: str
    avatar: str = None
    bio: str = None

class Comment(BaseModel):
    playlist_id: str
    username: str
    comment: str

class Subscriber(BaseModel):
    email: str

# ------------------ UTIL ------------------

def get_spotify_token():
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {b64_auth_str}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials"}
    response = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to get Spotify token")
    return response.json().get("access_token")

# ------------------ ROUTES ------------------

@app.post("/submit-playlist")
def submit_playlist(data: PlaylistSubmission):
    username = data.username
    playlist_url = data.playlist_url
    print("📥 Received Submission:", username, playlist_url)

    if "open.spotify.com/playlist" not in playlist_url:
        raise HTTPException(status_code=400, detail="Invalid Spotify URL")

    playlist_id = playlist_url.split("/")[-1].split("?")[0]
    token = get_spotify_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Spotify playlist not found")

    playlist_data = response.json()
    playlist_name = playlist_data.get("name", "Unknown")
    total_tracks = playlist_data["tracks"]["total"]
    image_url = playlist_data["images"][0]["url"] if playlist_data.get("images") else ""

    insert_data = {
        "username": username,
        "playlist_url": playlist_url,
        "playlist_name": playlist_name,
        "image": image_url,
        "tracks": total_tracks
    }

    print("🟢 Inserting into Supabase:", insert_data)
    try:
        result = supabase.table("binksake").insert(insert_data).execute()
        print("✅ Supabase insert result:", result.data)
    except Exception as e:
        print("❌ Supabase error:", e)
        raise HTTPException(status_code=500, detail="Supabase insert failed")

    if not result.data:
        raise HTTPException(status_code=500, detail="Insert returned no data")

    return {"message": "Playlist stored successfully", "playlist": result.data[0]}

@app.get("/leaderboard")
def get_leaderboard():
    try:
        response = supabase.table("binksake").select("username").execute()
        if not response.data:
            return {"leaderboard": []}

        user_counts = {}
        for entry in response.data:
            user = entry.get("username")
            if user:
                user_counts[user] = user_counts.get(user, 0) + 1

        leaderboard = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
        return {"leaderboard": leaderboard}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/vote")
def vote_playlist(playlist_id: str, vote_type: str):
    if vote_type not in ["upvotes", "downvotes"]:
        raise HTTPException(status_code=400, detail="Invalid vote type")
    try:
        supabase.rpc("increment_vote", {"p_id": playlist_id, "column_name": vote_type}).execute()
        return {"message": f"{vote_type} incremented"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/leaderboard/genre/{genre_name}")
def genre_leaderboard(genre_name: str):
    data = supabase.table("binksake").select("*").eq("genre", genre_name).order("upvotes", desc=True).limit(10).execute()
    return {"genre": genre_name, "leaderboard": data.data}

@app.post("/user")
def create_user(profile: UserProfile):
    response = supabase.table("users").insert(profile.dict()).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create user")
    return {"message": "User created", "user": response.data[0]}

@app.post("/comment")
def add_comment(data: Comment):
    response = supabase.table("comments").insert(data.dict()).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to add comment")
    return {"message": "Comment added", "comment": response.data[0]}

@app.get("/comments/{playlist_id}")
def get_comments(playlist_id: str):
    response = supabase.table("comments").select("*").eq("playlist_id", playlist_id).order("created_at", desc=True).execute()
    return {"comments": response.data}

@app.post("/subscribe")
def subscribe_email(sub: Subscriber):
    response = supabase.table("subscribers").insert(sub.dict()).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Subscription failed")
    return {"message": "Subscribed successfully"}

@app.get("/search")
def search_playlists(username: str = None, name: str = None):
    query = supabase.table("binksake").select("*")
    if username:
        query = query.ilike("username", f"%{username}%")
    if name:
        query = query.ilike("playlist_name", f"%{name}%")
    results = query.execute()
    return {"results": results.data}
