import datetime as dt
from typing import Tuple

import pandas as pd
import plotly.express as px
import streamlit as st

import db
from auth import hash_password, verify_password


# App Bootstrap
st.set_page_config(
    page_title="Walletwise",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ensure database exists and is migrated
db.init_db()


# Helpers 
def get_month_bounds(target_date: dt.date) -> Tuple[dt.date, dt.date]:
    first_day = target_date.replace(day=1)
    if first_day.month == 12:
        next_month_first = first_day.replace(year=first_day.year + 1, month=1)
    else:
        next_month_first = first_day.replace(month=first_day.month + 1)
    last_day = next_month_first - dt.timedelta(days=1)
    return first_day, last_day


def ensure_session_defaults() -> None:
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


ensure_session_defaults()


# Main Page Title
st.title("💸 Walletwise")
st.caption("Streamlit + SQLite")

def is_valid_email(email: str) -> bool:
    """Validate email format using a simple regex pattern."""
    import re
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

# Main Page Authentication
if not st.session_state.auth["logged_in"]:
    st.markdown("---")
    st.subheader("Welcome! Please login or create an account to continue.")
    
    tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])

    with tab_login:
        st.markdown("#### Sign in to your account")
        with st.form("login_form", clear_on_submit=False):
            col1, col2 = st.columns([2, 1])
            with col1:
                email = st.text_input("Email Address", key="login_email", placeholder="Enter your email")
                password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")
            with col2:
                st.write("")  # spacing
                st.write("")  # spacing
                submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                
            if submitted:
                if not email or not password:
                    st.error("Please fill in both email and password.")
                elif not is_valid_email(email):
                    st.error("Please enter a valid email address.")
                else:
                    user = db.get_user_by_email(email)
                    if not user:
                        st.error("No account found with this email.")
                    else:
                        if verify_password(password, user["password_hash"]):
                            st.session_state.auth = {
                                "user_id": user["id"],
                                "name": user["name"],
                                "email": user["email"],
                                "logged_in": True,
                            }
                            st.success("Signed in successfully!")
                            st.rerun()
                        else:
                            st.error("Incorrect password.")

    with tab_register:
        st.markdown("#### Create a new account")
        with st.form("register_form", clear_on_submit=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                name = st.text_input("Full Name", placeholder="Enter your full name")
                reg_email = st.text_input("Email Address", key="register_email", placeholder="Enter your email")
                reg_password = st.text_input("Password", type="password", key="register_password", placeholder="Create a password")
                reg_password2 = st.text_input("Confirm Password", type="password", key="register_password2", placeholder="Confirm your password")
            with col2:
                st.write("")  # spacing
                st.write("")  # spacing
                st.write("")  # spacing
                st.write("")  # spacing
                submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")
                
            if submitted:
                if not name or not reg_email or not reg_password:
                    st.error("All fields are required.")
                elif not is_valid_email(reg_email):
                    st.error("Please enter a valid email address.")
                elif len(reg_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif reg_password != reg_password2:
                    st.error("Passwords do not match.")
                elif db.get_user_by_email(reg_email):
                    st.error("An account with this email already exists.")
                else:
                    db.create_user(name=name, email=reg_email, password_hash=hash_password(reg_password))
                    st.success("Account created successfully! You can now log in.")

    st.stop()

# If user is logged in, show sidebar and main content
with st.sidebar:
    st.markdown("---")
    st.subheader(f"👋 Hello, {st.session_state.auth['name']}")
    st.caption(f"📧 {st.session_state.auth['email']}")
    
    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.auth = {"user_id": None, "name": None, "email": None, "logged_in": False}
        st.rerun()

    st.markdown("---")
    page = st.radio("📍 Navigate", ["Dashboard", "Add Transaction", "Transactions", "Budgets", "Group Expenses", "Import/Export", "Settings"], index=0)

    st.markdown("---")
    st.subheader("🔍 Filters")
    categories = ["All"] + db.get_distinct_categories(st.session_state.auth["user_id"])
    start_default = st.session_state.filters["start_date"]
    end_default = st.session_state.filters["end_date"]
    start_date = st.date_input("Start Date", value=start_default)
    end_date = st.date_input("End Date", value=end_default)
    category_filter = st.selectbox("Category", categories, index=categories.index(st.session_state.filters["category"]) if st.session_state.filters["category"] in categories else 0)
    type_filter = st.selectbox("Type", ["All", "Expense", "Income"], index=["All", "Expense", "Income"].index(st.session_state.filters["txn_type"]))

    st.session_state.filters.update(
        {
            "start_date": start_date,
            "end_date": end_date,
            "category": category_filter,
            "txn_type": type_filter,
        }
    )

# Data Loading 
def load_transactions_df() -> pd.DataFrame:
    user_id = st.session_state.auth["user_id"]
    f = st.session_state.filters
    rows = db.list_transactions(
        user_id=user_id,
        start_date=f["start_date"],
        end_date=f["end_date"],
        category=None if f["category"] == "All" else f["category"],
        txn_type=None if f["txn_type"] == "All" else f["txn_type"],
    )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["amount"] = df["amount"].astype(float)
    return df


def kpi(total_expense: float, total_income: float) -> None:
    net = total_income - total_expense
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Expense", f"₹ {total_expense:,.2f}")
    c2.metric("Total Income", f"₹ {total_income:,.2f}")
    c3.metric("Net", f"₹ {net:,.2f}", delta=f"{(total_income/total_expense - 1)*100:.1f}%" if total_expense else None)


# Pages 
if page == "Dashboard":
    st.header("📊 Dashboard")
    
    df = load_transactions_df()
    if df.empty:
        st.info("No transactions for selected period.")
    else:
        total_expense = df.loc[df["type"] == "Expense", "amount"].sum()
        total_income = df.loc[df["type"] == "Income", "amount"].sum()
        kpi(total_expense, total_income)

        # Time Period Selector
        time_period = st.selectbox("Time Period", 
                                 ["Daily", "Weekly", "Monthly", "Yearly"],
                                 help="Select the time grouping for the charts")

        # Prepare time-based aggregation
        df['date'] = pd.to_datetime(df['date'])
        if time_period == "Weekly":
            df['period'] = df['date'].dt.strftime('%Y-W%U')
        elif time_period == "Monthly":
            df['period'] = df['date'].dt.strftime('%Y-%m')
        elif time_period == "Yearly":
            df['period'] = df['date'].dt.strftime('%Y')
        else:  # Daily
            df['period'] = df['date'].dt.strftime('%Y-%m-%d')

        # Visualization Tabs
        tab1, tab2, tab3 = st.tabs(["📈 Trends", "🥧 Categories", "📊 Analysis"])
        
        with tab1:
            # Trend Analysis
            trend_data = df.groupby(["period", "type"], as_index=False)["amount"].sum()
            
            col1, col2 = st.columns([2, 1])
            with col1:
                fig_line = px.line(trend_data, x="period", y="amount", color="type", 
                                 markers=True, title=f"{time_period} Trend")
                st.plotly_chart(fig_line, use_container_width=True)
            
            with col2:
                # Stacked Bar Chart
                fig_bar = px.bar(trend_data, x="period", y="amount", color="type",
                               title=f"{time_period} Breakdown", barmode="stack")
                st.plotly_chart(fig_bar, use_container_width=True)

        with tab2:
            # Category Analysis
            col1, col2 = st.columns([1, 1])
            with col1:
                cat = df[df["type"] == "Expense"].groupby("category", as_index=False)["amount"].sum()
                if not cat.empty:
                    fig_pie = px.pie(cat, names="category", values="amount", 
                                   title="Expenses by Category", hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)

            with col2:
                # Top Categories Bar Chart
                cat_sorted = cat.sort_values("amount", ascending=True).tail(5)
                fig_bar = px.bar(cat_sorted, x="amount", y="category", 
                               title="Top 5 Expense Categories",
                               orientation='h')
                st.plotly_chart(fig_bar, use_container_width=True)

        with tab3:
            # Advanced Analysis
            col1, col2 = st.columns([1, 1])
            with col1:
                # Category Trends
                cat_trend = df[df["type"] == "Expense"].pivot_table(
                    index="period", columns="category", values="amount", 
                    aggfunc="sum").fillna(0)
                fig_cat_trend = px.line(cat_trend, title="Category Trends Over Time")
                st.plotly_chart(fig_cat_trend, use_container_width=True)
            
            with col2:
                # Expense Distribution
                fig_box = px.box(df[df["type"] == "Expense"], x="category", y="amount",
                               title="Expense Distribution by Category")
                st.plotly_chart(fig_box, use_container_width=True)

        st.subheader("💰 Budget Progress")
        ym = st.session_state.filters["start_date"].strftime("%Y-%m")
        overall_budget = db.get_budget(st.session_state.auth["user_id"], ym, category=None)
        if overall_budget is not None:
            used = total_expense
            pct = min(100.0, (used / overall_budget * 100) if overall_budget else 0.0)
            st.progress(pct / 100.0, text=f"{pct:.1f}% used (₹ {used:,.0f} / ₹ {overall_budget:,.0f})")
        else:
            st.caption("No budget set for this month.")

elif page == "Add Transaction":
    st.header("➕ Add Transaction")
    with st.form("add_txn_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0, format="%0.2f")
            txn_type = st.selectbox("Type", ["Expense", "Income"], index=0)
        with col2:
            date_val = st.date_input("Date", value=dt.date.today())
            category = st.text_input("Category", placeholder="e.g., Food, Rent")
        with col3:
            payment_method = st.text_input("Payment Method", placeholder="UPI, Card, Cash")
            tags = st.text_input("Tags (comma-separated)")
        description = st.text_area("Description", placeholder="Optional notes")
        submitted = st.form_submit_button("💾 Save Transaction", type="primary")
        if submitted:
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                db.add_transaction(
                    user_id=st.session_state.auth["user_id"],
                    amount=float(amount),
                    description=description.strip(),
                    category=category.strip() or "Uncategorized",
                    date=date_val,
                    txn_type=txn_type,
                    payment_method=payment_method.strip() or None,
                    tags=tags.strip() or None,
                )
                st.success("Transaction added successfully!")
                st.rerun()

elif page == "Transactions":
    st.header("📋 Transactions")
    df = load_transactions_df()
    if df.empty:
        st.info("No transactions to display.")
    else:
        st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)

        st.markdown("---")
        st.subheader("✏️ Edit / Delete")
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            txn_ids = df["id"].tolist()
            selected_id = st.selectbox("Select Transaction ID", txn_ids)
        with col2:
            if st.button("🗑️ Delete", type="primary"):
                db.delete_transaction(selected_id, st.session_state.auth["user_id"])
                st.warning("Transaction deleted.")
                st.rerun()
        with col3:
            open_edit = st.checkbox("✏️ Edit")

        if open_edit and selected_id:
            row = df[df["id"] == selected_id].iloc[0]
            with st.form("edit_txn_form"):
                e_col1, e_col2, e_col3 = st.columns(3)
                with e_col1:
                    e_amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0, value=float(row["amount"]))
                    e_type = st.selectbox("Type", ["Expense", "Income"], index=0 if row["type"] == "Expense" else 1)
                with e_col2:
                    e_date = st.date_input("Date", value=row["date"])  # type: ignore[arg-type]
                    e_category = st.text_input("Category", value=row["category"])
                with e_col3:
                    e_payment = st.text_input("Payment Method", value=row.get("payment_method") or "")
                    e_tags = st.text_input("Tags", value=row.get("tags") or "")
                e_desc = st.text_area("Description", value=row.get("description") or "")
                save = st.form_submit_button("💾 Save Changes", type="primary")
                if save:
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
                    st.success("Transaction updated successfully!")
                    st.rerun()

elif page == "Budgets":
    st.header("💰 Budgets")
    ym = st.date_input("Month", value=st.session_state.filters["start_date"]).strftime("%Y-%m")
    overall_current = db.get_budget(st.session_state.auth["user_id"], ym, category=None)
    with st.form("budget_form"):
        overall_budget = st.number_input("Overall Monthly Budget (₹)", min_value=0.0, step=500.0, value=float(overall_current or 0.0))
        cat_name = st.text_input("Category (optional)")
        cat_budget_existing = db.get_budget(st.session_state.auth["user_id"], ym, category=cat_name.strip() or None) if cat_name else None
        cat_budget = st.number_input("Category Budget (₹)", min_value=0.0, step=500.0, value=float(cat_budget_existing or 0.0))
        submitted = st.form_submit_button("💾 Save Budgets", type="primary")
        if submitted:
            db.set_budget(st.session_state.auth["user_id"], ym, None, overall_budget)
            if cat_name.strip():
                db.set_budget(st.session_state.auth["user_id"], ym, cat_name.strip(), cat_budget)
            st.success("Budget(s) saved successfully!")

    st.subheader("📊 Utilization")
    df = load_transactions_df()
    total_expense = df.loc[df["type"] == "Expense", "amount"].sum() if not df.empty else 0.0
    if overall_current is not None and overall_current > 0:
        pct = min(100.0, (total_expense / overall_current * 100))
        st.progress(pct / 100.0, text=f"Overall: {pct:.1f}% (₹ {total_expense:,.0f} / ₹ {overall_current:,.0f})")
    else:
        st.caption("No overall budget set.")

    by_cat = (
        df[df["type"] == "Expense"].groupby("category", as_index=False)["amount"].sum() if not df.empty else pd.DataFrame(columns=["category", "amount"])
    )
    if not by_cat.empty:
        for _, r in by_cat.iterrows():
            b = db.get_budget(st.session_state.auth["user_id"], ym, r["category"]) or 0.0
            if b > 0:
                p = min(100.0, r["amount"] / b * 100)
                st.progress(p / 100.0, text=f"{r['category']}: {p:.1f}% (₹ {r['amount']:,.0f} / ₹ {b:,.0f})")

elif page == "Import/Export":
    st.header("📤📥 Import / Export")
    st.write("Download your data as CSV or import transactions from CSV.")

    df = load_transactions_df()
    if not df.empty:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Current View (CSV)", data=csv, file_name="transactions.csv", mime="text/csv")

    st.subheader("📤 Import CSV")
    st.caption("Required columns: date (YYYY-MM-DD), amount, type (Expense/Income). Optional: category, description, payment_method, tags")
    file = st.file_uploader("Choose CSV file", type=["csv"])
    if file is not None:
        import_df = pd.read_csv(file)
        required = {"date", "amount", "type"}
        if not required.issubset(set(map(str.lower, import_df.columns))):
            st.error("CSV missing required columns.")
        else:
            # Normalize columns
            cols = {c: c.lower() for c in import_df.columns}
            import_df.rename(columns=cols, inplace=True)
            import_df["category"] = import_df.get("category", "Uncategorized").fillna("Uncategorized")
            import_df["description"] = import_df.get("description", "").fillna("")
            import_df["payment_method"] = import_df.get("payment_method", None)
            import_df["tags"] = import_df.get("tags", None)
            # Insert
            inserted = 0
            for _, r in import_df.iterrows():
                try:
                    db.add_transaction(
                        user_id=st.session_state.auth["user_id"],
                        amount=float(r["amount"]),
                        description=str(r["description"]).strip(),
                        category=str(r["category"]).strip() or "Uncategorized",
                        date=dt.date.fromisoformat(str(r["date"])[:10]),
                        txn_type=str(r["type"]).title(),
                        payment_method=(str(r["payment_method"]) if pd.notna(r["payment_method"]) else None),
                        tags=(str(r["tags"]) if pd.notna(r["tags"]) else None),
                    )
                    inserted += 1
                except Exception as exc:  # noqa: BLE001
                    st.warning(f"Skipped a row due to error: {exc}")
            st.success(f"Imported {inserted} transactions successfully!")

elif page == "Group Expenses":
    st.switch_page("pages/4_👥_Group_Expenses.py")

elif page == "Settings":
    st.header("⚙️ Settings")
    with st.form("password_change_form"):
        st.subheader("🔐 Change Password")
        old = st.text_input("Current Password", type="password")
        new = st.text_input("New Password", type="password")
        new2 = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("🔄 Update Password", type="primary")
        if submitted:
            user = db.get_user_by_email(st.session_state.auth["email"])  # fresh read
            if not verify_password(old, user["password_hash"]):
                st.error("Current password is incorrect.")
            elif len(new) < 6:
                st.error("New password must be at least 6 characters long.")
            elif new != new2:
                st.error("New passwords do not match.")
            else:
                db.update_user_password(user_id=user["id"], new_hash=hash_password(new))
                st.success("Password updated successfully!")