import pandas as pd
import plotly.express as px
import streamlit as st

import db
from utils import session as ss


ss.init_app()

# Check if user is logged in - redirect if not
if not st.session_state.get("auth", {}).get("logged_in", False):
    st.error("Please login from the main page to access this feature.")
    st.stop()

# Simple sidebar with user info only
with st.sidebar:
    st.markdown("---")
    st.subheader(f"👋 Hello, {st.session_state.auth['name']}")
    st.caption(f"📧 {st.session_state.auth['email']}")
    
    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.auth = {"user_id": None, "name": None, "email": None, "logged_in": False}
        st.switch_page("streamlit_app.py")

st.title("📈 Reports")

filters = ss.render_filters()
rows = db.list_transactions(
    user_id=st.session_state.auth["user_id"],
    start_date=filters["start_date"],
    end_date=filters["end_date"],
    category=None if filters["category"] == "All" else filters["category"],
    txn_type=None if filters["txn_type"] == "All" else filters["txn_type"],
)
df = pd.DataFrame(rows)
if df.empty:
    st.info("No data available for the selected filters.")
    st.stop()

df["date"] = pd.to_datetime(df["date"]).dt.date
df["amount"] = df["amount"].astype(float)

total_expense = df.loc[df["type"] == "Expense", "amount"].sum()
total_income = df.loc[df["type"] == "Income", "amount"].sum()
ss.show_kpis(total_expense, total_income)

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

st.subheader("Budgets")
ym = filters["start_date"].strftime("%Y-%m")
current_overall = db.get_budget(st.session_state.auth["user_id"], ym, None)
with st.form("budget_form"):
    overall = st.number_input("Overall Monthly Budget (₹)", min_value=0.0, step=500.0, value=float(current_overall or 0.0))
    cat_name = st.text_input("Category (optional)")
    existing_cat = db.get_budget(st.session_state.auth["user_id"], ym, cat_name.strip() or None) if cat_name else None
    cat_budget = st.number_input("Category Budget (₹)", min_value=0.0, step=500.0, value=float(existing_cat or 0.0))
    if st.form_submit_button("Save Budgets"):
        db.set_budget(st.session_state.auth["user_id"], ym, None, overall)
        if cat_name.strip():
            db.set_budget(st.session_state.auth["user_id"], ym, cat_name.strip(), cat_budget)
        st.success("Budget(s) saved.")

st.subheader("Utilization")
if current_overall and current_overall > 0:
    pct = min(100.0, total_expense / current_overall * 100)
    st.progress(pct / 100.0, text=f"Overall: {pct:.1f}% (₹ {total_expense:,.0f} / ₹ {current_overall:,.0f})")
else:
    st.caption("No overall budget set.")

by_cat = df[df["type"] == "Expense"].groupby("category", as_index=False)["amount"].sum()
if not by_cat.empty:
    for _, r in by_cat.iterrows():
        b = db.get_budget(st.session_state.auth["user_id"], ym, r["category"]) or 0.0
        if b > 0:
            p = min(100.0, r["amount"] / b * 100)
            st.progress(p / 100.0, text=f"{r['category']}: {p:.1f}% (₹ {r['amount']:,.0f} / ₹ {b:,.0f})")