import streamlit as st
import pandas as pd
import hashlib
import os
import requests
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk

# ---------------- Setup ----------------
nltk.download("vader_lexicon")
TMDB_API_KEY = "47ae6fa83619bfd3a777dcb6b45fc695"
BASE_URL = "https://image.tmdb.org/t/p/w200"
MOVIE_URL = "https://www.themoviedb.org/movie/"
USER_FILE = "users.csv"

# TMDb Genre IDs
genre_ids = {
    "Action": 28, "Comedy": 35, "Drama": 18,
    "Horror": 27, "Romance": 10749, "Sci-Fi": 878,
    "Thriller": 53, "Documentary": 99
}

# Mood → genres mapping
mood_to_genres = {
    "Positive": ["Comedy", "Romance", "Action"],
    "Neutral": ["Drama", "Documentary"],
    "Negative": ["Horror", "Thriller"]
}

# ---------------- User Authentication ----------------
def get_hashed_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(USER_FILE):
        return pd.read_csv(USER_FILE)
    return pd.DataFrame(columns=["username", "password"])

def save_user(username, password):
    users = load_users()
    if username in users["username"].values:
        return False
    new_user = pd.DataFrame([[username, get_hashed_password(password)]],
                            columns=["username", "password"])
    users = pd.concat([users, new_user], ignore_index=True)
    users.to_csv(USER_FILE, index=False)
    return True

def login_user(username, password):
    users = load_users()
    if username in users["username"].values:
        stored_pw = users.loc[users["username"] == username, "password"].values[0]
        return stored_pw == get_hashed_password(password)
    return False

# ---------------- Display Movies ----------------
def display_movies(movies):
    if not movies:
        st.warning("No recommendations found.")
        return
    cols = st.columns(5)
    for i, movie in enumerate(movies):
        col = cols[i % 5]
        with col:
            poster_url = BASE_URL + movie.get("poster", "") if movie.get("poster") else None
            movie_link = MOVIE_URL + str(movie.get("id", 0))
            if poster_url:
                st.markdown(
                    f'<a href="{movie_link}" target="_blank">'
                    f'<img src="{poster_url}" style="width:100%; border-radius:10px;"></a>',
                    unsafe_allow_html=True
                )
            else:
                st.write(f"🍿 {movie['title']}")
            title = movie.get("title", "Unknown")
            genre = movie.get("genre", "N/A")
            year = movie.get("release_year", "N/A")
            st.caption(f"**{title}**\n{genre} | {year}")
        if (i + 1) % 5 == 0:
            cols = st.columns(5)

# ---------------- TMDb API Calls ----------------
def get_tmdb_recommendations(genre_name, limit=5):
    genre_id = genre_ids.get(genre_name, 18)
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}&sort_by=popularity.desc&include_adult=false"
    response = requests.get(url)
    movies = []
    if response.status_code == 200:
        results = response.json().get("results", [])
        for m in results[:limit]:
            movies.append({
                "title": m.get("title", "Unknown"),
                "poster": m.get("poster_path"),
                "id": m.get("id", 0),
                "genre": genre_name,
                "release_year": m.get("release_date", "")[:4] if m.get("release_date") else "N/A"
            })
    return movies

def get_trending_movies_by_mood(mood, limit_per_genre=5):
    genres = mood_to_genres[mood]
    url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_API_KEY}&include_adult=false"
    response = requests.get(url)
    movies_to_display = []
    if response.status_code == 200:
        results = response.json().get("results", [])
        for genre_name in genres:
            genre_id = genre_ids.get(genre_name)
            count = 0
            for m in results:
                if genre_id in m.get("genre_ids", []):
                    movies_to_display.append({
                        "title": m.get("title", "Unknown"),
                        "poster": m.get("poster_path"),
                        "id": m.get("id", 0),
                        "genre": genre_name,
                        "release_year": m.get("release_date", "")[:4] if m.get("release_date") else "N/A"
                    })
                    count += 1
                if count >= limit_per_genre:
                    break
    return movies_to_display

# ---------------- Agentic AI Logic ----------------
def agentic_recommendation(username, last_text=None):
    # Determine mood
    mood = "Neutral"
    if last_text:
        analyzer = SentimentIntensityAnalyzer()
        score = analyzer.polarity_scores(last_text)["compound"]
        if score > 0.2:
            mood = "Positive"
        elif score < -0.2:
            mood = "Negative"
    
    # Trending movies
    trending = get_trending_movies_by_mood(mood)
    
    # Genre variety
    genres = mood_to_genres[mood]
    genre_movies = []
    for genre in genres:
        genre_movies += get_tmdb_recommendations(genre, limit=3)
    
    # Remove duplicates
    combined = {m['id']: m for m in trending + genre_movies}.values()
    return list(combined), mood

# ---------------- AI Agent Page ----------------
def ai_agent_page():
    st.subheader("🤖 AI Movie Assistant")
    user_input = st.text_area("Ask about movies or type how you feel:")

    if st.button("Get Recommendations"):
        if user_input.strip():
            movies, mood = agentic_recommendation(st.session_state.username, last_text=user_input)
            st.info(f"Detected Mood: **{mood}**")
            display_movies(movies)
        else:
            st.warning("Please type something!")

# ---------------- Dashboard ----------------
def dashboard(username):
    st.title(f"🎉 Welcome, {username}!")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
    
    menu = ["AI Agent", "Mood Trending"]
    choice = st.sidebar.radio("Navigation", menu)
    
    if choice == "AI Agent":
        ai_agent_page()
    elif choice == "Mood Trending":
        # Default autonomous recommendations
        movies, mood = agentic_recommendation(username)
        st.info(f"Detected Mood: **{mood}**")
        display_movies(movies)

# ---------------- Main App ----------------
def main():
    st.title("🎬 SentiMind - Agentic AI Movie Recommender")
    menu = ["Login", "Signup"]
    choice = st.sidebar.selectbox("Menu", menu)

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""

    if st.session_state.logged_in:
        dashboard(st.session_state.username)
    else:
        if choice == "Login":
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                if login_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
        elif choice == "Signup":
            st.subheader("Signup")
            username = st.text_input("Choose Username")
            password = st.text_input("Choose Password", type="password")
            if st.button("Create Account"):
                if save_user(username, password):
                    st.success("Account created! You can now log in.")
                else:
                    st.error("Username already exists.")

if __name__ == "__main__":
    main()
