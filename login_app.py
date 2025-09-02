import streamlit as st
import json
import os

# File to store user data
USER_DATA_FILE = "users.json"

# Load user data from file
def load_users():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# Save user data to file
def save_users(users):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(users, f)

# Dashboard Page
def dashboard(username):
    st.title(f"📊 Dashboard - Welcome {username}!")
    st.sidebar.subheader("Navigation")
    choice = st.sidebar.radio("Go to", ["Home", "Sentiment Analysis", "Movie Recommendations", "Profile", "Logout"])

    if choice == "Home":
        st.write("This is the home page of your dashboard.")
    elif choice == "Sentiment Analysis":
        st.write("🚀 Here you can analyze text sentiment (to be built).")
    elif choice == "Movie Recommendations":
        st.write("🎬 Here you’ll see mood-based movie recommendations (to be built).")
    elif choice == "Profile":
        st.write(f"👤 User Profile for {username} (to be built).")
    elif choice == "Logout":
        st.session_state['logged_in'] = False
        st.rerun()

# Main App
def main():
    st.set_page_config(page_title="Login & Signup", layout="centered")
    st.title("🔐 Welcome to SentiMind")

    # Initialize session state
    if "logged_in" not in st.session_state:
        st.session_state['logged_in'] = False
    if "username" not in st.session_state:
        st.session_state['username'] = ""

    users = load_users()

    # If user is logged in → show Dashboard
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

from textblob import TextBlob

def sentiment_analysis_page():
    st.subheader("📝 Sentiment Analysis")

    user_input = st.text_area("Enter your text here:")

    if st.button("Analyze Sentiment"):
        if user_input.strip() != "":
            blob = TextBlob(user_input)
            sentiment = blob.sentiment.polarity  # -1 (negative) → +1 (positive)

            if sentiment > 0:
                st.success(f"Positive 😊 (score: {sentiment:.2f})")
            elif sentiment < 0:
                st.error(f"Negative 😡 (score: {sentiment:.2f})")
            else:
                st.info(f"Neutral 😐 (score: {sentiment:.2f})")

        else:
            st.warning("Please enter some text to analyze.")



