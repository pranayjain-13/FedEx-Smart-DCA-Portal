import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# --- CONFIG & BRANDING ---
st.set_page_config(page_title="FedEx DCA | Intelligent Portal", layout="wide")

# FedEx Professional UI Styling
st.markdown("""
    <style>
    :root { --fedex-purple: #4D148C; --fedex-orange: #FF6200; }
    .main { background-color: #f4f7f6; }
    div[data-testid="stMetricValue"] { 
        background-color: white; 
        padding: 20px; 
        border-radius: 12px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
        border-left: 6px solid #4D148C; 
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #4D148C !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- HELPER: AUDIT LOGGING ---
def add_audit_log(action, user="System Manager"):
    new_log = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
        "User": user, 
        "Action": action
    }
    st.session_state.audit_logs = pd.concat([pd.DataFrame([new_log]), st.session_state.audit_logs], ignore_index=True)

# --- AI ENGINE ---
def apply_ai_logic(df):
    """Predictive Scoring & Automated Allocation Logic"""
    # Clean column names to handle variations
    df.columns = df.columns.str.strip()
    
    # AI Score: Predicts recovery based on age and amount
    df['AI Score'] = (100 - (df['Age'] * 0.4) - (df['Amount'] / 3000)).clip(5, 100).astype(int)
    
    # Automated SOP Allocation
    conditions = [(df['AI Score'] > 75), (df['AI Score'] > 45), (df['AI Score'] <= 45)]
    choices = ['Apex Collections', 'Global Recovery', 'Swift Debt Ltd']
    df['Allocated Agency'] = np.select(conditions, choices, default='Unallocated')
    df['Status'] = 'Allocated'
    return df

# --- SESSION INITIALIZATION ---
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame()
if 'audit_logs' not in st.session_state:
    st.session_state.audit_logs = pd.DataFrame(columns=["Timestamp", "User", "Action"])

# --- SIDEBAR: SMART IMPORT ---
st.sidebar.image("FedEx.png", use_container_width=True)
st.sidebar.markdown("### Data Management")

# Support for both CSV and XLSX
uploaded_file = st.sidebar.file_uploader("📂 Import Legacy Cases", type=['csv', 'xlsx'])

if uploaded_file:
    file_key= f"loaded_{uploaded_file.name}_{uploaded_file.size}"

    if st.session_state.get('current_file') != file_key:
        try:

            if uploaded_file.name.endswith('.csv'):
                new_data = pd.read_csv(uploaded_file)
            else:
                new_data = pd.read_excel(uploaded_file)
        
            processed_df = apply_ai_logic(new_data)
            
            st.session_state.db = apply_ai_logic(new_data)
            st.session_state.current_file=file_key

            add_audit_log(f"Bulk Ingested {len(new_data)} cases via {uploaded_file.name}")
            st.sidebar.success(f"Success! {len(new_data)} cases loaded.")
        except Exception as e:
            st.sidebar.error(f"Format Error: Ensure columns are 'Case ID', 'Customer Name', 'Amount', 'Age'")

# --- MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["📊 Executive Overview", "🏢 Agency Gateway", "📜 Governance Log"])

# --- TAB 1: EXECUTIVE VIEW ---
with tab1:
    st.title("DCA Management Dashboard")
    if not st.session_state.db.empty:
        df = st.session_state.db
        
        # Calculate counts dynamically
        total_cases = len(df)
        # We use .str.strip() to avoid errors with hidden spaces
        closed_cases = len(df[df['Status'].str.strip() == 'Closed'])

        if total_cases > 0:
            completion_rate = (closed_cases / total_cases) * 100
        else:
            completion_rate = 0

        # 1. KPI Row
        c1, c2, c3, c4 = st.columns(4)
        total_debt = df['Amount'].sum()
        c1.metric("Total Debt Portfolio", f"${total_debt:,.0f}")
        c2.metric("Total Cases", len(df))
        c3.metric("Avg Recovery Score", f"{int(df['AI Score'].mean())}%")

        # Calculate Recovery Completion %
        closed_cases = len(df[df['Status'] == 'Closed'])
        completion_rate = (closed_cases / len(df)) * 100
        c4.metric("Recovery Completion", f"{completion_rate:.1f}%")

        # 2. Status Progress Bar (New Feature)
        st.subheader("🏁 Global Recovery Progress")
        
        # Visual Progress Bar
        st.progress(completion_rate/100)
        st.caption(f"{closed_cases} out of {len(df)} cases successfully closed.")

        st.divider()

        # 3. Enhanced Analytics Section
        col_chart, col_status = st.columns([2, 1])
        
        with col_chart:
            st.write("### Recovery Forecast by Agency")
            fig = px.bar(df, x="Allocated Agency", y="Amount", color="Status", 
                         title="Portfolio by Agency and Status",
                         color_discrete_map={"Allocated": "#4D148C", "Closed": "#28a745", "Disputed": "#dc3545", "Contacted": "#FF6200"},
                         template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        with col_status:
            st.write("### Status Breakdown")
            status_counts = df['Status'].value_counts().reset_index()
            fig_pie = px.pie(status_counts, values='count', names='Status', 
                            color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        st.subheader("Global Case Inventory")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("👋 Welcome. Please upload an Excel or CSV file in the sidebar to generate the AI portfolio.")

# --- TAB 2: AGENCY PORTAL (Final Look) ---
with tab2:
    st.header("🏢 Secure Agency Gateway")
    st.caption("Role-based access for Debt Collection Agencies to manage and update assigned cases.")

    if not st.session_state.db.empty:
        # Simulated Role Selection
        agency_list = ['Apex Collections', 'Global Recovery', 'Swift Debt Ltd']
        selected_agency = st.selectbox("Switch Agency View", agency_list)
        
        # Filter data so Agency A cannot see Agency B's cases
        agency_df = st.session_state.db[st.session_state.db['Allocated Agency'] == selected_agency]
        
        # Dashboard for the specific agency
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            total_allotted=len(agency_df)
            st.metric("Total Allotted Cases",total_allotted)
            pending_count = len(agency_df[agency_df['Status'] != 'Closed'])
            st.metric("Pending Cases", pending_count)
        with col_stat2:
            agency_debt = agency_df['Amount'].sum()
            st.metric("Total Portfolio Value", f"${agency_debt:,.0f}")
    # Filter to include only cases that are NOT 'Closed'
            pending_debt_df = agency_df[agency_df['Status'] != 'Closed']
            agency_debt = pending_debt_df['Amount'].sum()
    
            st.metric("Pending Portfolio Value", f"${agency_debt:,.0f}")
        st.divider()

        # 🔍 SEARCH & UPDATE SECTION
        st.subheader("Update Case Status")
        search_id = st.text_input("🔍 Search by Case ID (e.g., FX-INV-10001)", placeholder="Type to filter...")

        # Apply search filter to the selection list
        if search_id:
            filtered_list = agency_df[agency_df['Case ID'].str.contains(search_id, case=False)]
        else:
            filtered_list = agency_df

        with st.expander("📝 Open Update Form", expanded=True):
            if not filtered_list.empty:
                # The actual selection box for the update
                target_case = st.selectbox("Confirm Case ID to modify:", filtered_list['Case ID'])
                
                c_form1, c_form2 = st.columns(2)
                with c_form1:
                    new_status = st.selectbox("Select New Status", 
                                            ["Allocated", "Contacted", "PTP (Promise to Pay)", "Disputed", "Closed"])
                with c_form2:
                    note = st.text_input("Add Operational Note", placeholder="e.g., Spoke to manager...")

                if st.button("🚀 Submit Official Update"):
                    # 1. Update the Main Database
                    st.session_state.db.loc[st.session_state.db['Case ID'] == target_case, 'Status'] = new_status
                    
                    # 2. Log the Action (with the note)
                    log_entry = f"Status: {new_status} | Note: {note}"
                    add_audit_log(f"Agency {selected_agency} updated {target_case}: {log_entry}", user=selected_agency)
                    
                    # 3. Success Message & UI Refresh
                    st.toast(f"Success! {target_case} updated to {new_status}.")
                    st.rerun() # This triggers the Progress Bar in Tab 1 to move!
            else:
                st.warning("No matching cases found for this agency.")

        st.divider()
        
        # DATA TABLE VIEW
        st.subheader(f"Current Assignments: {selected_agency}")
        st.dataframe(agency_df, use_container_width=True, hide_index=True)
        
    else:
        st.info("⚠️ No data available. Please upload a CSV or Excel file in the 'Management Operations' tab.")

        
# TAB 3: AUDIT LOG
with tab3:
    st.title("System Audit Trail & Compliance")
    st.markdown("Immutable record of all system activities, satisfying FedEx governance requirements.")
    st.table(st.session_state.audit_logs)
