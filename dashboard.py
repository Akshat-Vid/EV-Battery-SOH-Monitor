import streamlit as st
import pandas as pd
import json
import os
import pickle
import time
import sqlite3
from dotenv import load_dotenv
from supabase import create_client


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="EV Battery SOH Monitor",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# SUPABASE CREDENTIALS
# Works on Streamlit Cloud AND locally
# =========================================================

SUPABASE_URL = None
SUPABASE_KEY = None

# First try Streamlit Cloud Secrets
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    pass

# If Cloud Secrets are unavailable, use local .env
if not SUPABASE_URL:
    SUPABASE_URL = os.getenv("SUPABASE_URL")

if not SUPABASE_KEY:
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "battery.db")


# =========================================================
# SUPABASE CONNECTION
# =========================================================

supabase = None
supabase_error = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )
    except Exception as e:
        supabase_error = str(e)
else:
    supabase_error = "Supabase URL or key is missing."


# =========================================================
# TEMPORARY SUPABASE DIAGNOSTIC
# =========================================================

# This does NOT display your actual credentials.
# It only tells us whether Streamlit Cloud received them.

with st.expander("🔧 Connection Diagnostic", expanded=False):

    st.write(
        "SUPABASE URL FOUND:",
        bool(SUPABASE_URL)
    )

    st.write(
        "SUPABASE KEY FOUND:",
        bool(SUPABASE_KEY)
    )

    if supabase is not None:

        try:

            test_result = (
                supabase
                .table("battery_data")
                .select("id")
                .limit(1)
                .execute()
            )

            st.success("Supabase connection successful.")

            st.write(
                "SUPABASE TEST RESULT:",
                test_result.data
            )

        except Exception as e:

            st.error(
                f"SUPABASE ERROR: {e}"
            )

    else:

        st.error(
            f"SUPABASE CONNECTION NOT CREATED: {supabase_error}"
        )


# =========================================================
# LOAD XGBOOST MODEL
# =========================================================

MODEL_PATH = os.path.join(
    BASE_DIR,
    "xgboost_soh_model.pkl"
)

model = None
model_error = None

try:

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

except Exception as e:

    model_error = str(e)


# =========================================================
# LOGIN
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


def login_page():

    st.markdown(
        """
        <div style="text-align:center;">
            <h1>🔋 EV Battery SOH Monitor</h1>
            <p>AI-Based Battery State-of-Health Monitoring System</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        st.subheader("🔐 Login")

        username = st.text_input(
            "Username"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        login_button = st.button(
            "Login",
            use_container_width=True
        )

        if login_button:

            if (
                username == "admin"
                and password == "evbattery123"
            ):

                st.session_state.logged_in = True

                st.rerun()

            else:

                st.error(
                    "Invalid username or password."
                )


# =========================================================
# SQLITE FALLBACK
# =========================================================

def load_sqlite_data():

    try:

        if not os.path.exists(DB_NAME):
            return pd.DataFrame()

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

        return parse_database_data(df)

    except Exception:

        return pd.DataFrame()


# =========================================================
# PARSE DATABASE DATA
# =========================================================

def parse_database_data(df):

    if df.empty:
        return pd.DataFrame()

    records = []

    for _, row in df.iterrows():

        raw = row.get(
            "raw_data",
            {}
        )

        try:

            if isinstance(raw, str):
                raw = json.loads(raw)

            if not isinstance(raw, dict):
                continue

        except Exception:
            continue

        record = {
            "id": row.get("id"),
            "received_at": row.get("received_at"),
            "Battery_ID": raw.get(
                "Battery_ID",
                row.get("battery_id")
            ),
            "Cycle": raw.get(
                "Cycle",
                row.get("cycle")
            ),
            "Voltage_V": raw.get(
                "Voltage_V"
            ),
            "Current_A": raw.get(
                "Current_A"
            ),
            "Temperature_C": raw.get(
                "Temperature_C"
            ),
            "Capacity_Ah": raw.get(
                "Capacity_Ah"
            ),
            "Internal_Resistance_Ohm": raw.get(
                "Internal_Resistance_Ohm"
            ),
            "Charge_Time_min": raw.get(
                "Charge_Time_min"
            ),
            "SOH": raw.get(
                "SOH"
            ),
            "Cooling_ON": raw.get(
                "Cooling_ON",
                False
            ),
            "Load_Reduced": raw.get(
                "Load_Reduced",
                False
            )
        }

        records.append(record)

    if not records:
        return pd.DataFrame()

    result = pd.DataFrame(
        records
    )

    return result


# =========================================================
# LOAD SUPABASE DATA
# =========================================================

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

        data = response.data

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(
            data
        )

        return parse_database_data(df)

    except Exception as e:

        st.session_state.supabase_load_error = str(e)

        return pd.DataFrame()


# =========================================================
# LOAD DATA
# =========================================================

def get_data():

    df = load_supabase_data()

    # Supabase is the primary database.
    # SQLite is only used when Supabase is unavailable.
    if not df.empty:
        return df

    # Local fallback
    local_df = load_sqlite_data()

    return local_df


# =========================================================
# AI SOH PREDICTION
# =========================================================

def predict_soh(row):

    if model is None:
        return None

    try:

        features = pd.DataFrame(
            [[
                float(row["Voltage_V"]),
                float(row["Current_A"]),
                float(row["Temperature_C"]),
                float(row["Capacity_Ah"]),
                float(row["Internal_Resistance_Ohm"]),
                float(row["Charge_Time_min"])
            ]],
            columns=[
                "Voltage_V",
                "Current_A",
                "Temperature_C",
                "Capacity_Ah",
                "Internal_Resistance_Ohm",
                "Charge_Time_min"
            ]
        )

        prediction = model.predict(
            features
        )[0]

        return round(
            float(prediction),
            2
        )

    except Exception:
        return None


# =========================================================
# ALERT GENERATION
# =========================================================

def get_alerts(row, predicted_soh=None):

    alerts = []

    temperature = row.get(
        "Temperature_C"
    )

    voltage = row.get(
        "Voltage_V"
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
                "🔴 CRITICAL: Battery temperature is extremely high."
            )

        elif temperature >= 50:

            alerts.append(
                "🟠 WARNING: Battery temperature is high."
            )

    # Voltage
    if pd.notna(voltage):

        if voltage < 3.0:

            alerts.append(
                "🔴 CRITICAL: Battery voltage is too low."
            )

    # AI SOH
    if predicted_soh is not None:

        if predicted_soh < 75:

            alerts.append(
                "🔴 CRITICAL: Predicted SOH is below 75%."
            )

        elif predicted_soh < 85:

            alerts.append(
                "🟠 WARNING: Predicted SOH is below 85%."
            )

    # Cooling
    if cooling:

        alerts.append(
            "🔵 Cooling system is ON."
        )

    # Load reduction
    if load_reduced:

        alerts.append(
            "🟣 Load reduction is active."
        )

    return alerts


# =========================================================
# MAIN APPLICATION
# =========================================================

if not st.session_state.logged_in:

    login_page()

    st.stop()


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title(
    "🔋 EV SOH Monitor"
)

st.sidebar.markdown(
    "AI-Based EV Battery Monitoring"
)

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "Live Dashboard",
        "AI SOH Prediction",
        "Alerts",
        "Battery History",
        "System Info"
    ]
)

st.sidebar.markdown("---")

if st.sidebar.button(
    "Logout",
    use_container_width=True
):

    st.session_state.logged_in = False

    st.rerun()


# =========================================================
# GET DATA
# =========================================================

df = get_data()


# =========================================================
# NO DATA MESSAGE
# =========================================================

if df.empty:

    st.error(
        "No battery data found in the database."
    )

    st.info(
        "Make sure hivemq_receiver.py and mqtt_publisher.py are running."
    )

    # Show diagnostic information
    if "supabase_load_error" in st.session_state:

        st.error(
            "Supabase read error: "
            + st.session_state.supabase_load_error
        )

    st.stop()


# =========================================================
# CLEAN NUMERIC COLUMNS
# =========================================================

numeric_columns = [
    "Voltage_V",
    "Current_A",
    "Temperature_C",
    "Capacity_Ah",
    "Internal_Resistance_Ohm",
    "Charge_Time_min",
    "SOH",
    "Cycle",
    "Battery_ID"
]

for col in numeric_columns:

    if col in df.columns:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )


# =========================================================
# SORT DATA
# =========================================================

if "id" in df.columns:

    df = df.sort_values(
        "id",
        ascending=True
    )

else:

    df = df.sort_values(
        "Cycle",
        ascending=True
    )


# =========================================================
# LATEST DATA
# =========================================================

latest = df.iloc[-1]


# =========================================================
# LIVE DASHBOARD
# =========================================================

if page == "Live Dashboard":

    st.title(
        "🔋 EV Battery Live Dashboard"
    )

    st.caption(
        "Real-time EV battery monitoring using MQTT, Supabase and AI"
    )

    st.markdown("---")

    # -----------------------------------------------------
    # Latest battery values
    # -----------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Battery ID",
            int(latest["Battery_ID"])
            if pd.notna(latest["Battery_ID"])
            else "N/A"
        )

    with col2:

        st.metric(
            "Cycle",
            int(latest["Cycle"])
            if pd.notna(latest["Cycle"])
            else "N/A"
        )

    with col3:

        temperature = latest[
            "Temperature_C"
        ]

        st.metric(
            "Temperature",
            f"{temperature:.2f} °C"
            if pd.notna(temperature)
            else "N/A"
        )

    with col4:

        voltage = latest[
            "Voltage_V"
        ]

        st.metric(
            "Voltage",
            f"{voltage:.3f} V"
            if pd.notna(voltage)
            else "N/A"
        )

    st.markdown("---")

    # -----------------------------------------------------
    # Electrical parameters
    # -----------------------------------------------------

    st.subheader(
        "⚡ Battery Parameters"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        current = latest[
            "Current_A"
        ]

        st.metric(
            "Current",
            f"{current:.3f} A"
            if pd.notna(current)
            else "N/A"
        )

    with c2:

        capacity = latest[
            "Capacity_Ah"
        ]

        st.metric(
            "Capacity",
            f"{capacity:.3f} Ah"
            if pd.notna(capacity)
            else "N/A"
        )

    with c3:

        resistance = latest[
            "Internal_Resistance_Ohm"
        ]

        st.metric(
            "Internal Resistance",
            f"{resistance:.4f} Ω"
            if pd.notna(resistance)
            else "N/A"
        )

    with c4:

        charge_time = latest[
            "Charge_Time_min"
        ]

        st.metric(
            "Charge Time",
            f"{charge_time:.2f} min"
            if pd.notna(charge_time)
            else "N/A"
        )

    st.markdown("---")

    # -----------------------------------------------------
    # SOH
    # -----------------------------------------------------

    st.subheader(
        "🤖 State of Health"
    )

    predicted = predict_soh(
        latest
    )

    actual_soh = latest.get(
        "SOH"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        if pd.notna(actual_soh):

            st.metric(
                "Actual SOH",
                f"{actual_soh:.2f}%"
            )

        else:

            st.metric(
                "Actual SOH",
                "N/A"
            )

    with c2:

        if predicted is not None:

            st.metric(
                "AI Predicted SOH",
                f"{predicted:.2f}%"
            )

        else:

            st.metric(
                "AI Predicted SOH",
                "N/A"
            )

    with c3:

        if predicted is None:

            status = "UNKNOWN"

        elif predicted >= 85:

            status = "GOOD"

        elif predicted >= 75:

            status = "WARNING"

        else:

            status = "CRITICAL"

        st.metric(
            "Battery Status",
            status
        )

    st.markdown("---")

    # -----------------------------------------------------
    # Alerts
    # -----------------------------------------------------

    alerts = get_alerts(
        latest,
        predicted
    )

    st.subheader(
        "🚨 Current Alerts"
    )

    if alerts:

        for alert in alerts:

            st.warning(
                alert
            )

    else:

        st.success(
            "✅ No abnormal activity detected."
        )

    st.markdown("---")

    # -----------------------------------------------------
    # Temperature chart
    # -----------------------------------------------------

    st.subheader(
        "🌡️ Temperature Trend"
    )

    chart_df = df.tail(100).copy()

    if "Cycle" in chart_df.columns:

        chart_df = chart_df.set_index(
            "Cycle"
        )

    st.line_chart(
        chart_df[
            ["Temperature_C"]
        ]
    )

    # -----------------------------------------------------
    # SOH chart
    # -----------------------------------------------------

    st.subheader(
        "📈 SOH Trend"
    )

    soh_chart = df.tail(100).copy()

    if "Cycle" in soh_chart.columns:

        soh_chart = soh_chart.set_index(
            "Cycle"
        )

    columns = []

    if "SOH" in soh_chart.columns:
        columns.append("SOH")

    predicted_values = []

    for _, row in soh_chart.iterrows():

        predicted_values.append(
            predict_soh(row)
        )

    if predicted_values:

        soh_chart[
            "AI Predicted SOH"
        ] = predicted_values

        columns.append(
            "AI Predicted SOH"
        )

    if columns:

        st.line_chart(
            soh_chart[columns]
        )


# =========================================================
# AI SOH PREDICTION PAGE
# =========================================================

elif page == "AI SOH Prediction":

    st.title(
        "🤖 AI-Based SOH Prediction"
    )

    st.write(
        "The XGBoost model estimates battery State-of-Health "
        "using six battery parameters."
    )

    st.markdown("---")

    if model_error:

        st.error(
            f"Model loading error: {model_error}"
        )

    elif model is None:

        st.error(
            "XGBoost model could not be loaded."
        )

    else:

        st.success(
            "XGBoost model loaded successfully."
        )

        st.subheader(
            "Model Input Parameters"
        )

        input_row = latest

        prediction = predict_soh(
            input_row
        )

        if prediction is not None:

            st.metric(
                "AI Predicted SOH",
                f"{prediction:.2f}%"
            )

            if prediction >= 85:

                st.success(
                    "Battery condition: GOOD"
                )

            elif prediction >= 75:

                st.warning(
                    "Battery condition: WARNING"
                )

            else:

                st.error(
                    "Battery condition: CRITICAL"
                )

        st.markdown("---")

        display_data = {

            "Voltage (V)": latest.get(
                "Voltage_V"
            ),

            "Current (A)": latest.get(
                "Current_A"
            ),

            "Temperature (°C)": latest.get(
                "Temperature_C"
            ),

            "Capacity (Ah)": latest.get(
                "Capacity_Ah"
            ),

            "Internal Resistance (Ω)": latest.get(
                "Internal_Resistance_Ohm"
            ),

            "Charge Time (min)": latest.get(
                "Charge_Time_min"
            )
        }

        st.dataframe(
            pd.DataFrame(
                [display_data]
            ),
            use_container_width=True
        )


# =========================================================
# ALERT PAGE
# =========================================================

elif page == "Alerts":

    st.title(
        "🚨 Battery Alerts"
    )

    alert_records = []

    for _, row in df.tail(200).iterrows():

        prediction = predict_soh(
            row
        )

        alerts = get_alerts(
            row,
            prediction
        )

        for alert in alerts:

            alert_records.append({

                "Battery ID": row.get(
                    "Battery_ID"
                ),

                "Cycle": row.get(
                    "Cycle"
                ),

                "Temperature": row.get(
                    "Temperature_C"
                ),

                "Voltage": row.get(
                    "Voltage_V"
                ),

                "AI SOH": prediction,

                "Alert": alert

            })

    if alert_records:

        alerts_df = pd.DataFrame(
            alert_records
        )

        st.dataframe(
            alerts_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.success(
            "✅ No abnormal activity detected."
        )


# =========================================================
# BATTERY HISTORY
# =========================================================

elif page == "Battery History":

    st.title(
        "📊 Battery History"
    )

    st.write(
        f"Showing latest {min(len(df), 500)} records."
    )

    display_columns = [

        "Battery_ID",
        "Cycle",
        "Voltage_V",
        "Current_A",
        "Temperature_C",
        "Capacity_Ah",
        "Internal_Resistance_Ohm",
        "Charge_Time_min",
        "SOH",
        "Cooling_ON",
        "Load_Reduced"

    ]

    available_columns = [
        col
        for col in display_columns
        if col in df.columns
    ]

    st.dataframe(
        df[
            available_columns
        ].sort_values(
            "Cycle",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# SYSTEM INFORMATION
# =========================================================

elif page == "System Info":

    st.title(
        "ℹ️ System Information"
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
        """,
        language="text"
    )

    st.markdown("---")

    st.subheader(
        "Database Status"
    )

    st.write(
        "Records loaded:",
        len(df)
    )

    st.write(
        "Supabase configured:",
        "Yes" if supabase is not None else "No"
    )

    st.write(
        "AI Model loaded:",
        "Yes" if model is not None else "No"
    )

    st.markdown("---")

    st.subheader(
        "Monitoring Parameters"
    )

    st.write(
        "Temperature warning threshold: 50 °C"
    )

    st.write(
        "Temperature critical threshold: 60 °C"
    )

    st.write(
        "SOH warning threshold: 85%"
    )

    st.write(
        "SOH critical threshold: 75%"
    )


# =========================================================
# AUTO REFRESH
# =========================================================

time.sleep(2)

st.rerun()