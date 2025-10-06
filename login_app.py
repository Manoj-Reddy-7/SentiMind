import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import os
import requests
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
from typing import Dict, List

# ---------------- Setup ----------------
nltk.download("vader_lexicon", quiet=True)
TMDB_API_KEY = "47ae6fa83619bfd3a777dcb6b45fc695"
BASE_URL = "https://image.tmdb.org/t/p/w200"
MOVIE_URL = "https://www.themoviedb.org/movie/"
DB_FILE = "app_data.db"

# Genre IDs
genre_ids = {
    "Action": 28, "Comedy": 35, "Drama": 18, "Horror": 27,
    "Romance": 10749, "Sci-Fi": 878, "Thriller": 53, "Documentary": 99
}

mood_to_genres = {
    "Positive": ["Comedy", "Romance", "Action"],
    "Neutral": ["Drama", "Documentary"],
    "Negative": ["Horror", "Thriller"]
}

# ---------------- Database Setup ----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_logs (
            username TEXT,
            input_text TEXT,
            mood TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_FILE)

# ---------------- Authentication ----------------
def get_hashed_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                       (username, get_hashed_password(password)))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def validate_login(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    record = cursor.fetchone()
    conn.close()
    if record:
        return record[0] == get_hashed_password(password)
    return False

# ---------------- TMDb API ----------------
@st.cache_data(ttl=1800)
def fetch_tmdb_genre_movies(genre_id, limit=10):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}&sort_by=popularity.desc&include_adult=false"
    res = requests.get(url)
    movies = []
    if res.status_code == 200:
        for m in res.json().get("results", [])[:limit]:
            movies.append({
                "title": m.get("title", "Unknown"),
                "poster": m.get("poster_path"),
                "id": m.get("id", 0),
                "release_year": m.get("release_date", "")[:4] if m.get("release_date") else "N/A"
            })
    return movies

@st.cache_data(ttl=1800)
def fetch_trending_movies():
    url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_API_KEY}&include_adult=false"
    res = requests.get(url)
    if res.status_code == 200:
        return res.json().get("results", [])
    return []

# ---------------- Sentiment + Agentic AI ----------------
def analyze_sentiment(text):
    analyzer = SentimentIntensityAnalyzer()
    score = analyzer.polarity_scores(text)["compound"]
    if score > 0.2:
        return "Positive"
    elif score < -0.2:
        return "Negative"
    else:
        return "Neutral"

def agentic_recommendation(username, text=None):
    mood = analyze_sentiment(text) if text else "Neutral"
    genres = mood_to_genres[mood]
    movies_by_genre = {}

    # Save interaction
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_logs (username, input_text, mood) VALUES (?, ?, ?)",
                   (username, text, mood))
    conn.commit()
    conn.close()

    trending = fetch_trending_movies()
    for genre in genres:
        genre_id = genre_ids[genre]
        genre_movies = fetch_tmdb_genre_movies(genre_id)
        filtered_trending = [
            {
                "title": m.get("title", "Unknown"),
                "poster": m.get("poster_path"),
                "id": m.get("id", 0),
                "release_year": m.get("release_date", "")[:4] if m.get("release_date") else "N/A"
            }
            for m in trending if genre_id in m.get("genre_ids", [])
        ][:5]
        combined = {m['id']: m for m in genre_movies + filtered_trending}.values()
        movies_by_genre[genre] = list(combined)
    return movies_by_genre, mood

# ---------------- Display Helpers ----------------
def display_movies(movies):
    cols = st.columns(5)
    for i, movie in enumerate(movies):
        col = cols[i % 5]
        with col:
            poster_url = BASE_URL + movie["poster"] if movie.get("poster") else None
            movie_link = MOVIE_URL + str(movie["id"])
            if poster_url:
                st.markdown(
                    f'<a href="{movie_link}" target="_blank">'
                    f'<img src="{poster_url}" style="width:100%; border-radius:10px;"></a>',
                    unsafe_allow_html=True
                )
            st.caption(f"**{movie['title']}**  \n{movie['release_year']}")
        if (i + 1) % 5 == 0:
            cols = st.columns(5)

def display_movies_by_genre(movies_by_genre):
    for genre, movies in movies_by_genre.items():
        st.markdown(f"### 🎬 {genre} Movies")
        display_movies(movies)

# ---------------- Pages ----------------
def ai_agent_page(username):
    st.subheader("🤖 Agentic AI Movie Assistant")
    user_input = st.text_area("Type how you feel or ask about movies:")
    if st.button("Get Smart Recommendations"):
        if user_input.strip():
            movies_by_genre, mood = agentic_recommendation(username, user_input)
            st.info(f"🧠 Detected Mood: **{mood}**")
            display_movies_by_genre(movies_by_genre)
        else:
            st.warning("Please enter your thoughts!")

def dashboard(username):
    st.title(f"🎉 Welcome, {username}")
    menu = ["AI Agent", "Your History"]
    choice = st.sidebar.radio("Navigation", menu)

    if choice == "AI Agent":
        ai_agent_page(username)
    elif choice == "Your History":
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM user_logs WHERE username = ? ORDER BY timestamp DESC", conn, params=(username,))
        conn.close()
        if not df.empty:
            st.dataframe(df)
        else:
            st.info("No past interactions yet.")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

# ---------------- Main ----------------
def main():
    st.set_page_config(page_title="🎬 SentiMind - AI Movie Recommender", layout="wide")
    init_db()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""

    menu = ["Login", "Signup"]
    choice = st.sidebar.selectbox("Menu", menu)

    if st.session_state.logged_in:
        dashboard(st.session_state.username)
    else:
        if choice == "Login":
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                if validate_login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        elif choice == "Signup":
            st.subheader("Create Account")
            username = st.text_input("Choose Username")
            password = st.text_input("Choose Password", type="password")
            if st.button("Signup"):
                if create_user(username, password):
                    st.success("Account created! Please log in.")
                else:
                    st.error("Username already exists.")

if __name__ == "__main__":
    main()
