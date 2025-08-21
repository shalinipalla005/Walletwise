import datetime as dt
from typing import Dict, Tuple

import streamlit as st

import db
from auth import hash_password, verify_password


def init_app():
    """Initialize the Streamlit app with proper session state"""
    st.set_page_config(
        page_title="Group Expenses",
        page_icon="👥",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    ensure_session_defaults()

def ensure_session_defaults() -> None:
    """Ensure all required session state variables exist"""
    if "auth" not in st.session_state:
        st.session_state.auth = {
            "user_id": None,
            "name": None,
            "email": None,
            "logged_in": False,
        }
    if "filters" not in st.session_state:
        start, end = get_month_bounds(dt.date.today())
        st.session_state.filters = {
            "start_date": start,
            "end_date": end,
            "category": "All",
            "txn_type": "All",
        }

def get_month_bounds(target_date: dt.date) -> Tuple[dt.date, dt.date]:
    """Get the first and last day of the month for a given date"""
    first_day = target_date.replace(day=1)
    if first_day.month == 12:
        next_month_first = first_day.replace(year=first_day.year + 1, month=1)
    else:
        next_month_first = first_day.replace(month=first_day.month + 1)
    last_day = next_month_first - dt.timedelta(days=1)
    return first_day, last_day

def is_user_logged_in() -> bool:
    """Check if user is currently logged in"""
    return st.session_state.get("auth", {}).get("logged_in", False)

def get_current_user_id() -> int:
    """Get the current user's ID"""
    if not is_user_logged_in():
        return None
    return st.session_state.auth["user_id"]

def get_current_user_name() -> str:
    """Get the current user's name"""
    if not is_user_logged_in():
        return None
    return st.session_state.auth["name"]


def auth_sidebar() -> None:
    with st.sidebar:
        st.title("💸 Walletwise")
        st.caption("Streamlit + SQLite")
        if not st.session_state.auth["logged_in"]:
            tab_login, tab_register = st.tabs(["Login", "Register"])
            with tab_login:
                with st.form("login_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    if st.form_submit_button("Sign In"):
                        user = db.get_user_by_email(email)
                        if not user:
                            st.error("No account found with this email.")
                        elif not verify_password(password, user["password_hash"]):
                            st.error("Incorrect password.")
                        else:
                            st.session_state.auth = {
                                "user_id": user["id"],
                                "name": user["name"],
                                "email": user["email"],
                                "logged_in": True,
                            }
                            st.success("Signed in.")
                            st.rerun()
            with tab_register:
                with st.form("register_form", clear_on_submit=True):
                    name = st.text_input("Full Name")
                    email = st.text_input("Email")
                    pw1 = st.text_input("Password", type="password")
                    pw2 = st.text_input("Confirm Password", type="password")
                    if st.form_submit_button("Create Account"):
                        if not name or not email or not pw1:
                            st.error("All fields are required.")
                        elif pw1 != pw2:
                            st.error("Passwords do not match.")
                        elif db.get_user_by_email(email):
                            st.error("Email already registered.")
                        else:
                            db.create_user(name=name, email=email, password_hash=hash_password(pw1))
                            st.success("Account created. Please log in.")
        else:
            st.subheader(f"Hello, {st.session_state.auth['name']}")
            st.caption(st.session_state.auth["email"])
            if st.button("Sign Out"):
                st.session_state.auth = {"user_id": None, "name": None, "email": None, "logged_in": False}
                st.rerun()


def require_login() -> None:
    if not st.session_state.auth["logged_in"]:
        st.info("Please log in or register from the left sidebar to continue.")
        st.stop()


def render_filters() -> Dict[str, object]:
    with st.sidebar:
        st.markdown("---")
        st.subheader("Filters")
        categories = ["All"] + db.get_distinct_categories(st.session_state.auth["user_id"])
        f = st.session_state.filters
        start = st.date_input("Start", value=f["start_date"])
        end = st.date_input("End", value=f["end_date"])
        cat = st.selectbox("Category", categories, index=categories.index(f["category"]) if f["category"] in categories else 0)
        t = st.selectbox("Type", ["All", "Expense", "Income"], index=["All", "Expense", "Income"].index(f["txn_type"]))
        st.session_state.filters.update({"start_date": start, "end_date": end, "category": cat, "txn_type": t})
        return st.session_state.filters


def show_kpis(total_expense: float, total_income: float) -> None:
    net = total_income - total_expense
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Expense", f"₹ {total_expense:,.2f}")
    c2.metric("Total Income", f"₹ {total_income:,.2f}")
    c3.metric("Net", f"₹ {net:,.2f}")


