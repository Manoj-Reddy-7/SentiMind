import streamlit as st
import json
import os

USER_DATA_FILE = "users.json"

# Load users with fallback to empty dict
def load_users():
    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

# Try saving users (fails silently on Streamlit Cloud)
def save_users(users):
    try:
        with open(USER_DATA_FILE, "w") as f:
            json.dump(users, f)
    except:
        pass

# Main App
def main():
    st.set_page_config(page_title="Login & Signup", layout="centered")
    st.title("🔐 Welcome to My App")

    menu = st.sidebar.selectbox("Select Action", ["Login", "Sign Up"])

    users = load_users()

    if menu == "Login":
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username in users and users[username] == password:
                st.success(f"Welcome back, {username}!")
                st.balloons()
            else:
                st.error("Invalid username or password")

    elif menu == "Sign Up":
        st.subheader("Create a New Account")
        new_user = st.text_input("Choose a Username")
        new_pass = st.text_input("Choose a Password", type="password")
        confirm_pass = st.text_input("Confirm Password", type="password")
        if st.button("Sign Up"):
            if new_user in users:
                st.warning("Username already exists.")
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
