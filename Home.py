import datetime as dt
import pandas as pd
import plotly.express as px
import streamlit as st

import db
# from utils import session as ss  # Comment this out temporarily


# Initialize session state manually
if "auth" not in st.session_state:
    st.session_state.auth = {
        "logged_in": False,
        "user_id": None,
        "username": None
    }

st.title("Welcome 👋")
st.caption("A clean, resume-ready Expense Tracker with Streamlit + SQLite")

# Check if user is logged in
if not st.session_state.auth["logged_in"]:
    # Main page authentication instead of sidebar
    st.markdown("---")
    
    # Create tabs for Login and Signup
    login_tab, signup_tab = st.tabs(["🔑 Login", "📝 Sign Up"])
    
    with login_tab:
        st.subheader("Login to Your Account")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_submitted = st.form_submit_button("Login", use_container_width=True)
            
            if login_submitted:
                if username and password:
                    # Simple login check - replace with your actual authentication
                    user = db.authenticate_user(username, password)  # You'll need to implement this
                    if user:
                        st.session_state.auth = {
                            "logged_in": True,
                            "user_id": user["id"],
                            "username": user["username"]
                        }
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.warning("Please enter both username and password")
    
    with signup_tab:
        st.subheader("Create New Account")
        with st.form("signup_form"):
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            signup_submitted = st.form_submit_button("Create Account", use_container_width=True)
            
            if signup_submitted:
                if new_username and new_password and confirm_password:
                    if new_password == confirm_password:
                        # Simple registration - replace with your actual registration
                        success = db.create_user(new_username, new_password)  # You'll need to implement this
                        if success:
                            st.success("Account created successfully! Please login.")
                        else:
                            st.error("Username already exists or registration failed")
                    else:
                        st.error("Passwords do not match")
                else:
                    st.warning("Please fill in all fields")
    
    st.stop()

# If user is logged in, show the main dashboard
st.markdown("---")
st.subheader(f"Welcome back, {st.session_state.auth.get('username', 'User')}!")

# Add logout button
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.auth = {
            "logged_in": False,
            "user_id": None,
            "username": None
        }
        st.rerun()

# Simple filters (replace with your filter logic)
st.markdown("### Filters")
col1, col2, col3, col4 = st.columns(4)
with col1:
    start_date = st.date_input("Start Date", dt.date.today() - dt.timedelta(days=30))
with col2:
    end_date = st.date_input("End Date", dt.date.today())
with col3:
    category = st.selectbox("Category", ["All", "Food", "Transport", "Entertainment", "Bills", "Other"])
with col4:
    txn_type = st.selectbox("Type", ["All", "Income", "Expense"])

filters = {
    "start_date": start_date,
    "end_date": end_date,
    "category": category,
    "txn_type": txn_type
}

rows = db.list_transactions(
    user_id=st.session_state.auth["user_id"],
    start_date=filters["start_date"],
    end_date=filters["end_date"],
    category=None if filters["category"] == "All" else filters["category"],
    txn_type=None if filters["txn_type"] == "All" else filters["txn_type"],
)

df = pd.DataFrame(rows)
if df.empty:
    st.info("No transactions for the selected period.")
else:
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["amount"] = df["amount"].astype(float)
    total_expense = df.loc[df["type"] == "Expense", "amount"].sum()
    total_income = df.loc[df["type"] == "Income", "amount"].sum()
    
    # Show KPIs
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Income", f"${total_income:.2f}")
    with col2:
        st.metric("Total Expenses", f"${total_expense:.2f}")
    with col3:
        st.metric("Net Balance", f"${total_income - total_expense:.2f}")

    left, right = st.columns([2, 1])
    with left:
        daily = df.groupby(["date", "type"], as_index=False)["amount"].sum()
        fig_line = px.line(daily, x="date", y="amount", color="type", markers=True, title="Daily Trend")
        st.plotly_chart(fig_line, use_container_width=True)
    with right:
        cat = df[df["type"] == "Expense"].groupby("category", as_index=False)["amount"].sum()
        if not cat.empty:
            fig_pie = px.pie(cat, names="category", values="amount", hole=0.5, title="Expenses by Category")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No expense data by category.")