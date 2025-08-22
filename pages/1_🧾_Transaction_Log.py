import datetime as dt
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

st.title("🧾 Log Transactions")

# Current balance across all time
all_rows = db.list_transactions(
    user_id=st.session_state.auth["user_id"],
    start_date=dt.date(1970, 1, 1),
    end_date=dt.date.today(),
)

# Calculate balance with special handling for salary
balance = 0
for r in all_rows:
    if r["type"] == "Income":
        # Add all income (including salary)
        balance += r["amount"]
    elif r["type"] == "Expense":
        # Subtract all expenses
        balance -= r["amount"]

st.caption(f"Current Balance: ₹{balance:,.2f}")

# Initialize session state for form visibility
if 'show_expense_success' not in st.session_state:
    st.session_state.show_expense_success = False
if 'show_income_success' not in st.session_state:
    st.session_state.show_income_success = False

# Show success messages at the top level
if st.session_state.show_expense_success:
    st.success("Expense added successfully!")
    st.session_state.show_expense_success = False

if st.session_state.show_income_success:
    st.success("Income added successfully!")
    st.session_state.show_income_success = False

with st.expander("Add New Expense", expanded=True):
    with st.form("add_expense"):
        c1, c2, c3 = st.columns(3)
        with c1:
            amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0, format="%0.2f")
        with c2:
            date_val = st.date_input("Date", value=dt.date.today())
        with c3:
            category = st.text_input("Category", placeholder="Food, Rent, Travel…")
        description = st.text_area("Description", placeholder="Optional notes")
        payment_method = st.text_input("Payment Method", placeholder="UPI, Card, Cash")
        tags = st.text_input("Tags (comma-separated)")
        
        if st.form_submit_button("Save Expense"):
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                try:
                    db.add_transaction(
                        user_id=st.session_state.auth["user_id"],
                        amount=float(amount),
                        description=description.strip(),
                        category=category.strip() or "Uncategorized",
                        date=date_val,
                        txn_type="Expense",
                        payment_method=payment_method.strip() or None,
                        tags=tags.strip() or None,
                    )
                    st.session_state.show_expense_success = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding expense: {str(e)}")

with st.expander("Add New Income", expanded=False):
    with st.form("add_income"):
        c1, c2 = st.columns(2)
        with c1:
            amount = st.number_input("Amount (₹)", min_value=0.0, step=500.0, format="%0.2f", key="income_amount")
            # Add a selectbox for common income types
            income_type = st.selectbox("Income Type", 
                                     options=["Salary", "Bonus", "Freelance", "Investment", "Other"], 
                                     index=0)
            if income_type == "Other":
                source = st.text_input("Custom Category", placeholder="Enter custom category")
            else:
                source = income_type
        with c2:
            date_val = st.date_input("Date", value=dt.date.today(), key="income_date")
        description = st.text_area("Description", placeholder="Optional notes", key="income_desc")
        payment_method = st.text_input("Payment Method", placeholder="Bank, UPI", key="income_pay")
        
        if st.form_submit_button("Save Income"):
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                try:
                    db.add_transaction(
                        user_id=st.session_state.auth["user_id"],
                        amount=float(amount),
                        description=description.strip(),
                        category=source.strip() or "Income",
                        date=date_val,
                        txn_type="Income",
                        payment_method=payment_method.strip() or None,
                        tags=None,
                    )
                    st.session_state.show_income_success = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding income: {str(e)}")

st.subheader("Recent Transactions")
recent_transactions = db.list_transactions(
    user_id=st.session_state.auth["user_id"],
    start_date=dt.date.today() - dt.timedelta(days=7),
    end_date=dt.date.today(),
)

if recent_transactions:
    for txn in recent_transactions[-5:]:  # Show last 5 transactions
        col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
        with col1:
            st.write(f"**{txn['category']}**")
        with col2:
            color = "red" if txn['type'] == 'Expense' else "green"
            sign = "-" if txn['type'] == 'Expense' else "+"
            st.write(f":{color}[{sign}₹{txn['amount']:,.2f}]")
        with col3:
            st.write(txn['date'])
        with col4:
            desc = txn.get('description') or ''
            st.write(desc[:30] + '...' if len(desc) > 30 else desc)
else:
    st.info("No recent transactions found.")