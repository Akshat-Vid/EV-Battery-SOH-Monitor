```python
import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import json
import os
import time
import joblib


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="EV Battery SOH Monitor",
    page_icon="🔋",
    layout="wide"
)


# ============================================================
# LOGIN CREDENTIALS
# ============================================================

USERNAME = "admin"
PASSWORD = "EV@123"


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_NAME = os.path.join(
    BASE_DIR,
    "battery.db"
)

TABLE_NAME = "battery_data"

MODEL_NAME = os.path.join(
    BASE_DIR,
    "xgboost_soh_model.pkl"
)


# ============================================================
# LOGIN PAGE
# ============================================================

def login_page():

    st.markdown(
        """
        <style>

        .login-box {
            max-width: 450px;
            margin: 100px auto;
            padding: 35px;
            border-radius: 15px;
            background-color: #111827;
            border: 1px solid #374151;
        }

        .login-title {
            text-align: center;
            font-size: 32px;
            font-weight: bold;
        }

        .login-subtitle {
            text-align: center;
            color: #9CA3AF;
            margin-bottom: 25px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="login-box">

            <div class="login-title">
                🔋 EV Battery Monitor
            </div>

            <div class="login-subtitle">
                AI-Based Battery State-of-Health System
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    username = st.text_input(
        "Username"
    )

    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button(
        "Login",
        use_container_width=True
    ):

        if username == USERNAME and password == PASSWORD:

            st.session_state.logged_in = True

            st.rerun()

        else:

            st.error(
                "Invalid username or password."
            )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database():

    try:

        conn = sqlite3.connect(DB_NAME)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS battery_data (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                received_at DATETIME
                DEFAULT CURRENT_TIMESTAMP,

                battery_id TEXT,

                cycle INTEGER,

                raw_data TEXT
            )
            """
        )

        conn.commit()
        conn.close()

        return True

    except Exception as e:

        st.error(
            f"Database initialization error: {e}"
        )

        return False


# ============================================================
# INITIALIZE DATABASE
# ============================================================

initialize_database()


# ============================================================
# LOAD AI MODEL
# ============================================================

FEATURES = [

    "Voltage_V",

    "Current_A",

    "Temperature_C",

    "Capacity_Ah",

    "Internal_Resistance_Ohm",

    "Charge_Time_min"

]


MODEL_STATUS = "Offline"
MODEL_ERROR = ""

model = None


try:

    if os.path.exists(MODEL_NAME):

        model = joblib.load(
            MODEL_NAME
        )

        MODEL_STATUS = "Online"

    else:

        MODEL_STATUS = "Offline"

        MODEL_ERROR = (
            "xgboost_soh_model.pkl not found."
        )

except Exception as e:

    MODEL_STATUS = "Offline"

    MODEL_ERROR = str(e)


# ============================================================
# LOAD DATA FROM SQLITE
# ============================================================

def get_data():

    try:

        conn = sqlite3.connect(
            DB_NAME
        )

        query = f"""
        SELECT *
        FROM {TABLE_NAME}
        ORDER BY id DESC
        LIMIT 100
        """

        df = pd.read_sql_query(
            query,
            conn
        )

        conn.close()

        if df.empty:

            return pd.DataFrame()

        # ----------------------------------------------------
        # Convert raw JSON data
        # ----------------------------------------------------

        records = []

        for _, row in df.iterrows():

            try:

                raw = json.loads(
```
