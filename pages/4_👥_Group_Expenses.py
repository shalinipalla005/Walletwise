import datetime as dt
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

import db

# Initialize session state
def init_session_state():
    if "auth" not in st.session_state:
        st.session_state.auth = {
            "user_id": None,
            "name": None,
            "email": None,
            "logged_in": False,
        }

init_session_state()

# Check if user is logged in
if not st.session_state.get("auth", {}).get("logged_in", False):
    st.error("Please login from the main page to access this feature.")
    if st.button("Go to Login"):
        st.switch_page("streamlit_app.py")
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown("---")
    st.subheader(f"👋 Hello, {st.session_state.auth['name']}")
    st.caption(f"📧 {st.session_state.auth['email']}")
    
    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.auth = {"user_id": None, "name": None, "email": None, "logged_in": False}
        st.switch_page("streamlit_app.py")

st.title("👥 Group Expenses")

# Get user balance summary with error handling
try:
    balance_summary = db.get_user_balance_summary(st.session_state.auth["user_id"])
    expense_stats = db.get_group_expense_statistics(st.session_state.auth["user_id"], days=30)
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    balance_summary = {
        'total_owes': 0, 'total_owed_to_user': 0, 'net_balance': 0, 
        'total_paid': 0, 'owes_to': [], 'owed_by': []
    }
    expense_stats = {'recent_expenses_count': 0, 'recent_expenses_total': 0, 'categories': []}

# Display balance overview
st.subheader("💰 Balance Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("You Owe", f"₹{balance_summary['total_owes']:,.2f}", 
              delta=None, delta_color="inverse")

with col2:
    st.metric("Owed to You", f"₹{balance_summary['total_owed_to_user']:,.2f}")

with col3:
    net_balance = balance_summary['net_balance']
    color = "normal" if net_balance >= 0 else "inverse"
    st.metric("Net Balance", f"₹{net_balance:,.2f}", 
              delta=f"{'Positive' if net_balance >= 0 else 'Negative'}", delta_color=color)

with col4:
    st.metric("Total Paid", f"₹{balance_summary['total_paid']:,.2f}")

# Quick settlement reminder
if balance_summary['total_owes'] > 0:
    st.warning(f"⚠️ You have pending payments of ₹{balance_summary['total_owes']:,.2f}")

# Tabs for different functionalities
tab_overview, tab_add, tab_expenses, tab_settle, tab_analytics = st.tabs([
    "🏠 Overview", "➕ Add Expense", "📋 All Expenses", "💳 Settle Up", "📊 Analytics"
])


with tab_overview:
    st.subheader("Recent Activity")
    
    # Show recent expenses
    try:
        recent_expenses = db.get_group_expenses(
            st.session_state.auth["user_id"], 
            limit=5, 
            include_settled=True
        )
        
        if recent_expenses:
            for exp in recent_expenses:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.write(f"**{exp['title']}**")
                        st.caption(f"📅 {exp['date']} | 🏷️ {exp['category']} | 💳 {exp['payer_name']}")
                        if exp.get('description'):
                            st.caption(f"📝 {exp['description']}")
                    
                    with col2:
                        st.write(f"₹{exp['amount']:,.2f}")
                        if 'share_amount' in exp:
                            st.caption(f"Your share: ₹{exp['share_amount']:,.2f}")
                    
                    with col3:
                        # Fixed logic: Check if user's share is settled, not the entire expense
                        if exp['payer_id'] == st.session_state.auth["user_id"]:
                            # If user is the payer, show overall expense status
                            if exp.get('is_settled'):
                                st.success("✅ All Settled")
                            else:
                                st.warning("⏳ Partially Paid")
                        else:
                            # If user is a participant, show their share status
                            if exp.get('share_settled', True):  # Default to True if not found
                                st.success("✅ Paid")
                            else:
                                st.warning("⏳ Pending")
                    
                    st.markdown("---")
        else:
            st.info("No recent group expenses found.")
            
    except Exception as e:
        st.error(f"Error loading recent expenses: {str(e)}")
    

with tab_add:
    st.subheader("➕ Add Group Expense")
    
    with st.form("add_group_expense", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Expense Title*", placeholder="Dinner, Trip, Movie, etc.")
            amount = st.number_input("Total Amount (₹)*", min_value=0.0, step=100.0, format="%.2f")
            category = st.selectbox("Category", [
                "Food & Dining", "Transportation", "Entertainment", "Travel", 
                "Shopping", "Bills & Utilities", "Healthcare", "Other"
            ])
        
        with col2:
            date = st.date_input("Date*", value=dt.date.today())
            description = st.text_area("Description", placeholder="Optional details about the expense")
        
        st.subheader("Split Details")
        
        # Get available users
        try:
            all_users = db.get_all_users()
            available_users = [
                (u["id"], u["name"]) for u in all_users 
                if u["id"] != st.session_state.auth["user_id"]
            ]
        except Exception as e:
            st.error(f"Error loading users: {str(e)}")
            available_users = []
        
        if not available_users:
            st.warning("No other users found. You need other users to create group expenses.")
        else:
            selected_users = st.multiselect(
                "Split with (select people to share this expense)*",
                options=available_users,
                format_func=lambda x: x[1],
                help="Select the people who will share this expense with you"
            )
            
            split_type = st.radio(
                "How to split?", 
                ["Equal Split", "Custom Amounts"],
                help="Equal: divide amount equally among all participants. Custom: specify individual amounts."
            )
            
            shares = []
            current_user_share = 0
            
            if selected_users and amount > 0:
                if split_type == "Equal Split":
                    total_people = len(selected_users) + 1  # +1 for current user
                    share_per_person = round(amount / total_people, 2)
                    
                    # Handle rounding difference
                    total_allocated = share_per_person * (total_people - 1)
                    current_user_share = amount - total_allocated
                    
                    st.info(f"Each person's share: ₹{share_per_person:,.2f} (Your share: ₹{current_user_share:,.2f})")
                    
                    for user_id, user_name in selected_users:
                        shares.append({"user_id": user_id, "amount": share_per_person})
                    
                else:  # Custom amounts
                    st.write("Specify amounts for each person:")
                    total_others = 0
                    
                    for user_id, user_name in selected_users:
                        share_amount = st.number_input(
                            f"Amount for {user_name} (₹)",
                            min_value=0.0,
                            max_value=amount,
                            step=10.0,
                            key=f"share_{user_id}",
                            format="%.2f"
                        )
                        if share_amount > 0:
                            shares.append({"user_id": user_id, "amount": share_amount})
                            total_others += share_amount
                    
                    current_user_share = amount - total_others
                    
                    if current_user_share < 0:
                        st.error(f"Total shares (₹{total_others:,.2f}) exceed expense amount (₹{amount:,.2f})")
                    elif current_user_share >= 0:
                        st.success(f"Your share: ₹{current_user_share:,.2f}")
            
            # Add current user's share
            if current_user_share > 0:
                shares.append({
                    "user_id": st.session_state.auth["user_id"], 
                    "amount": current_user_share
                })
        
        submitted = st.form_submit_button("💾 Create Group Expense", type="primary")
        
        if submitted:
            # Validation
            if not title.strip():
                st.error("Please enter an expense title.")
            elif amount <= 0:
                st.error("Amount must be greater than 0.")
            elif not available_users:
                st.error("No other users available to share expenses with.")
            elif not selected_users:
                st.error("Please select at least one person to share with.")
            elif abs(sum(s["amount"] for s in shares) - amount) > 0.01:
                st.error("Share amounts must equal the total expense amount.")
            else:
                try:
                    expense_id = db.add_group_expense(
                        title=title.strip(),
                        amount=amount,
                        payer_id=st.session_state.auth["user_id"],
                        category=category,
                        date=date,
                        description=description.strip(),
                        shares=shares
                    )
                    st.success(f"✅ Group expense '{title}' created successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating expense: {str(e)}")

with tab_expenses:
    st.subheader("📋 All Group Expenses")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        show_settled = st.checkbox("Include Settled Expenses", value=True)
    with col2:
        limit_results = st.number_input("Number of expenses to show", min_value=5, max_value=100, value=20)
    with col3:
        st.write("")  # spacing
    
    try:
        all_expenses = db.get_group_expenses(
            st.session_state.auth["user_id"],
            limit=limit_results,
            include_settled=show_settled
        )
        
        if all_expenses:
            # Create DataFrame for better display
            display_data = []
            for exp in all_expenses:
                # Get the expense ID safely
                expense_id = exp.get('id') or exp.get('expense_id')
                
                status = "✅ Settled" if exp.get('is_settled') else "⏳ Pending"
                your_share = exp.get('share_amount', 0)
                your_status = "✅" if exp.get('share_settled', True) else "⏳"
                
                display_data.append({
                    "Date": exp['date'],
                    "Title": exp['title'],
                    "Category": exp['category'],
                    "Total Amount": f"₹{exp['amount']:,.2f}",
                    "Your Share": f"₹{your_share:,.2f}",
                    "Paid By": exp['payer_name'],
                    "Your Status": your_status,
                    "Overall Status": status,
                    "ID": expense_id
                })
            
            df = pd.DataFrame(display_data)
            
            # Display with styling
            st.dataframe(
                df.drop('ID', axis=1),  # Hide ID column
                use_container_width=True,
                height=400
            )
            
            # Expense management section
            st.markdown("---")
            st.subheader("🛠️ Manage Expenses")
            
            if len(all_expenses) > 0:
                col1, col2 = st.columns([2, 1])
                with col1:
                    # Create options with proper IDs
                    expense_options = []
                    for exp in all_expenses:
                        expense_id = exp.get('id') or exp.get('expense_id')
                        expense_options.append((expense_id, exp['title']))
                    
                    selected_expense_id = st.selectbox(
                        "Select an expense to manage",
                        options=[opt[0] for opt in expense_options],
                        format_func=lambda x: next(opt[1] for opt in expense_options if opt[0] == x)
                    )
                
                with col2:
                    action = st.selectbox("Action", ["View Details", "Delete"])
                
                if selected_expense_id and action:
                    selected_expense = next((exp for exp in all_expenses 
                                           if (exp.get('id') or exp.get('expense_id')) == selected_expense_id), None)
                    
                    if selected_expense:
                        if action == "View Details":
                            with st.expander("📖 Expense Details", expanded=True):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**Title:** {selected_expense['title']}")
                                    st.write(f"**Amount:** ₹{selected_expense['amount']:,.2f}")
                                    st.write(f"**Category:** {selected_expense['category']}")
                                    st.write(f"**Date:** {selected_expense['date']}")
                                with col2:
                                    st.write(f"**Paid by:** {selected_expense['payer_name']}")
                                    st.write(f"**Status:** {'Settled ✅' if selected_expense.get('is_settled') else 'Pending ⏳'}")
                                    if selected_expense.get('description'):
                                        st.write(f"**Description:** {selected_expense['description']}")
                                
                                # Enhanced share breakdown with proper names
                                if 'shares' in selected_expense and selected_expense['shares']:
                                    st.write("**Share Breakdown:**")
                                    
                                    # Get all user names for the shares
                                    try:
                                        # Get all unique user IDs from shares
                                        user_ids_in_shares = list(set(share['user_id'] for share in selected_expense['shares']))
                                        
                                        # Get user details for all participants
                                        conn = db._connect()
                                        cur = conn.cursor()
                                        
                                        if user_ids_in_shares:
                                            placeholders = ','.join('?' * len(user_ids_in_shares))
                                            cur.execute(f"SELECT id, name FROM users WHERE id IN ({placeholders})", user_ids_in_shares)
                                            user_names = {row['id']: row['name'] for row in cur.fetchall()}
                                            conn.close()
                                            
                                            # Display shares with proper formatting
                                            for share in selected_expense['shares']:
                                                user_name = user_names.get(share['user_id'], f"User {share['user_id']}")
                                                status_icon = "✅" if share.get('is_settled') else "⏳"
                                                
                                                if share['user_id'] == st.session_state.auth["user_id"]:
                                                    if selected_expense['payer_id'] == st.session_state.auth["user_id"]:
                                                        # User is the payer - show as "I paid"
                                                        st.write(f"• **{user_name} (You)**: ₹{share['share_amount']:,.2f} - **I paid this** ✅")
                                                    else:
                                                        # User owes money - show their share
                                                        st.write(f"• **{user_name} (You)**: ₹{share['share_amount']:,.2f} {status_icon}")
                                                else:
                                                    # Other users
                                                    st.write(f"• **{user_name}**: ₹{share['share_amount']:,.2f} {status_icon}")
                                                    
                                        else:
                                            conn.close()
                                            
                                    except Exception as e:
                                        st.error(f"Error loading share details: {str(e)}")
                                        # Fallback to original display
                                        for share in selected_expense['shares']:
                                            status_icon = "✅" if share.get('is_settled') else "⏳"
                                            st.write(f"• User {share['user_id']}: ₹{share['share_amount']:,.2f} {status_icon}")
                        
                        elif action == "Delete" and selected_expense['payer_id'] == st.session_state.auth["user_id"]:
                            st.warning("⚠️ Are you sure you want to delete this expense? This action cannot be undone.")
                            if st.button("🗑️ Confirm Delete", type="primary"):
                                try:
                                    if db.delete_group_expense(selected_expense_id, st.session_state.auth["user_id"]):
                                        st.success("✅ Expense deleted successfully!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to delete expense. You can only delete expenses you created.")
                                except Exception as e:
                                    st.error(f"Error deleting expense: {str(e)}")
                        elif action == "Delete":
                            st.info("You can only delete expenses that you created.")
        
        else:
            st.info("📝 No group expenses found. Create your first group expense using the 'Add Expense' tab!")
            
    except Exception as e:
        st.error(f"Error loading expenses: {str(e)}")     

with tab_settle:
    st.subheader("💳 Settle Up")
    
    try:
        unsettled_expenses = db.get_unsettled_expenses_for_user(st.session_state.auth["user_id"])
        
        if not unsettled_expenses:
            st.success("🎉 Congratulations! You're all settled up. No pending payments.")
            
        else:
            st.write(f"You have **{len(unsettled_expenses)}** pending payments totaling **₹{sum(exp['share_amount'] for exp in unsettled_expenses):,.2f}**")
            
            # Quick settle all option
            col1, col2 = st.columns([1, 1])
            with col1:
                settlement_method = st.selectbox(
                    "Payment Method",
                    ["UPI", "Bank Transfer", "Cash", "Credit Card", "Other"]
                )
            with col2:
                settlement_reference = st.text_input(
                    "Transaction Reference (Optional)",
                    placeholder="UPI Ref: 123456789"
                )
            
            if st.button("💰 Settle All Pending Expenses", type="primary"):
                try:
                    expense_ids = [exp['expense_id'] for exp in unsettled_expenses]
                    result = db.settle_multiple_expenses(
                        st.session_state.auth["user_id"],
                        expense_ids,
                        method=settlement_method,
                        reference=settlement_reference if settlement_reference.strip() else None
                    )
                    
                    if result['settled_count'] > 0:
                        st.success(f"✅ Successfully settled {result['settled_count']} expenses totaling ₹{result['settled_amount']:,.2f}!")
                        st.rerun()
                    else:
                        st.error("❌ No expenses were settled. Please try again.")
                        
                except Exception as e:
                    st.error(f"Error during settlement: {str(e)}")
            
            st.markdown("---")
            st.write("**Individual Settlement Options:**")
            
            # Individual expense settlement
            for i, exp in enumerate(unsettled_expenses):
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.write(f"**{exp['title']}**")
                        st.caption(f"Paid by: {exp['payer_name']} | Date: {exp['date']}")
                        st.caption(f"Total: ₹{exp['total_amount']:,.2f}")
                    
                    with col2:
                        st.write(f"**₹{exp['share_amount']:,.2f}**")
                        st.caption("Your share")
                    
                    with col3:
                        button_key = f"settle_{i}_{exp['share_id']}"
                        if st.button("✅ Settle", key=button_key, use_container_width=True):
                            try:
                                success = db.settle_expense_share(
                                    exp['share_id'],
                                    st.session_state.auth["user_id"],
                                    method=settlement_method,
                                    reference=settlement_reference if settlement_reference.strip() else None
                                )
                                
                                if success:
                                    st.success(f"✅ Settled {exp['title']}!")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Failed to settle {exp['title']}")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    
                    st.markdown("---")
                    
    except Exception as e:
        st.error(f"Error loading settlement data: {str(e)}")

with tab_analytics:
    st.subheader("📊 Expense Analytics")
    
    try:
        # Time period selector
        col1, col2 = st.columns(2)
        with col1:
            analysis_days = st.selectbox("Analysis Period", [7, 30, 90, 180, 365], index=1)
        with col2:
            st.write("")  # spacing
        
        # Get updated statistics
        stats = db.get_group_expense_statistics(st.session_state.auth["user_id"], days=analysis_days)
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Expenses", stats['recent_expenses_count'])
        with col2:
            st.metric("Total Amount", f"₹{stats['recent_expenses_total']:,.2f}")
        with col3:
            avg_expense = stats['recent_expenses_total'] / max(stats['recent_expenses_count'], 1)
            st.metric("Average Expense", f"₹{avg_expense:,.2f}")
        
        # Category breakdown
        if stats['categories']:
            st.subheader("💼 Category Breakdown")
            
            # Prepare data for visualization
            cat_df = pd.DataFrame(stats['categories'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart
                fig_pie = px.pie(
                    cat_df, 
                    values='total_amount', 
                    names='category',
                    title="Spending by Category"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Bar chart
                fig_bar = px.bar(
                    cat_df.sort_values('total_amount', ascending=True),
                    x='total_amount',
                    y='category',
                    orientation='h',
                    title="Category Spending"
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # Category details table
            st.subheader("📋 Category Details")
            cat_df['Amount'] = cat_df['total_amount'].apply(lambda x: f"₹{x:,.2f}")
            cat_df['Count'] = cat_df['expense_count']
            cat_df['Category'] = cat_df['category']
            cat_df['Avg per Expense'] = (cat_df['total_amount'] / cat_df['expense_count']).apply(lambda x: f"₹{x:,.2f}")
            
            st.dataframe(
                cat_df[['Category', 'Count', 'Amount', 'Avg per Expense']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No expense data available for the selected period.")
            
        # Settlement pattern analysis
        st.subheader("💳 Settlement Patterns")
        settlement_col1, settlement_col2 = st.columns(2)
        
        with settlement_col1:
            pending_amount = balance_summary['total_owes']
            total_involved = balance_summary['total_paid'] + balance_summary['total_owed_to_user']
            
            if total_involved > 0:
                settlement_rate = ((total_involved - pending_amount) / total_involved) * 100
                st.metric("Settlement Rate", f"{settlement_rate:.1f}%")
            else:
                st.metric("Settlement Rate", "N/A")
        
        with settlement_col2:
            if balance_summary['owes_to']:
                avg_debt = balance_summary['total_owes'] / len(balance_summary['owes_to'])
                st.metric("Avg Debt per Person", f"₹{avg_debt:,.2f}")
            else:
                st.metric("Avg Debt per Person", "₹0.00")
        
    except Exception as e:
        st.error(f"Error loading analytics: {str(e)}")