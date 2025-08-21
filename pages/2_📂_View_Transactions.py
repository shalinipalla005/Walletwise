import pandas as pd
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

st.title("📂 View Transactions")

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
    st.info("No transactions to display.")
    st.stop()

df["amount"] = df["amount"].astype(float)
st.dataframe(df.sort_values(["date", "id"], ascending=False), use_container_width=True)

st.markdown("---")
st.subheader("Edit / Delete")
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    txn_ids = df["id"].tolist()
    selected_id = st.selectbox("Select Transaction ID", txn_ids)
with col2:
    if st.button("Delete", type="primary"):
        db.delete_transaction(selected_id, st.session_state.auth["user_id"])
        st.warning("Transaction deleted.")
        st.rerun()
with col3:
    open_edit = st.checkbox("Edit")

if open_edit and selected_id:
    row = df[df["id"] == selected_id].iloc[0]
    with st.form("edit_txn_form"):
        e_col1, e_col2, e_col3 = st.columns(3)
        with e_col1:
            e_amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0, value=float(row["amount"]))
            e_type = st.selectbox("Type", ["Expense", "Income"], index=0 if row["type"] == "Expense" else 1)
        with e_col2:
            e_date = st.date_input("Date", value=pd.to_datetime(row["date"]).date())
            e_category = st.text_input("Category", value=row["category"])
        with e_col3:
            e_payment = st.text_input("Payment Method", value=row.get("payment_method") or "")
            e_tags = st.text_input("Tags", value=row.get("tags") or "")
        e_desc = st.text_area("Description", value=row.get("description") or "")
        if st.form_submit_button("Save Changes"):
            db.update_transaction(
                txn_id=int(row["id"]),
                user_id=st.session_state.auth["user_id"],
                amount=float(e_amount),
                description=e_desc.strip(),
                category=e_category.strip() or "Uncategorized",
                date=e_date,
                txn_type=e_type,
                payment_method=e_payment.strip() or None,
                tags=e_tags.strip() or None,
            )
            st.success("Transaction updated.")
            st.rerun()