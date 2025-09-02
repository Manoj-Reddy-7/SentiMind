import streamlit as st
import json
import os
import pandas as pd
import random
import requests
import nltk
import matplotlib.pyplot as plt
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# ==========================
# Setup
# ==========================
USER_DATA_FILE = "users.json"
MOVIES_FILE = "movies.csv"
TMDB_API_KEY = "47ae6fa83619bfd3a777dcb6b45fc695"  # Hardcoded for personal use

# Download VADER lexicon (only once)
nltk.download("vader_lexicon", quiet=True)
sia = SentimentIntensityAnalyzer()


# ==========================
# Helper Functions
# ==========================
def load_users():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(users, f)

def load_movies():
    if os.path.exists(MOVIES_FILE):
        return pd.read_csv(MOVIES_FILE)
    return pd.DataFrame(columns=["title", "genre"])

def fetch_movies_from_tmdb(genre_id):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}&language=en-US&page=1"
    response = requests.get(url)
    if response.status_code == 200:
        return [m["title"] for m in response.json().get("results", [])]
    return ["No movies found"]

# ==========================
# Sentiment Analysis Page
# ==========================
def sentiment_analysis_page():
    st.subheader("📝 Sentiment Analysis")

    user_input = st.text_area("Enter your text here:")

    if st.button("Analyze Sentiment"):
        if user_input.strip() != "":
            score = sia.polarity_scores(user_input)["compound"]

            if score > 0.05:
                st.success(f"Positive 😊 (score: {score:.2f})")
            elif score < -0.05:
                st.error(f"Negative 😡 (score: {score:.2f})")
            else:
                st.info(f"Neutral 😐 (score: {score:.2f})")
        else:
            st.warning("Please enter some text to analyze.")


# ==========================
# Movie Recommendations
# ==========================
def movie_recommendations_page():
    st.subheader("🎬 Movie Recommendations")

    movies_df = load_movies()

    sentiment_score = st.slider("Select your mood score (-1 = Sad, +1 = Happy)", -1.0, 1.0, 0.0, 0.1)

    if st.button("Recommend Movies"):
        if sentiment_score > 0.05:
            mood = "Positive"
            recs = movies_df[movies_df["genre"] == "Comedy"]["title"].tolist()
        elif sentiment_score < -0.05:
            mood = "Negative"
            recs = movies_df[movies_df["genre"] == "Drama"]["title"].tolist()
        else:
            mood = "Neutral"
            recs = movies_df[movies_df["genre"] == "Documentary"]["title"].tolist()

        if recs:
            st.success(f"Based on your {mood} mood, here are some movies:")
            st.write(random.sample(recs, min(5, len(recs))))
        else:
            st.warning("No recommendations found in the dataset.")


# ==========================
# 🎯 New Feature: Movie Review Sentiment Analyzer with Chart
# ==========================
def review_sentiment_recommender():
    st.subheader("🎯 Movie Review Sentiment Analyzer")

    review = st.text_area("Write your movie review here:")

    if st.button("Analyze Review & Recommend"):
        if review.strip() == "":
            st.warning("Please enter a review first.")
            return

        scores = sia.polarity_scores(review)
        compound = scores["compound"]

        # Determine overall mood
        if compound > 0.05:
            st.success(f"Your review is Positive 😊 (score: {compound:.2f})")
            mood = "Positive"
            genre = "Comedy"
        elif compound < -0.05:
            st.error(f"Your review is Negative 😡 (score: {compound:.2f})")
            mood = "Negative"
            genre = "Drama"
        else:
            st.info(f"Your review is Neutral 😐 (score: {compound:.2f})")
            mood = "Neutral"
            genre = "Documentary"

        # 🎨 Bar Chart
        st.write("### Sentiment Breakdown (Bar Chart)")
        fig, ax = plt.subplots()
        ax.bar(scores.keys(), scores.values(), color=["red", "blue", "green", "purple"])
        ax.set_title("Sentiment Breakdown")
        st.pyplot(fig)

        # 🎨 Pie Chart
        st.write("### Sentiment Breakdown (Pie Chart)")
        fig2, ax2 = plt.subplots()
        labels = ["Negative", "Neutral", "Positive"]
        sizes = [scores["neg"], scores["neu"], scores["pos"]]
        ax2.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=["red", "yellow", "green"])
        ax2.axis("equal")  # Equal aspect ratio for circle
        st.pyplot(fig2)

        # Recommend Movies
        movies_df = load_movies()
        recs = movies_df[movies_df["genre"] == genre]["title"].tolist()

        st.write(f"🎬 Since your review was {mood}, you might enjoy these {genre} movies:")
        if recs:
            st.write(random.sample(recs, min(5, len(recs))))
        else:
            st.warning("No matching movies in dataset.")


# ==========================
# Genre Explorer
# ==========================
def genre_explorer_page():
    st.subheader("🎯 Genre Explorer (via TMDb API)")

    genre_dict = {
        "Action": 28,
        "Comedy": 35,
        "Drama": 18,
        "Horror": 27,
        "Romance": 10749,
        "Sci-Fi": 878,
        "Thriller": 53,
    }

    genre_choice = st.selectbox("Choose a genre", list(genre_dict.keys()))

    if st.button("Fetch Movies"):
        movies = fetch_movies_from_tmdb(genre_dict[genre_choice])
        st.write(movies)


# ==========================
# Dashboard Page
# ==========================
def dashboard(username):
    st.title(f"📊 Dashboard - Welcome {username}!")
    st.sidebar.subheader("Navigation")
    choice = st.sidebar.radio(
        "Go to",
        ["Home", "Sentiment Analysis", "Movie Recommendations", "Review Analyzer", "Genre Explorer", "Profile", "Logout"]
    )

    if choice == "Home":
        st.write("This is the home page of your dashboard.")
    elif choice == "Sentiment Analysis":
        sentiment_analysis_page()
    elif choice == "Movie Recommendations":
        movie_recommendations_page()
    elif choice == "Review Analyzer":
        review_sentiment_recommender()
    elif choice == "Genre Explorer":
        genre_explorer_page()
    elif choice == "Profile":
        st.write(f"👤 User Profile for {username} (to be built).")
    elif choice == "Logout":
        st.session_state['logged_in'] = False
        st.rerun()


# ==========================
# Main App
# ==========================
def main():
    st.set_page_config(page_title="Login & Signup", layout="centered")
    st.title("🔐 Welcome to SentiMind")

    if "logged_in" not in st.session_state:
        st.session_state['logged_in'] = False
    if "username" not in st.session_state:
        st.session_state['username'] = ""

    users = load_users()

    if st.session_state['logged_in']:
        dashboard(st.session_state['username'])
    else:
        menu = st.sidebar.selectbox("Select Action", ["Login", "Sign Up"])

        if menu == "Login":
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if st.button("Login"):
                if username in users and users[username] == password:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.success(f"Welcome back, {username}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        elif menu == "Sign Up":
            st.subheader("Create a New Account")
            new_user = st.text_input("Choose a Username")
            new_pass = st.text_input("Choose a Password", type="password")
            confirm_pass = st.text_input("Confirm Password", type="password")

            if st.button("Sign Up"):
                if new_user in users:
                    st.warning("Username already exists. Try another.")
                elif new_pass != confirm_pass:
                    st.warning("Passwords do not match.")
                elif new_user == "" or new_pass == "":
                    st.warning("Fields cannot be empty.")
                else:
                    users[new_user] = new_pass
                    save_users(users)
                    st.success("Signup successful! You can now log in.")


if __name__ == "__main__":
    main()

