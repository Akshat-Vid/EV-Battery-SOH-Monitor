import sqlite3
import json
import time
import joblib
import pandas as pd

# ============================================================
# CONFIGURATION
# ============================================================

DB_FILE = "battery.db"
MODEL_FILE = "xgboost_soh_model.pkl"

FEATURES = [
    "Voltage_V",
    "Current_A",
    "Temperature_C",
    "Capacity_Ah",
    "Internal_Resistance_Ohm",
    "Charge_Time_min"
]

# ============================================================
# LOAD XGBOOST MODEL
# ============================================================

print("========================================")
print(" AI-Based EV Battery SOH Prediction")
print("========================================")

print("\nLoading XGBoost model...")

try:
    model = joblib.load(MODEL_FILE)
    print("XGBoost model loaded successfully!")

except Exception as e:
    print("ERROR: Could not load XGBoost model.")
    print("Reason:", e)
    exit()

# ============================================================
# CHECK DATABASE
# ============================================================

try:
    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name='battery_data'
    """)

    table = cursor.fetchone()

    conn.close()

    if table is None:
        print("\nERROR: battery_data table does not exist.")
        print("Start the MQTT subscriber first.")
        exit()

except Exception as e:
    print("\nERROR: Could not open SQLite database.")
    print("Reason:", e)
    exit()

print("SQLite database connected successfully!")

print("\nWaiting for live battery data...")
print("Press CTRL + C to stop.\n")

# ============================================================
# LIVE DATA LOOP
# ============================================================

last_id = 0

while True:

    try:

        # ----------------------------------------------------
        # CONNECT TO SQLITE
        # ----------------------------------------------------

        conn = sqlite3.connect(DB_FILE)

        query = """
            SELECT id, received_at, raw_data
            FROM battery_data
            WHERE id > ?
            ORDER BY id ASC
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=(last_id,)
        )

        conn.close()

        # ----------------------------------------------------
        # PROCESS NEW RECORDS
        # ----------------------------------------------------

        if not df.empty:

            for _, database_row in df.iterrows():

                try:

                    # Get database information
                    database_id = int(database_row["id"])
                    received_at = database_row["received_at"]

                    # ------------------------------------------------
                    # CONVERT JSON TO PYTHON DICTIONARY
                    # ------------------------------------------------

                    data = json.loads(database_row["raw_data"])

                    # ------------------------------------------------
                    # CHECK REQUIRED PARAMETERS
                    # ------------------------------------------------

                    missing_features = [
                        feature
                        for feature in FEATURES
                        if feature not in data
                    ]

                    if missing_features:

                        print("\nERROR: Missing battery parameters:")
                        print(missing_features)

                        last_id = database_id
                        continue

                    # ------------------------------------------------
                    # CREATE MODEL INPUT
                    # ------------------------------------------------

                    input_data = pd.DataFrame([data])

                    X_live = input_data[FEATURES]

                    # ------------------------------------------------
                    # AI PREDICTION
                    # ------------------------------------------------

                    predicted_soh = model.predict(X_live)[0]

                    # Keep SOH between 0 and 100
                    predicted_soh = max(
                        0,
                        min(100, predicted_soh)
                    )

                    # ------------------------------------------------
                    # GET ACTUAL SOH
                    # ------------------------------------------------

                    actual_soh = data.get("SOH", None)

                    # ------------------------------------------------
                    # CALCULATE ERROR
                    # ------------------------------------------------

                    if actual_soh is not None:

                        prediction_difference = abs(
                            float(actual_soh) -
                            float(predicted_soh)
                        )

                    else:

                        prediction_difference = None

                    # ------------------------------------------------
                    # BATTERY HEALTH STATUS
                    # ------------------------------------------------

                    if predicted_soh >= 90:

                        status = "GOOD"

                    elif predicted_soh >= 75:

                        status = "WARNING"

                    else:

                        status = "CRITICAL"

                    # ------------------------------------------------
                    # TEMPERATURE STATUS
                    # ------------------------------------------------

                    temperature = float(
                        data["Temperature_C"]
                    )

                    if temperature >= 45:

                        temperature_status = "HIGH TEMPERATURE"

                    elif temperature >= 40:

                        temperature_status = "WARNING"

                    else:

                        temperature_status = "NORMAL"

                    # =================================================
                    # DISPLAY LIVE DATA
                    # =================================================

                    print("\n")
                    print("========================================")
                    print("       LIVE EV BATTERY DATA")
                    print("========================================")

                    print(
                        f"Database ID    : {database_id}"
                    )

                    print(
                        f"Received At    : {received_at}"
                    )

                    print(
                        f"Battery ID     : "
                        f"{int(data['Battery_ID'])}"
                    )

                    print(
                        f"Cycle          : "
                        f"{int(data['Cycle'])}"
                    )

                    print("----------------------------------------")

                    print(
                        f"Voltage        : "
                        f"{float(data['Voltage_V']):.3f} V"
                    )

                    print(
                        f"Current        : "
                        f"{float(data['Current_A']):.3f} A"
                    )

                    print(
                        f"Temperature    : "
                        f"{temperature:.2f} °C"
                    )

                    print(
                        f"Capacity       : "
                        f"{float(data['Capacity_Ah']):.3f} Ah"
                    )

                    print(
                        f"Resistance     : "
                        f"{float(data['Internal_Resistance_Ohm']):.5f} Ω"
                    )

                    print(
                        f"Charge Time    : "
                        f"{float(data['Charge_Time_min']):.2f} min"
                    )

                    print("----------------------------------------")

                    print(
                        f"Actual SOH     : "
                        f"{float(actual_soh):.2f}%"
                        if actual_soh is not None
                        else "Actual SOH     : N/A"
                    )

                    print(
                        f"AI Predicted SOH: "
                        f"{predicted_soh:.2f}%"
                    )

                    if prediction_difference is not None:

                        print(
                            f"Prediction Error: "
                            f"{prediction_difference:.2f}%"
                        )

                    print("----------------------------------------")

                    print(
                        f"Battery Status : {status}"
                    )

                    print(
                        f"Temperature    : {temperature_status}"
                    )

                    print("========================================")

                    # ------------------------------------------------
                    # UPDATE LAST PROCESSED DATABASE ID
                    # ------------------------------------------------

                    last_id = database_id

                except json.JSONDecodeError:

                    print(
                        "\nERROR: Invalid JSON received from MQTT."
                    )

                    last_id = int(database_row["id"])

                except Exception as e:

                    print(
                        "\nERROR processing battery data:"
                    )

                    print(e)

                    last_id = int(database_row["id"])

        # ----------------------------------------------------
        # WAIT BEFORE CHECKING DATABASE AGAIN
        # ----------------------------------------------------

        time.sleep(1)

    # ========================================================
    # STOP PROGRAM
    # ========================================================

    except KeyboardInterrupt:

        print("\n")
        print("========================================")
        print("Live SOH prediction stopped.")
        print("========================================")

        break

    # ========================================================
    # DATABASE ERROR
    # ========================================================

    except sqlite3.Error as e:

        print("\nSQLite database error:")
        print(e)

        time.sleep(2)

    # ========================================================
    # OTHER ERROR
    # ========================================================

    except Exception as e:

        print("\nUnexpected error:")
        print(e)

        time.sleep(2)