import streamlit as st
import pandas as pd
import json
import os
import pickle
import time
import sqlite3

from dotenv import load_dotenv
from supabase import create_client


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="EV Battery Intelligence",
    page_icon="🔋",
    layout="wide"
)


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================
load_dotenv()

# ---------------------------------------------------------
# SUPABASE CREDENTIALS
# Works locally and on Streamlit Cloud
# ---------------------------------------------------------

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")


DB_NAME = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "battery.db"
)

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "xgboost_soh_model.pkl"
)


# ============================================================
# SUPABASE CONNECTION
# ============================================================

supabase = None
supabase_status = False

try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )
        supabase_status = True
except Exception:
    supabase = None
    supabase_status = False


# ============================================================
# LOGIN
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


def login_page():

    st.title("🔋 EV Battery Intelligence")

    st.subheader("Secure Login")

    st.write(
        "AI Based Electric Vehicle Battery "
        "State-of-Health Monitoring System"
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

        if username == "admin" and password == "evbattery123":

            st.session_state.logged_in = True
            st.rerun()

        else:

            st.error(
                "Invalid username or password."
            )


# ============================================================
# SUPABASE DATA LOADER
# ============================================================

@st.cache_data(ttl=1)
def load_supabase_data():

    if supabase is None:
        return pd.DataFrame()

    try:

        response = (
            supabase
            .table("battery_data")
            .select(
                "id,received_at,battery_id,cycle,raw_data"
            )
            .order(
                "id",
                desc=True
            )
            .limit(500)
            .execute()
        )

        rows = response.data

        if not rows:
            return pd.DataFrame()

        records = []

        for row in rows:

            raw = row.get("raw_data", {})

            if isinstance(raw, str):

                try:
                    raw = json.loads(raw)

                except Exception:
                    raw = {}

            record = {
                "id": row.get("id"),
                "received_at": row.get("received_at"),
                "battery_id": row.get("battery_id"),
                "cycle": row.get("cycle")
            }

            if isinstance(raw, dict):
                record.update(raw)

            records.append(record)

        df = pd.DataFrame(records)

        return df

    except Exception as e:

        st.error(
            f"Supabase database error: {e}"
        )

        return pd.DataFrame()


# ============================================================
# SQLITE FALLBACK
# ============================================================

def load_sqlite_data():

    if not os.path.exists(DB_NAME):

        return pd.DataFrame()

    try:

        conn = sqlite3.connect(
            DB_NAME
        )

        query = """
        SELECT
            id,
            received_at,
            battery_id,
            cycle,
            raw_data
        FROM battery_data
        ORDER BY id DESC
        LIMIT 500
        """

        df = pd.read_sql_query(
            query,
            conn
        )

        conn.close()

        if df.empty:
            return pd.DataFrame()

        records = []

        for _, row in df.iterrows():

            raw = row["raw_data"]

            try:

                if isinstance(raw, str):
                    raw = json.loads(raw)

            except Exception:

                raw = {}

            record = {
                "id": row["id"],
                "received_at": row["received_at"],
                "battery_id": row["battery_id"],
                "cycle": row["cycle"]
            }

            if isinstance(raw, dict):
                record.update(raw)

            records.append(record)

        return pd.DataFrame(records)

    except Exception:

        return pd.DataFrame()


# ============================================================
# MAIN DATA LOADER
# ============================================================

def load_data():

    # Try Supabase first

    if supabase_status:

        df = load_supabase_data()

        if not df.empty:

            return df, "Supabase Cloud"

    # Local fallback

    df = load_sqlite_data()

    if not df.empty:

        return df, "Local SQLite"

    return pd.DataFrame(), "No Data"


# ============================================================
# LOAD AI MODEL
# ============================================================

@st.cache_resource
def load_model():

    try:

        with open(
            MODEL_PATH,
            "rb"
        ) as file:

            model = pickle.load(file)

        return model

    except Exception as e:

        st.error(
            f"Unable to load AI model: {e}"
        )

        return None


# ============================================================
# AI SOH PREDICTION
# ============================================================

def predict_soh(df):

    model = load_model()

    if model is None:

        return df

    required_features = [

        "Voltage_V",
        "Current_A",
        "Temperature_C",
        "Capacity_Ah",
        "Internal_Resistance_Ohm",
        "Charge_Time_min"

    ]

    for column in required_features:

        if column not in df.columns:

            return df

    try:

        X = df[required_features].copy()

        df["AI_Predicted_SOH"] = model.predict(X)

        df["AI_Predicted_SOH"] = (
            df["AI_Predicted_SOH"]
            .clip(0, 100)
        )

    except Exception as e:

        st.warning(
            f"AI prediction unavailable: {e}"
        )

    return df


# ============================================================
# ALERT GENERATION
# ============================================================

def generate_alerts(row):

    alerts = []

    temperature = row.get(
        "Temperature_C",
        None
    )

    voltage = row.get(
        "Voltage_V",
        None
    )

    predicted_soh = row.get(
        "AI_Predicted_SOH",
        None
    )

    cooling = row.get(
        "Cooling_ON",
        False
    )

    load_reduced = row.get(
        "Load_Reduced",
        False
    )

    # Temperature

    if pd.notna(temperature):

        if temperature >= 60:

            alerts.append(
                (
                    "CRITICAL",
                    f"Battery temperature is {temperature:.2f} °C"
                )
            )

        elif temperature >= 50:

            alerts.append(
                (
                    "WARNING",
                    f"High battery temperature: {temperature:.2f} °C"
                )
            )

    # Voltage

    if pd.notna(voltage):

        if voltage < 3.0:

            alerts.append(
                (
                    "CRITICAL",
                    f"Low battery voltage: {voltage:.3f} V"
                )
            )

    # SOH

    if pd.notna(predicted_soh):

        if predicted_soh < 75:

            alerts.append(
                (
                    "CRITICAL",
                    f"Predicted SOH is {predicted_soh:.2f}%"
                )
            )

    # Cooling

    if cooling:

        alerts.append(
            (
                "ACTION",
                "Cooling system is ON"
            )
        )

    # Load reduction

    if load_reduced:

        alerts.append(
            (
                "ACTION",
                "Battery load has been reduced"
            )
        )

    return alerts


# ============================================================
# DASHBOARD
# ============================================================

def dashboard():

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    st.title(
        "🔋 EV Battery Intelligence Dashboard"
    )

    st.caption(
        "AI Based EV Battery State-of-Health "
        "Estimation & Real-Time Monitoring"
    )

    # --------------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------------

    st.sidebar.title(
        "Navigation"
    )

    page = st.sidebar.radio(
        "Select Page",
        [
            "Live Dashboard",
            "AI SOH Prediction",
            "Alerts",
            "Battery History",
            "System Info"
        ]
    )

    st.sidebar.divider()

    if st.sidebar.button(
        "Logout",
        use_container_width=True
    ):

        st.session_state.logged_in = False
        st.rerun()

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    df, data_source = load_data()

    if df.empty:

        st.warning(
            "No battery data available yet."
        )

        st.info(
            "Make sure hivemq_receiver.py is running "
            "and Supabase is receiving data."
        )

        return

    # --------------------------------------------------------
    # CONVERT NUMERIC COLUMNS
    # --------------------------------------------------------

    numeric_columns = [

        "Cycle",
        "Voltage_V",
        "Current_A",
        "Temperature_C",
        "Capacity_Ah",
        "Internal_Resistance_Ohm",
        "Charge_Time_min",
        "SOH"

    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # --------------------------------------------------------
    # AI PREDICTION
    # --------------------------------------------------------

    df = predict_soh(df)

    # ========================================================
    # LIVE DASHBOARD
    # ========================================================

    if page == "Live Dashboard":

        st.header(
            "📡 Live Battery Monitoring"
        )

        latest = df.iloc[0]

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        temperature = latest.get(
            "Temperature_C",
            0
        )

        predicted_soh = latest.get(
            "AI_Predicted_SOH",
            None
        )

        if temperature >= 60:

            status = "🔴 CRITICAL"

        elif temperature >= 50:

            status = "🟠 WARNING"

        elif (
            pd.notna(predicted_soh)
            and predicted_soh < 75
        ):

            status = "🔴 LOW SOH"

        else:

            status = "🟢 GOOD"

        st.success(
            f"System Status: {status}"
        )

        st.caption(
            f"Data Source: {data_source}"
        )

        # ----------------------------------------------------
        # PRIMARY METRICS
        # ----------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.metric(
                "🔋 Battery ID",
                str(
                    latest.get(
                        "Battery_ID",
                        latest.get(
                            "battery_id",
                            "-"
                        )
                    )
                )
            )

        with col2:

            st.metric(
                "🔄 Cycle",
                f"{int(latest['Cycle'])}"
                if pd.notna(
                    latest.get("Cycle")
                )
                else "-"
            )

        with col3:

            st.metric(
                "🌡️ Temperature",
                f"{latest['Temperature_C']:.2f} °C"
                if pd.notna(
                    latest.get("Temperature_C")
                )
                else "-"
            )

        with col4:

            st.metric(
                "💚 Actual SOH",
                f"{latest['SOH']:.2f}%"
                if pd.notna(
                    latest.get("SOH")
                )
                else "-"
            )

        # ----------------------------------------------------
        # SECONDARY METRICS
        # ----------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.metric(
                "⚡ Voltage",
                f"{latest['Voltage_V']:.3f} V"
                if pd.notna(
                    latest.get("Voltage_V")
                )
                else "-"
            )

        with col2:

            st.metric(
                "🔌 Current",
                f"{latest['Current_A']:.2f} A"
                if pd.notna(
                    latest.get("Current_A")
                )
                else "-"
            )

        with col3:

            st.metric(
                "🔋 Capacity",
                f"{latest['Capacity_Ah']:.3f} Ah"
                if pd.notna(
                    latest.get("Capacity_Ah")
                )
                else "-"
            )

        with col4:

            st.metric(
                "🤖 AI Predicted SOH",
                f"{predicted_soh:.2f}%"
                if pd.notna(predicted_soh)
                else "-"
            )

        # ----------------------------------------------------
        # THIRD ROW
        # ----------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            resistance = latest.get(
                "Internal_Resistance_Ohm",
                None
            )

            st.metric(
                "Resistance",
                f"{resistance:.5f} Ω"
                if pd.notna(resistance)
                else "-"
            )

        with col2:

            charge_time = latest.get(
                "Charge_Time_min",
                None
            )

            st.metric(
                "Charge Time",
                f"{charge_time:.2f} min"
                if pd.notna(charge_time)
                else "-"
            )

        with col3:

            cooling = latest.get(
                "Cooling_ON",
                False
            )

            st.metric(
                "Cooling",
                "ON" if cooling else "OFF"
            )

        with col4:

            load_reduced = latest.get(
                "Load_Reduced",
                False
            )

            st.metric(
                "Load Reduced",
                "YES" if load_reduced else "NO"
            )

        # ----------------------------------------------------
        # ALERT
        # ----------------------------------------------------

        alerts = generate_alerts(
            latest
        )

        if alerts:

            st.subheader(
                "🚨 Current Alerts"
            )

            for level, message in alerts:

                if level == "CRITICAL":

                    st.error(
                        f"🔴 {message}"
                    )

                elif level == "WARNING":

                    st.warning(
                        f"🟠 {message}"
                    )

                else:

                    st.info(
                        f"🔵 {message}"
                    )

        # ----------------------------------------------------
        # CHARTS
        # ----------------------------------------------------

        st.subheader(
            "📊 Live Battery Parameters"
        )

        chart_df = (
            df
            .sort_values("id")
            .tail(100)
            .copy()
        )

        if "Temperature_C" in chart_df:

            st.line_chart(
                chart_df.set_index("id")[
                    ["Temperature_C"]
                ]
            )

        if "Voltage_V" in chart_df:

            st.line_chart(
                chart_df.set_index("id")[
                    ["Voltage_V"]
                ]
            )

        if "Current_A" in chart_df:

            st.line_chart(
                chart_df.set_index("id")[
                    ["Current_A"]
                ]
            )

        if (
            "SOH" in chart_df
            and "AI_Predicted_SOH" in chart_df
        ):

            st.line_chart(
                chart_df.set_index("id")[
                    [
                        "SOH",
                        "AI_Predicted_SOH"
                    ]
                ]
            )

        # ----------------------------------------------------
        # RECENT DATA
        # ----------------------------------------------------

        st.subheader(
            "📋 Recent Battery Data"
        )

        display_columns = [

            "received_at",
            "Battery_ID",
            "Cycle",
            "Voltage_V",
            "Current_A",
            "Temperature_C",
            "Capacity_Ah",
            "Internal_Resistance_Ohm",
            "Charge_Time_min",
            "SOH",
            "AI_Predicted_SOH"

        ]

        display_columns = [
            c for c in display_columns
            if c in df.columns
        ]

        st.dataframe(
            df[display_columns].head(20),
            use_container_width=True
        )

    # ========================================================
    # AI SOH PAGE
    # ========================================================

    elif page == "AI SOH Prediction":

        st.header(
            "🤖 AI Based SOH Prediction"
        )

        st.write(
            "The XGBoost machine-learning model "
            "uses battery operating parameters "
            "to estimate State-of-Health."
        )

        if "AI_Predicted_SOH" in df.columns:

            latest = df.iloc[0]

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Actual SOH",
                    f"{latest['SOH']:.2f}%"
                )

            with col2:

                st.metric(
                    "AI Predicted SOH",
                    f"{latest['AI_Predicted_SOH']:.2f}%"
                )

            with col3:

                difference = (
                    latest["AI_Predicted_SOH"]
                    - latest["SOH"]
                )

                st.metric(
                    "Prediction Difference",
                    f"{difference:+.2f}%"
                )

            st.subheader(
                "SOH Prediction History"
            )

            history = (
                df
                .sort_values("id")
                .tail(200)
            )

            st.line_chart(
                history.set_index("id")[
                    [
                        "SOH",
                        "AI_Predicted_SOH"
                    ]
                ]
            )

            st.subheader(
                "AI Input Parameters"
            )

            input_columns = [

                "Voltage_V",
                "Current_A",
                "Temperature_C",
                "Capacity_Ah",
                "Internal_Resistance_Ohm",
                "Charge_Time_min"

            ]

            available = [
                c for c in input_columns
                if c in latest.index
            ]

            st.dataframe(
                pd.DataFrame(
                    {
                        "Parameter": available,
                        "Value": [
                            latest[c]
                            for c in available
                        ]
                    }
                ),
                use_container_width=True
            )

    # ========================================================
    # ALERTS PAGE
    # ========================================================

    elif page == "Alerts":

        st.header(
            "🚨 Battery Alerts"
        )

        alert_records = []

        for _, row in df.iterrows():

            row_alerts = generate_alerts(
                row
            )

            for level, message in row_alerts:

                alert_records.append(
                    {
                        "Time": row.get(
                            "received_at",
                            ""
                        ),
                        "Battery": row.get(
                            "Battery_ID",
                            row.get(
                                "battery_id",
                                ""
                            )
                        ),
                        "Cycle": row.get(
                            "Cycle",
                            ""
                        ),
                        "Level": level,
                        "Alert": message
                    }
                )

        if alert_records:

            alerts_df = pd.DataFrame(
                alert_records
            )

            st.dataframe(
                alerts_df,
                use_container_width=True
            )

        else:

            st.success(
                "No abnormal activity detected."
            )

    # ========================================================
    # HISTORY PAGE
    # ========================================================

    elif page == "Battery History":

        st.header(
            "📚 Battery History"
        )

        st.write(
            "Historical battery measurements "
            "received through the MQTT pipeline."
        )

        st.dataframe(
            df,
            use_container_width=True
        )

    # ========================================================
    # SYSTEM INFO
    # ========================================================

    elif page == "System Info":

        st.header(
            "⚙️ System Information"
        )

        st.subheader(
            "Project Architecture"
        )

        st.code(
            """
Synthetic Battery Data
        ↓
MQTT Publisher
        ↓
HiveMQ Cloud
        ↓
MQTT Receiver
        ↓
Supabase Cloud Database
        ↓
XGBoost AI Model
        ↓
Streamlit Dashboard
        ↓
Real-Time Alerts
            """
        )

        st.subheader(
            "Database Status"
        )

        if supabase_status:

            st.success(
                "Supabase: Connected"
            )

        else:

            st.error(
                "Supabase: Not Connected"
            )

        st.write(
            f"Local SQLite Database: "
            f"{'Available' if os.path.exists(DB_NAME) else 'Not Found'}"
        )

        st.subheader(
            "AI Model"
        )

        if os.path.exists(MODEL_PATH):

            st.success(
                "XGBoost model loaded."
            )

        else:

            st.error(
                "XGBoost model not found."
            )

        st.subheader(
            "Data Statistics"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Records Loaded",
                len(df)
            )

        with col2:

            if "Battery_ID" in df.columns:

                batteries = df["Battery_ID"].nunique()

            elif "battery_id" in df.columns:

                batteries = df["battery_id"].nunique()

            else:

                batteries = 0

            st.metric(
                "Batteries",
                batteries
            )

        with col3:

            if "Cycle" in df.columns:

                max_cycle = df["Cycle"].max()

                st.metric(
                    "Latest Cycle",
                    int(max_cycle)
                    if pd.notna(max_cycle)
                    else "-"
                )


# ============================================================
# RUN APPLICATION
# ============================================================

if not st.session_state.logged_in:

    login_page()

else:

    dashboard()

    # --------------------------------------------------------
    # AUTO REFRESH
    # --------------------------------------------------------

    time.sleep(2)

    st.rerun()