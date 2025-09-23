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
TMDB_API_KEY = "47ae6fa83619bfd3a777dcb6b45fc695"  # Hardcoded for personal use
MOVIES_FILE = "movies.csv"
BASE_URL = "https://image.tmdb.org/t/p/w200"
MOVIE_URL = "https://www.themoviedb.org/movie/"

if os.path.exists(MOVIES_FILE):
    movies_df = pd.read_csv(MOVIES_FILE)
else:
    movies_df = pd.DataFrame(columns=["title", "genre", "mood"])

def display_movies(movies):
    if not movies:
        st.warning("No recommendations found.")
        return

    # Grid of 5 columns
    cols = st.columns(5)
    for i, movie in enumerate(movies):
        col = cols[i % 5]
        with col:
            if movie.get("poster"):
                url = MOVIE_URL + str(movie["id"])
                # clickable poster with markdown
                st.markdown(
                    f'<a href="{url}" target="_blank">'
                    f'<img src="{BASE_URL + movie["poster"]}" '
                    f'style="width:100%; border-radius:10px;"></a>',
                    unsafe_allow_html=True
                )
                st.caption(movie["title"])
            else:
                st.write(f"🍿 {movie['title']}")
        if (i + 1) % 5 == 0 and i != len(movies) - 1:
            cols = st.columns(5)

def get_tmdb_recommendations(mood):
    mood_to_genre = {
        "Positive": 35,   # Comedy
        "Negative": 27,   # Horror
        "Neutral": 18     # Drama
    }
    genre_id = mood_to_genre.get(mood, 18)
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}&sort_by=popularity.desc"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return [{"title": m["title"], "poster": m.get("poster_path"), "id": m["id"]}
                for m in data.get("results", [])[:20]]
    return []

def recommend_movies(mood):
    local_movies = movies_df[movies_df["mood"].str.lower() == mood.lower()]
    if not local_movies.empty:
        sampled = random.sample(local_movies["title"].tolist(), min(20, len(local_movies)))
        return [{"title": title, "poster": None, "id": 0} for title in sampled]
    else:
        return get_tmdb_recommendations(mood)

# ---------------- STREAMLIT PAGES ----------------
def sentiment_analysis_page():
    st.subheader("📝 Sentiment Analysis")
    text = st.text_area("Enter text (review, comment, etc.)")
    if st.button("Analyze"):
        if text.strip():
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

            st.success(f"Sentiment: **{sentiment}** (score={score})")

            st.subheader("🎬 Recommended Movies")
            recommended = recommend_movies(mood)
            display_movies(recommended)
        else:
            st.warning("Please enter some text.")

def movie_recommendations_page():
    st.subheader("🎬 Movie Recommendations (Standalone)")
    mood = st.selectbox("Select mood", ["Positive", "Negative", "Neutral"])
    if st.button("Get Recommendations"):
        recommended = recommend_movies(mood)
        display_movies(recommended)

def genre_explorer_page():
    st.subheader("🎭 Explore by Genre")
    genres = {
        "Action": 28, "Comedy": 35, "Drama": 18,
        "Horror": 27, "Romance": 10749, "Sci-Fi": 878
    }
    choice = st.selectbox("Pick a genre", list(genres.keys()))
    if st.button("Show Movies"):
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genres[choice]}&sort_by=popularity.desc"
        response = requests.get(url)
        if response.status_code == 200:
            results = response.json().get("results", [])
            movies = [{"title": m["title"], "poster": m.get("poster_path"), "id": m["id"]}
                      for m in results[:20]]
            display_movies(movies)
        else:
            st.error("Error fetching data from TMDb.")

def sentiment_trends_page():
    st.subheader("📊 Sentiment Trends (Demo Data)")
    demo_texts = [
        "I love this movie!", "It was okay, not bad.",
        "Worst film ever.", "Amazing experience!",
        "Pretty boring."
    ]
    analyzer = SentimentIntensityAnalyzer()
    scores = [analyzer.polarity_scores(t)["compound"] for t in demo_texts]

    fig, ax = plt.subplots()
    ax.plot(range(len(scores)), scores, marker="o")
    ax.axhline(0, color="gray", linestyle="--")
    ax.set_title("Sentiment Trend (Sample Data)")
    ax.set_xlabel("Sample Index")
    ax.set_ylabel("Sentiment Score")
    st.pyplot(fig)

def dashboard(username):
    st.title(f"🎉 Welcome, {username}!")
    menu = ["Sentiment Analysis", "Movie Recommendations",
            "Genre Explorer", "Sentiment Trends"]
    choice = st.sidebar.radio("Navigation", menu)

    if choice == "Sentiment Analysis":
        sentiment_analysis_page()
    elif choice == "Movie Recommendations":
        movie_recommendations_page()
    elif choice == "Genre Explorer":
        genre_explorer_page()
    elif choice == "Sentiment Trends":
        sentiment_trends_page()

# ---------------- MAIN APP ----------------
def main():
    st.title("🎬 SentiMind - Movie Recommendation System")
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
