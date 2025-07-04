import random
from supabase import create_client
from faker import Faker

# Initialize Faker for random names
fake = Faker()

# Use your real credentials
SUPABASE_URL = "https://nhyttadsfggjusqlmjfv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5oeXR0YWRzZmdnanVzcWxtamZ2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTYxMzMzNCwiZXhwIjoyMDY3MTg5MzM0fQ.VVyorVOhmkrnfgLxfo7BY7Cr7VAfYrBO1zx6c2ApZ1U"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Set total playlists to create
TOTAL = 100

# Dummy image
dummy_image = "https://via.placeholder.com/300"

for i in range(TOTAL):
    username = fake.user_name()
    playlist_name = f"{fake.word().capitalize()} Beats {random.randint(1, 100)}"
    playlist_url = f"https://open.spotify.com/playlist/fake{i}"
    tracks = random.randint(5, 50)

    data = {
        "username": username,
        "playlist_url": playlist_url,
        "playlist_name": playlist_name,
        "image": dummy_image,
        "tracks": tracks
    }

    response = supabase.table("binksake").insert(data).execute()
    print(f"✅ Inserted playlist {i + 1}: {response.data[0]['playlist_name']}")
