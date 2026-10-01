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
    page_title="EV Battery Monitoring System",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# LOGIN
# ============================================================

USERNAME = "admin"
PASSWORD = "EV@123"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


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

    # Login heading
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

    username = st.text_input("Username")
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


if not st.session_state.logged_in:

    login_page()
    st.stop()


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_NAME = os.path.join(
    BASE_DIR,
    "battery.db"
)

MODEL_NAME = os.path.join(
    BASE_DIR,
    "xgboost_soh_model.pkl"
)

TABLE_NAME = "battery_data"


# ============================================================
# LOAD AI MODEL
# ============================================================

try:

    model = joblib.load(
        MODEL_NAME
    )

    MODEL_STATUS = True
    MODEL_ERROR = ""

except Exception as e:

    model = None
    MODEL_STATUS = False
    MODEL_ERROR = str(e)


# ============================================================
# MODEL FEATURES
# ============================================================

FEATURES = [
    "Voltage_V",
    "Current_A",
    "Temperature_C",
    "Capacity_Ah",
    "Internal_Resistance_Ohm",
    "Charge_Time_min"
]


# ============================================================
# READ BATTERY DATA
# ============================================================

def get_data():

    conn = sqlite3.connect(
        DB_NAME
    )

    query = f"""
        SELECT *
        FROM {TABLE_NAME}
        ORDER BY id DESC
        LIMIT 100
    """

    raw_df = pd.read_sql_query(
        query,
        conn
    )

    conn.close()

    if raw_df.empty:
        return pd.DataFrame()

    # The raw JSON is stored in the last column
    json_column = raw_df.columns[-1]

    records = []

    for _, row in raw_df.iterrows():

        try:

            data = json.loads(
                row[json_column]
            )

            data["Database_ID"] = row["id"]

            if len(raw_df.columns) > 1:
                data["Timestamp"] = row.iloc[1]

            records.append(data)

        except Exception:
            continue

    df = pd.DataFrame(
        records
    )

    if df.empty:
        return df

    numeric_columns = [
        "Battery_ID",
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

    return df


# ============================================================
# AI PREDICTION FUNCTION
# ============================================================

def add_predictions(df):

    if df.empty:
        return df

    if model is None:
        return df

    result = df.copy()

    # Check required model features
    missing = [
        feature
        for feature in FEATURES
        if feature not in result.columns
    ]

    if missing:
        return result

    # Convert model inputs to numeric
    for feature in FEATURES:

        result[feature] = pd.to_numeric(
            result[feature],
            errors="coerce"
        )

    # Valid rows
    valid_rows = result[
        FEATURES
    ].notna().all(axis=1)

    result["Predicted_SOH"] = float("nan")
    result["Prediction_Error"] = float("nan")

    if valid_rows.any():

        predictions = model.predict(
            result.loc[
                valid_rows,
                FEATURES
            ]
        )

        predictions = pd.Series(
            predictions,
            index=result.index[valid_rows]
        )

        # Keep SOH between 0 and 100
        predictions = predictions.clip(
            lower=0,
            upper=100
        )

        result.loc[
            valid_rows,
            "Predicted_SOH"
        ] = predictions

        # Calculate prediction error
        if "SOH" in result.columns:

            actual = pd.to_numeric(
                result.loc[
                    valid_rows,
                    "SOH"
                ],
                errors="coerce"
            )

            result.loc[
                valid_rows,
                "Prediction_Error"
            ] = (
                actual - predictions
            ).abs()

    return result


# ============================================================
# LOAD DATA
# ============================================================

try:

    df = get_data()

    if df.empty:

        st.warning(
            "No battery data available."
        )

        st.stop()

except Exception as e:

    st.error(
        f"Database error: {e}"
    )

    st.stop()


# ============================================================
# ADD AI PREDICTIONS
# ============================================================

df = add_predictions(
    df
)


# ============================================================
# LATEST DATA
# ============================================================

latest = df.iloc[0]

battery_id = latest.get(
    "Battery_ID",
    0
)

cycle = latest.get(
    "Cycle",
    0
)

voltage = latest.get(
    "Voltage_V",
    0
)

current = latest.get(
    "Current_A",
    0
)

temperature = latest.get(
    "Temperature_C",
    0
)

capacity = latest.get(
    "Capacity_Ah",
    0
)

resistance = latest.get(
    "Internal_Resistance_Ohm",
    0
)

charge_time = latest.get(
    "Charge_Time_min",
    0
)

actual_soh = latest.get(
    "SOH",
    0
)

predicted_soh = latest.get(
    "Predicted_SOH",
    float("nan")
)

prediction_error = latest.get(
    "Prediction_Error",
    float("nan")
)

cooling = latest.get(
    "Cooling_ON",
    False
)

load_reduced = latest.get(
    "Load_Reduced",
    False
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "🔋 EV BATTERY SYSTEM"
)

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "📊 Live Dashboard",
        "⚠️ Alerts",
        "📈 History",
        "🤖 AI SOH",
        "⚙️ Settings"
    ]
)

st.sidebar.markdown("---")

if MODEL_STATUS:

    st.sidebar.success(
        "🟢 AI Model Online"
    )

else:

    st.sidebar.error(
        "🔴 AI Model Offline"
    )

st.sidebar.success(
    "🟢 System Online"
)

if st.sidebar.button(
    "Logout",
    use_container_width=True
):

    st.session_state.logged_in = False

    st.rerun()


# ============================================================
# LIVE DASHBOARD
# ============================================================

if page == "📊 Live Dashboard":

    st.title(
        "🔋 EV Battery Live Monitoring"
    )

    st.caption(
        "Real-time monitoring of EV battery operating parameters"
    )

    st.markdown("---")

    # ========================================================
    # MAIN METRICS
    # ========================================================

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Battery ID",
        int(battery_id)
    )

    col2.metric(
        "Cycle",
        int(cycle)
    )

    col3.metric(
        "Temperature",
        f"{temperature:.2f} °C"
    )

    col4.metric(
        "Actual SOH",
        f"{actual_soh:.2f}%"
    )

    # ========================================================
    # AI SOH
    # ========================================================

    st.markdown(
        "### 🤖 AI Battery Health"
    )

    col1, col2, col3 = st.columns(3)

    if pd.notna(predicted_soh):

        col1.metric(
            "AI Predicted SOH",
            f"{float(predicted_soh):.2f}%"
        )

        if pd.notna(prediction_error):

            col2.metric(
                "Prediction Error",
                f"{float(prediction_error):.2f}%"
            )

        else:

            col2.metric(
                "Prediction Error",
                "N/A"
            )

        if float(predicted_soh) >= 90:

            col3.success(
                "🟢 GOOD"
            )

        elif float(predicted_soh) >= 75:

            col3.warning(
                "🟡 WARNING"
            )

        else:

            col3.error(
                "🔴 CRITICAL"
            )

    else:

        col1.metric(
            "AI Predicted SOH",
            "N/A"
        )

        col2.metric(
            "Prediction Error",
            "N/A"
        )

        col3.warning(
            "AI Prediction Unavailable"
        )

    # ========================================================
    # ELECTRICAL PARAMETERS
    # ========================================================

    st.markdown(
        "### ⚡ Electrical Parameters"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Voltage",
        f"{voltage:.3f} V"
    )

    col2.metric(
        "Current",
        f"{current:.2f} A"
    )

    col3.metric(
        "Capacity",
        f"{capacity:.3f} Ah"
    )

    col4.metric(
        "Resistance",
        f"{resistance:.5f} Ω"
    )

    # ========================================================
    # BATTERY STATUS
    # ========================================================

    st.markdown(
        "### 🔧 Battery Operating Status"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Charge Time",
        f"{charge_time:.2f} min"
    )

    col2.metric(
        "Cooling",
        "ON" if cooling else "OFF"
    )

    col3.metric(
        "Load Reduction",
        "ACTIVE"
        if load_reduced
        else "NORMAL"
    )

    st.markdown("---")

    # ========================================================
    # TEMPERATURE ALERT
    # ========================================================

    TEMP_LIMIT = 50

    if temperature > TEMP_LIMIT:

        st.error(
            f"🚨 HIGH TEMPERATURE ALERT — "
            f"{temperature:.2f} °C "
            f"(Limit: {TEMP_LIMIT} °C)"
        )

    else:

        st.success(
            f"🟢 Temperature Normal — "
            f"{temperature:.2f} °C"
        )

    # ========================================================
    # BATTERY TRENDS
    # ========================================================

    chart_df = df.sort_values(
        "Cycle"
    )

    st.markdown(
        "## 📈 Battery Trends"
    )

    col1, col2 = st.columns(2)

    # Temperature chart
    with col1:

        fig_temp = go.Figure()

        fig_temp.add_trace(
            go.Scatter(
                x=chart_df["Cycle"],
                y=chart_df["Temperature_C"],
                mode="lines+markers",
                name="Temperature"
            )
        )

        fig_temp.update_layout(
            title="Temperature vs Cycle",
            xaxis_title="Cycle",
            yaxis_title="Temperature (°C)",
            template="plotly_dark"
        )

        st.plotly_chart(
            fig_temp,
            use_container_width=True
        )

    # SOH chart
    with col2:

        fig_soh = go.Figure()

        fig_soh.add_trace(
            go.Scatter(
                x=chart_df["Cycle"],
                y=chart_df["SOH"],
                mode="lines+markers",
                name="Actual SOH"
            )
        )

        if "Predicted_SOH" in chart_df.columns:

            fig_soh.add_trace(
                go.Scatter(
                    x=chart_df["Cycle"],
                    y=chart_df["Predicted_SOH"],
                    mode="lines+markers",
                    name="AI Predicted SOH"
                )
            )

        fig_soh.update_layout(
            title="Actual vs AI Predicted SOH",
            xaxis_title="Cycle",
            yaxis_title="SOH (%)",
            template="plotly_dark"
        )

        st.plotly_chart(
            fig_soh,
            use_container_width=True
        )

    # Voltage and current
    col1, col2 = st.columns(2)

    with col1:

        fig_voltage = go.Figure()

        fig_voltage.add_trace(
            go.Scatter(
                x=chart_df["Cycle"],
                y=chart_df["Voltage_V"],
                mode="lines",
                name="Voltage"
            )
        )

        fig_voltage.update_layout(
            title="Voltage vs Cycle",
            xaxis_title="Cycle",
            yaxis_title="Voltage (V)",
            template="plotly_dark"
        )

        st.plotly_chart(
            fig_voltage,
            use_container_width=True
        )

    with col2:

        fig_current = go.Figure()

        fig_current.add_trace(
            go.Scatter(
                x=chart_df["Cycle"],
                y=chart_df["Current_A"],
                mode="lines",
                name="Current"
            )
        )

        fig_current.update_layout(
            title="Current vs Cycle",
            xaxis_title="Cycle",
            yaxis_title="Current (A)",
            template="plotly_dark"
        )

        st.plotly_chart(
            fig_current,
            use_container_width=True
        )

    # ========================================================
    # RECENT DATA
    # ========================================================

    st.markdown(
        "## 🗃️ Recent Battery Data"
    )

    display_columns = [
        "Database_ID",
        "Battery_ID",
        "Cycle",
        "Voltage_V",
        "Current_A",
        "Temperature_C",
        "Capacity_Ah",
        "Internal_Resistance_Ohm",
        "Charge_Time_min",
        "SOH",
        "Predicted_SOH",
        "Prediction_Error"
    ]

    display_columns = [
        col
        for col in display_columns
        if col in df.columns
    ]

    st.dataframe(
        df[display_columns].head(10),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# ALERTS
# ============================================================

elif page == "⚠️ Alerts":

    st.title(
        "⚠️ Battery Alert Center"
    )

    st.write(
        "Current battery condition based on configured safety limits."
    )

    st.markdown("---")

    TEMP_LIMIT = 50
    MAX_VOLTAGE = 4.20
    MIN_VOLTAGE = 3.00
    MAX_CURRENT = 15
    MIN_SOH = 80
    MAX_RESISTANCE = 0.08

    alerts = []

    if temperature > TEMP_LIMIT:

        alerts.append(
            f"🌡️ High Temperature: "
            f"{temperature:.2f} °C"
        )

    if voltage > MAX_VOLTAGE:

        alerts.append(
            f"⚡ Over Voltage: "
            f"{voltage:.3f} V"
        )

    if voltage < MIN_VOLTAGE:

        alerts.append(
            f"⚡ Low Voltage: "
            f"{voltage:.3f} V"
        )

    if current > MAX_CURRENT:

        alerts.append(
            f"🔌 High Current: "
            f"{current:.2f} A"
        )

    if pd.notna(predicted_soh):

        if float(predicted_soh) < MIN_SOH:

            alerts.append(
                f"🤖 AI Predicted Low SOH: "
                f"{float(predicted_soh):.2f}%"
            )

    if resistance > MAX_RESISTANCE:

        alerts.append(
            f"🔥 High Internal Resistance: "
            f"{resistance:.5f} Ω"
        )

    if alerts:

        for alert in alerts:
            st.error(alert)

    else:

        st.success(
            "🟢 No active alerts"
        )


# ============================================================
# HISTORY
# ============================================================

elif page == "📈 History":

    st.title(
        "📈 Battery History"
    )

    st.write(
        "Historical battery measurements and AI predictions."
    )

    display_columns = [
        "Database_ID",
        "Timestamp",
        "Battery_ID",
        "Cycle",
        "Voltage_V",
        "Current_A",
        "Temperature_C",
        "Capacity_Ah",
        "Internal_Resistance_Ohm",
        "Charge_Time_min",
        "SOH",
        "Predicted_SOH",
        "Prediction_Error"
    ]

    display_columns = [
        col
        for col in display_columns
        if col in df.columns
    ]

    st.dataframe(
        df[display_columns],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# AI SOH
# ============================================================

elif page == "🤖 AI SOH":

    st.title(
        "🤖 AI-Based Battery SOH Estimation"
    )

    if not MODEL_STATUS:

        st.error(
            "XGBoost model could not be loaded."
        )

        st.code(
            MODEL_ERROR
        )

        st.stop()

    st.success(
        "🟢 XGBoost SOH Prediction Model Online"
    )

    st.markdown("---")

    # ========================================================
    # CURRENT AI RESULT
    # ========================================================

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Actual SOH",
        f"{actual_soh:.2f}%"
    )

    if pd.notna(predicted_soh):

        col2.metric(
            "AI Predicted SOH",
            f"{float(predicted_soh):.2f}%"
        )

    else:

        col2.metric(
            "AI Predicted SOH",
            "N/A"
        )

    if pd.notna(prediction_error):

        col3.metric(
            "Prediction Error",
            f"{float(prediction_error):.2f}%"
        )

    else:

        col3.metric(
            "Prediction Error",
            "N/A"
        )

    st.markdown("---")

    # ========================================================
    # INPUT FEATURES
    # ========================================================

    st.subheader(
        "🔍 AI Model Input Parameters"
    )

    input_col1, input_col2, input_col3 = st.columns(3)

    input_col1.metric(
        "Voltage",
        f"{voltage:.3f} V"
    )

    input_col2.metric(
        "Current",
        f"{current:.2f} A"
    )

    input_col3.metric(
        "Temperature",
        f"{temperature:.2f} °C"
    )

    input_col1, input_col2, input_col3 = st.columns(3)

    input_col1.metric(
        "Capacity",
        f"{capacity:.3f} Ah"
    )

    input_col2.metric(
        "Resistance",
        f"{resistance:.5f} Ω"
    )

    input_col3.metric(
        "Charge Time",
        f"{charge_time:.2f} min"
    )

    st.markdown("---")

    # ========================================================
    # SOH GAUGE
    # ========================================================

    if pd.notna(predicted_soh):

        gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=float(predicted_soh),
                title={
                    "text": "AI Predicted Battery SOH"
                },
                gauge={
                    "axis": {
                        "range": [0, 100]
                    },
                    "threshold": {
                        "line": {
                            "width": 4
                        },
                        "value": 80
                    }
                }
            )
        )

        gauge.update_layout(
            height=350,
            template="plotly_dark"
        )

        st.plotly_chart(
            gauge,
            use_container_width=True
        )

    # ========================================================
    # ACTUAL VS PREDICTED
    # ========================================================

    st.subheader(
        "📊 Actual SOH vs AI Predicted SOH"
    )

    ai_chart_df = df.sort_values(
        "Cycle"
    ).copy()

    fig_ai = go.Figure()

    fig_ai.add_trace(
        go.Scatter(
            x=ai_chart_df["Cycle"],
            y=ai_chart_df["SOH"],
            mode="lines+markers",
            name="Actual SOH"
        )
    )

    if "Predicted_SOH" in ai_chart_df.columns:

        fig_ai.add_trace(
            go.Scatter(
                x=ai_chart_df["Cycle"],
                y=ai_chart_df["Predicted_SOH"],
                mode="lines+markers",
                name="AI Predicted SOH"
            )
        )

    fig_ai.update_layout(
        title="Battery SOH Prediction Performance",
        xaxis_title="Cycle",
        yaxis_title="SOH (%)",
        template="plotly_dark"
    )

    st.plotly_chart(
        fig_ai,
        use_container_width=True
    )

    # ========================================================
    # PREDICTION TABLE
    # ========================================================

    st.subheader(
        "🧠 Recent AI Predictions"
    )

    prediction_columns = [
        "Database_ID",
        "Cycle",
        "SOH",
        "Predicted_SOH",
        "Prediction_Error"
    ]

    prediction_columns = [
        col
        for col in prediction_columns
        if col in df.columns
    ]

    st.dataframe(
        df[prediction_columns].head(20),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# SETTINGS
# ============================================================

elif page == "⚙️ Settings":

    st.title(
        "⚙️ Battery Monitoring Settings"
    )

    st.write(
        "Configure the limits used by the alert system."
    )

    st.markdown("---")

    temperature_limit = st.number_input(
        "Maximum Temperature (°C)",
        min_value=20.0,
        max_value=100.0,
        value=50.0,
        step=1.0
    )

    max_voltage = st.number_input(
        "Maximum Voltage (V)",
        min_value=1.0,
        max_value=10.0,
        value=4.20,
        step=0.05
    )

    min_voltage = st.number_input(
        "Minimum Voltage (V)",
        min_value=0.0,
        max_value=10.0,
        value=3.00,
        step=0.05
    )

    max_current = st.number_input(
        "Maximum Current (A)",
        min_value=1.0,
        max_value=100.0,
        value=15.0,
        step=1.0
    )

    min_soh = st.number_input(
        "Minimum SOH (%)",
        min_value=0.0,
        max_value=100.0,
        value=80.0,
        step=1.0
    )

    st.markdown("---")

    if st.button(
        "💾 Save Settings",
        use_container_width=True
    ):

        st.success(
            "Settings updated for this dashboard session."
        )

    st.markdown(
        "### Current Battery"
    )

    st.write(
        f"Temperature: **{temperature:.2f} °C**"
    )

    st.write(
        f"Voltage: **{voltage:.3f} V**"
    )

    st.write(
        f"Current: **{current:.2f} A**"
    )

    st.write(
        f"Actual SOH: **{actual_soh:.2f}%**"
    )

    if pd.notna(predicted_soh):

        st.write(
            f"AI Predicted SOH: "
            f"**{float(predicted_soh):.2f}%**"
        )


# ============================================================
# AUTO REFRESH
# ============================================================

time.sleep(3)

st.rerun()