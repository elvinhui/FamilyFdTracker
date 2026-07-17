import streamlit as st
import pandas as pd
from db import DynamoDBHandler
from analytics import AnalyticsEngine

st.set_page_config(page_title="Family FD Tracker", page_icon="🏦", layout="wide")

st.title("🏦 Family Fixed Deposit Tracker")

db = DynamoDBHandler()
engine = AnalyticsEngine()

# --- SIDEBAR: Add New Deposit ---
st.sidebar.header("Add New Deposit")
with st.sidebar.form("add_fd_form"):
    bank_code = st.text_input("Bank Code (e.g., MBB, PBB)", max_chars=10)
    account_full = st.text_input("Full Account Number", help="Will be masked before saving.")
    principal = st.number_input("Principal Amount", min_value=0.0, step=1000.0)
    interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, step=0.1, format="%.2f")
    maturity_date = st.date_input("Maturity Date")
    
    submitted = st.form_submit_button("Add Deposit")
    if submitted:
        if bank_code and account_full:
            # Format date as YYYY-MM-DD
            date_str = maturity_date.strftime("%Y-%m-%d")
            db.add_deposit(bank_code, account_full, principal, interest_rate, date_str)
            st.sidebar.success("Deposit added successfully!")
        else:
            st.sidebar.error("Bank code and account number are required.")

# --- MAIN PAGE: Dashboard ---
st.header("Portfolio Overview")

# Fetch active deposits
active_items = db.get_all_active_deposits()
df = engine.load_data(active_items)
df = engine.calculate_days_to_maturity(df)

summary = engine.get_portfolio_summary(df)

col1, col2, col3 = st.columns(3)
col1.metric("Active Deposits", summary['active_deposits'])
col2.metric("Total Principal", f"${summary['total_principal']:,.2f}")
col3.metric("Weighted Avg Interest", f"{summary['weighted_avg_interest']:.2f}%")

st.subheader("Active Fixed Deposits")
if not df.empty:
    # Select columns to display and rename them for clarity
    display_df = df[['bank_code', 'account_tail', 'principal_amount', 'interest_rate', 'maturity_date', 'days_to_maturity']]
    display_df.columns = ['Bank', 'Account', 'Principal', 'Interest (%)', 'Maturity Date', 'Days Left']
    
    # Sort by days left
    display_df = display_df.sort_values(by='Days Left')
    
    st.dataframe(display_df, use_container_width=True)
else:
    st.info("No active fixed deposits found.")

# Simple refresh button
if st.button("Refresh Data"):
    st.rerun()
