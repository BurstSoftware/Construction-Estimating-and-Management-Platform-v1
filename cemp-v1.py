import streamlit as st
import pandas as pd
import sqlite3
import datetime
import uuid

# Initialize SQLite database
conn = sqlite3.connect('construction_platform.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT,
        client TEXT,
        trade TEXT,
        status TEXT,
        created_at TIMESTAMP
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS estimates (
        id TEXT PRIMARY KEY,
        project_id TEXT,
        item TEXT,
        quantity REAL,
        unit_cost REAL,
        total_cost REAL,
        trade TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS time_logs (
        id TEXT PRIMARY KEY,
        project_id TEXT,
        worker TEXT,
        hours REAL,
        date TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS invoices (
        id TEXT PRIMARY KEY,
        project_id TEXT,
        amount REAL,
        status TEXT,
        created_at TIMESTAMP
    )
''')
conn.commit()

# Sample cost database (replace with real data or API in production)
COST_DATABASE = {
    'Plumbing': {'Pipe (per ft)': 5.0, 'Fitting': 10.0, 'Labor (per hr)': 50.0},
    'HVAC': {'Duct (per ft)': 8.0, 'Vent': 15.0, 'Labor (per hr)': 60.0},
    'Electrical': {'Wire (per ft)': 3.0, 'Outlet': 12.0, 'Labor (per hr)': 55.0},
}

# User authentication (simplified for demo)
if 'user' not in st.session_state:
    st.session_state.user = None
if 'plan' not in st.session_state:
    st.session_state.plan = 'Free'  # Free or Premium

def login():
    st.sidebar.subheader("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        # Replace with real authentication logic
        if username and password:
            st.session_state.user = username
            st.session_state.plan = 'Free'  # Default to Free (extend for Premium logic)
            st.sidebar.success("Logged in!")
        else:
            st.sidebar.error("Invalid credentials")

def logout():
    st.session_state.user = None
    st.session_state.plan = 'Free'
    st.sidebar.success("Logged out!")

# Main app
st.title("Construction Estimating & Management Platform")

if not st.session_state.user:
    login()
    st.write("Please log in to continue.")
else:
    st.sidebar.write(f"Welcome, {st.session_state.user} ({st.session_state.plan} Plan)")
    if st.sidebar.button("Logout"):
        logout()

    # Navigation
    page = st.sidebar.selectbox("Navigate", ["Projects", "Estimating", "Time Tracking", "Invoicing", "Analytics"])

    # Projects Page
    if page == "Projects":
        st.subheader("Project Management")
        project_name = st.text_input("Project Name")
        client_name = st.text_input("Client Name")
        trade = st.selectbox("Trade", ['Plumbing', 'HVAC', 'Electrical'])
        if st.button("Create Project"):
            project_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO projects (id, name, client, trade, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (project_id, project_name, client_name, trade, 'Active', datetime.datetime.now()))
            conn.commit()
            st.success("Project created!")

        # Display projects
        cursor.execute("SELECT * FROM projects WHERE status = 'Active'")
        projects = cursor.fetchall()
        if projects:
            st.write("Active Projects:")
            df = pd.DataFrame(projects, columns=['ID', 'Name', 'Client', 'Trade', 'Status', 'Created At'])
            st.dataframe(df)

    # Estimating Page
    elif page == "Estimating":
        st.subheader("Estimating")
        cursor.execute("SELECT id, name FROM projects")
        projects = cursor.fetchall()
        project_options = {name: id for id, name in projects}
        selected_project = st.selectbox("Select Project", list(project_options.keys()))
        project_id = project_options[selected_project]

        trade = st.selectbox("Trade", ['Plumbing', 'HVAC', 'Electrical'])
        item = st.selectbox("Item", list(COST_DATABASE[trade].keys()))
        quantity = st.number_input("Quantity", min_value=0.0, step=0.1)
        unit_cost = COST_DATABASE[trade][item]

        total_cost = quantity * unit_cost
        st.write(f"Unit Cost: ${unit_cost:.2f} | Total Cost: ${total_cost:.2f}")

        if st.button("Add to Estimate"):
            estimate_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO estimates (id, project_id, item, quantity, unit_cost, total_cost, trade)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (estimate_id, project_id, item, quantity, unit_cost, total_cost, trade))
            conn.commit()
            st.success("Estimate added!")

        # Display estimates for the project
        cursor.execute("SELECT item, quantity, unit_cost, total_cost FROM estimates WHERE project_id = ?", (project_id,))
        estimates = cursor.fetchall()
        if estimates:
            df = pd.DataFrame(estimates, columns=['Item', 'Quantity', 'Unit Cost', 'Total Cost'])
            st.dataframe(df)
            st.write(f"Total Estimate: ${sum([e[3] for e in estimates]):.2f}")

    # Time Tracking Page
    elif page == "Time Tracking":
        st.subheader("Time Tracking (Mobile-Friendly)")
        cursor.execute("SELECT id, name FROM projects")
        projects = cursor.fetchall()
        project_options = {name: id for id, name in projects}
        selected_project = st.selectbox("Select Project", list(project_options.keys()))
        project_id = project_options[selected_project]

        worker = st.text_input("Worker Name")
        hours = st.number_input("Hours Worked", min_value=0.0, step=0.1)
        date = st.date_input("Date", datetime.date.today())

        if st.button("Log Time"):
            log_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO time_logs (id, project_id, worker, hours, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (log_id, project_id, worker, hours, str(date)))
            conn.commit()
            st.success("Time logged!")

        # Display time logs
        cursor.execute("SELECT worker, hours, date FROM time_logs WHERE project_id = ?", (project_id,))
        logs = cursor.fetchall()
        if logs:
            df = pd.DataFrame(logs, columns=['Worker', 'Hours', 'Date'])
            st.dataframe(df)

    # Invoicing Page
    elif page == "Invoicing":
        st.subheader("Invoicing")
        cursor.execute("SELECT id, name FROM projects")
        projects = cursor.fetchall()
        project_options = {name: id for id, name in projects}
        selected_project = st.selectbox("Select Project", list(project_options.keys()))
        project_id = project_options[selected_project]

        # Calculate total from estimates
        cursor.execute("SELECT total_cost FROM estimates WHERE project_id = ?", (project_id,))
        estimates = cursor.fetchall()
        total_amount = sum([e[0] for e in estimates]) if estimates else 0.0

        st.write(f"Estimated Total: ${total_amount:.2f}")
        if st.button("Generate Invoice"):
            invoice_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO invoices (id, project_id, amount, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (invoice_id, project_id, total_amount, 'Pending', datetime.datetime.now()))
            conn.commit()
            st.success("Invoice generated! (Integration with QuickBooks/Xero placeholder)")

        # Display invoices
        cursor.execute("SELECT id, amount, status, created_at FROM invoices WHERE project_id = ?", (project_id,))
        invoices = cursor.fetchall()
        if invoices:
            df = pd.DataFrame(invoices, columns=['ID', 'Amount', 'Status', 'Created At'])
            st.dataframe(df)

    # Analytics Page (Premium Feature)
    elif page == "Analytics":
        st.subheader("Analytics (Premium Feature)")
        if st.session_state.plan == 'Premium':
            st.write("Advanced Analytics Dashboard (Placeholder)")
            # Example: Project cost breakdown
            cursor.execute("SELECT trade, SUM(total_cost) FROM estimates GROUP BY trade")
            data = cursor.fetchall()
            if data:
                df = pd.DataFrame(data, columns=['Trade', 'Total Cost'])
                st.bar_chart(df.set_index('Trade'))
        else:
            st.warning("Upgrade to Premium for advanced analytics.")

# Cleanup
st.write("Note: This is a demo. In production, integrate with QuickBooks/Xero APIs and payment processors.")
