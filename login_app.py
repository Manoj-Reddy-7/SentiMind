import streamlit as st
import pandas as pd
import hashlib
import os
import requests
import matplotlib.pyplot as plt
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
import random

# Download NLTK VADER if not already
nltk.download("vader_lexicon")

# ---------------- USER AUTHENTICATION ----------------
USER_FILE = "users.csv"

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

# ---------------- MOVIE RECOMMENDATION ----------------
TMDB_API_KEY = "47ae6fa83619bfd3a777dcb6b45fc695"  # For testing
MOVIES_FILE = "movies.csv"
BASE_URL = "https://image.tmdb.org/t/p/w200"
MOVIE_URL = "https://www.themoviedb.org/movie/"

if os.path.exists(MOVIES_FILE):
    movies_df = pd.read_csv(MOVIES_FILE)
else:
    movies_df = pd.DataFrame(columns=["title", "genre", "mood", "release_year"])

# TMDb Genre IDs
genre_ids = {
    "Action": 28, "Comedy": 35, "Drama": 18,
    "Horror": 27, "Romance": 10749, "Sci-Fi": 878,
    "Thriller": 53, "Documentary": 99
}

# ---------------- DISPLAY MOVIES ----------------
def display_movies(movies):
    if not movies:
        st.warning("No recommendations found.")
        return

    cols = st.columns(5)
    for i, movie in enumerate(movies):
        col = cols[i % 5]
        with col:
            poster_url = BASE_URL + movie["poster"] if movie.get("poster") else None
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

# ---------------- TMDb RECOMMENDATIONS ----------------
def get_tmdb_recommendations(genre_name, limit=5):
    genre_id = genre_ids.get(genre_name, 18)
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}&sort_by=popularity.desc"
    response = requests.get(url)
    if response.status_code == 200:
        results = response.json().get("results", [])
        movies = []
        for m in results[:limit]:
            movies.append({
                "title": m.get("title", "Unknown"),
                "poster": m.get("poster_path"),
                "id": m.get("id", 0),
                "genre": genre_name,
                "release_year": m.get("release_date", "")[:4] if m.get("release_date") else "N/A"
            })
        return movies
    return []

# ---------------- COMBINED MOOD & GENRE RECOMMENDATION ----------------
mood_to_genres = {
    "Positive": ["Comedy", "Romance", "Action"],
    "Neutral": ["Drama", "Documentary"],
    "Negative": ["Horror", "Thriller"]
}

def sentiment_genre_recommendation_page():
    st.subheader("🧠 Mood & Genre Based Recommendations")
    text = st.text_area("Enter text (review, comment, etc.)")

    if st.button("Analyze & Recommend"):
        if text.strip():
            # Sentiment analysis
            analyzer = SentimentIntensityAnalyzer()
            score = analyzer.polarity_scores(text)["compound"]

            if score > 0.2:
                sentiment = "Positive 😀"
                mood = "Positive"
            elif score < -0.2:
                sentiment = "Negative 😞"
                mood = "Negative"
            else:
                sentiment = "Neutral 😐"
                mood = "Neutral"

            st.success(f"Sentiment: **{sentiment}** (score={score:.2f})")

            # Recommend movies for multiple genres based on mood
            genres = mood_to_genres[mood]

            for genre in genres:
                st.markdown(f"### 🎬 {genre} Movies")
                recommended = get_tmdb_recommendations(genre, limit=5)
                display_movies(recommended)

        else:
            st.warning("Please enter some text.")

# ---------------- DASHBOARD ----------------
def dashboard(username):
    st.title(f"🎉 Welcome, {username}!")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    # Only the unified section
    sentiment_genre_recommendation_page()

# ---------------- MAIN APP ----------------
def main():
    st.title("🎬 SentiMind - Mood & Genre Movie Recommendation")
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
            username = st.text_input("Choose a Username")
            password = st.text_input("Choose a Password", type="password")
            if st.button("Create Account"):
                if save_user(username, password):
                    st.success("Account created! You can now log in.")
                else:
                    st.error("Username already exists.")

if __name__ == "__main__":
    main()
