import streamlit as st
import pandas as pd
import hashlib
import os
import requests
import matplotlib.pyplot as plt
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
from transformers import pipeline
import random
import google.generativeai as genai

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
TMDB_API_KEY = "47ae6fa83619bfd3a777dcb6b45fc695"
MOVIES_FILE = "movies.csv"

if os.path.exists(MOVIES_FILE):
    movies_df = pd.read_csv(MOVIES_FILE)
else:
    movies_df = pd.DataFrame(columns=["title", "genre"])

def get_genre_and_id_for_movie(movie_title):
    """
    Tries to find a movie's genre and ID locally first.
    If not found, falls back to the TMDB API.
    Returns (genre_id, movie_id_to_exclude) or (None, None).
    """
    # Check local movies.csv first (case-insensitive and stripping whitespace)
    local_movie = movies_df[movies_df['title'].str.strip().str.lower() == movie_title.strip().lower()]
   
    if not local_movie.empty:
        genre_name_to_id = {
            "Action": 28, "Comedy": 35, "Drama": 18, "Horror": 27,
            "Romance": 10749, "Sci-Fi": 878, "Adventure": 12, "Animation": 16,
            "Crime": 80, "Documentary": 99, "Family": 10751, "History": 36,
            "Fantasy": 14, "Music": 10402, "Mystery": 9648, "Thriller": 53,
            "War": 10752, "Western": 37
        }
        genre_name = local_movie.iloc[0]['genre']
        genre_id = genre_name_to_id.get(genre_name, 18)
        st.info("Found movie in local dataset.")
        return genre_id, None

    st.info("Movie not in local dataset, searching online...")
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_title}"
    try:
        response = requests.get(search_url, timeout=10)
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                first_movie = results[0]
                genre_id = first_movie.get("genre_ids", [18])[0]
                movie_id_to_exclude = first_movie["id"]
                return genre_id, movie_id_to_exclude
            else:
                st.error("API Error: The online database returned no results for this movie.")
                return None, None
        else:
            st.error(f"API Error: Received status code {response.status_code} from the movie database.")
            return None, None
    except requests.exceptions.RequestException as e:
        st.error(f"Network Error: Could not connect to the movie database. Details: {e}")
        return None, None

def get_tmdb_recommendations(movie_title, mood):
    opposite_genre_map = {
        28: 35, 12: 10749, 16: 18, 35: 28, 80: 99,
        27: 10751, 10749: 12, 878: 36, 14: 10752, 53: 10749
    }
   
    original_genre_id, movie_id_to_exclude = get_genre_and_id_for_movie(movie_title)

    if original_genre_id is None:
        st.warning(f"Could not find the movie '{movie_title}' locally or online.")
        return []

    if mood == "Negative":
        recommend_genre_id = opposite_genre_map.get(original_genre_id, 35)
        st.info(f"Since you disliked that movie, here are some recommendations from a different genre.")
    else: # For Positive and Neutral
        recommend_genre_id = original_genre_id
        st.info(f"Here are some similar recommendations.")

    discover_url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={recommend_genre_id}&sort_by=popularity.desc"
    try:
        response = requests.get(discover_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            movies = []
            for movie in data.get("results", []):
                if movie_id_to_exclude is None or movie["id"] != movie_id_to_exclude:
                    poster_path = movie.get("poster_path")
                    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
                    movies.append({"title": movie["title"], "poster": poster_url})
                if len(movies) >= 9:
                    break
            return movies
    except requests.exceptions.RequestException:
        st.error("Network error while fetching recommendations.")
    return []

def recommend_movies(movie_title, mood):
    return get_tmdb_recommendations(movie_title, mood)

def get_ai_summary(recommended_titles, mood):
    """
    Uses the Gemini API to generate a personalized recommendation summary.
    """
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
       
        model = genai.GenerativeModel('gemini-1.5-flash')
       
        movie_list_str = ", ".join(f"'{title}'" for title in recommended_titles)
       
        if mood == "Positive":
            prompt = f"A user loved a movie and was recommended the following movies: {movie_list_str}. Write a short, exciting, and friendly paragraph (about 2-3 sentences) explaining why these are great choices for someone who wants more of what they liked. Be creative and engaging."
        else: # For Negative or Neutral moods
            prompt = f"A user disliked a movie and was recommended movies from a different genre: {movie_list_str}. Write a short, friendly, and reassuring paragraph (about 2-3 sentences) suggesting these movies as a refreshing change of pace. Be creative and engaging."
           
        response = model.generate_content(prompt)
       
        st.subheader("🤖 Your AI Recommendation Summary")
        st.write(response.text)
       
    except Exception as e:
        st.warning(f"Could not generate an AI summary. Error: {e}")

# ---------------- AI MODEL LOADING ----------------
@st.cache_resource
def load_sentiment_model():
    model_path = "sentimind_model"
    if not os.path.exists(model_path):
        st.error("Sentiment model files not found. Please ensure the 'sentimind_model' directory is in the correct location.")
        return None
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(model_path, local_files_only=True)
        return pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)
    except Exception as e:
        st.error(f"Error loading sentiment model: {e}")
        return None

sentiment_pipeline = load_sentiment_model()

# ---------------- HELPER: DISPLAY MOVIES IN GRID ----------------
def display_movies_grid(movies, cols=3):
    if not movies:
        return
    rows = [movies[i:i+cols] for i in range(0, len(movies), cols)]
    for row in rows:
        cols_list = st.columns(cols)
        for idx, movie in enumerate(row):
            with cols_list[idx]:
                st.text(movie["title"])
                if movie["poster"]:
                    st.image(movie["poster"], use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/500x750.png?text=No+Poster", use_container_width=True)

# ---------------- STREAMLIT PAGES ----------------
def sentiment_analysis_page():
    st.subheader("📝 Movie Review Analysis")
    movie_title = st.text_input("Enter the movie title you are reviewing")
    text = st.text_area("Enter your review for the movie")
   
    if st.button("Analyze and Recommend"):
        if sentiment_pipeline is None:
            st.error("Sentiment model is not loaded. Cannot perform analysis.")
            return

        if text.strip() and movie_title.strip():
            result = sentiment_pipeline(text)[0]
            label = result["label"]
            score = result["score"]

            if label == "LABEL_2" and score < 0.70:
                sentiment = f"Neutral 😐 (score={score:.2f}, originally Positive)"
                mood = "Neutral"
            elif label == "LABEL_2":
                sentiment = f"Positive 😀 (score={score:.2f})"
                mood = "Positive"
            elif label == "LABEL_0" and score < 0.60:
                sentiment = f"Neutral 😐 (score={score:.2f}, originally Negative)"
                mood = "Neutral"
            elif label == "LABEL_0":
                sentiment = f"Negative 😞 (score={score:.2f})"
                mood = "Negative"
            else:
                sentiment = f"Neutral 😐 (score={score:.2f})"
                mood = "Neutral"

            st.success(f"Sentiment: **{sentiment}**")
            st.subheader("🎬 Recommended Movies")
           
            recommended = recommend_movies(movie_title, mood)
           
            if recommended:
                display_movies_grid(recommended)
                recommended_titles = [movie['title'] for movie in recommended]
                get_ai_summary(recommended_titles, mood)
               
        else:
            st.warning("Please enter both a movie title and a review.")

def movie_recommendations_page():
    st.subheader("🎬 Movie Recommendations (Standalone)")
    movie_title = st.text_input("Enter a movie title to get recommendations")
    mood = st.selectbox("How did you feel about it?", ["Positive", "Negative", "Neutral"])

    if st.button("Get Recommendations"):
        if movie_title.strip():
            recommended = recommend_movies(movie_title, mood)
            if recommended:
                display_movies_grid(recommended)
        else:
            st.warning("Please enter a movie title.")

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
            if results:
                movies = []
                for m in results[:9]:
                    poster_url = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else None
                    movies.append({"title": m["title"], "poster": poster_url})
                display_movies_grid(movies)
            else:
                st.warning("No movies found.")
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
   
    if st.sidebar.button("Clear Cache"):
        st.cache_data.clear()
