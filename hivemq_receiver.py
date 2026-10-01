import paho.mqtt.client as mqtt
import sqlite3
import json
import csv
import os


# =========================================================
# HiveMQ Cloud Configuration
# =========================================================

BROKER = "2ed599332c774488978838f91633b9db.s1.eu.hivemq.cloud"
PORT = 8883

USERNAME = "EV"
PASSWORD = "Iaj@4793"

TOPIC = "ev/battery/data"


# =========================================================
# File Paths
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(BASE_DIR, "battery.db")

CSV_DIR = os.path.join(BASE_DIR, "data")
CSV_FILE = os.path.join(CSV_DIR, "mqtt_battery_data.csv")


# =========================================================
# CSV Columns
# =========================================================

CSV_COLUMNS = [
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


# =========================================================
# Create data folder
# =========================================================

os.makedirs(CSV_DIR, exist_ok=True)


# =========================================================
# Create SQLite database/table if needed
# =========================================================

conn = sqlite3.connect(DB_FILE)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS battery_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    battery_id TEXT,
    cycle INTEGER,
    raw_data TEXT
)
""")

conn.commit()
conn.close()


# =========================================================
# Create CSV if needed
# =========================================================

if not os.path.exists(CSV_FILE):

    with open(
        CSV_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=CSV_COLUMNS
        )

        writer.writeheader()


# =========================================================
# MQTT CONNECT
# =========================================================

def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):

    if reason_code == 0:

        print()
        print("Connected to HiveMQ Cloud!")

        result = client.subscribe(TOPIC)

        if result[0] == mqtt.MQTT_ERR_SUCCESS:

            print("Subscribed to:", TOPIC)

        else:

            print(
                "Subscription failed:",
                result
            )

    else:

        print()
        print("Connection failed.")
        print("Reason Code:", reason_code)


# =========================================================
# MQTT DISCONNECT
# =========================================================

def on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties
):

    print()
    print("MQTT DISCONNECTED")
    print("Reason Code:", reason_code)


# =========================================================
# MQTT MESSAGE
# =========================================================

def on_message(
    client,
    userdata,
    message
):

    try:

        # -------------------------------------------------
        # Decode message
        # -------------------------------------------------

        payload = message.payload.decode("utf-8")

        data = json.loads(payload)


        # -------------------------------------------------
        # Extract values
        # -------------------------------------------------

        battery_id = data.get("Battery_ID")
        cycle = data.get("Cycle")

        voltage = data.get("Voltage_V")
        current = data.get("Current_A")
        temperature = data.get("Temperature_C")

        capacity = data.get("Capacity_Ah")

        resistance = data.get(
            "Internal_Resistance_Ohm"
        )

        charge_time = data.get(
            "Charge_Time_min"
        )

        soh = data.get("SOH")

        cooling = data.get(
            "Cooling_ON"
        )

        load_reduced = data.get(
            "Load_Reduced"
        )


        # =================================================
        # Save to SQLite
        # =================================================

        conn = sqlite3.connect(DB_FILE)

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO battery_data
            (
                battery_id,
                cycle,
                raw_data
            )
            VALUES (?, ?, ?)
            """,
            (
                str(battery_id),
                cycle,
                json.dumps(data)
            )
        )

        conn.commit()
        conn.close()


        # =================================================
        # Save to CSV
        # =================================================

        csv_row = {

            "Battery_ID": battery_id,
            "Cycle": cycle,
            "Voltage_V": voltage,
            "Current_A": current,
            "Temperature_C": temperature,
            "Capacity_Ah": capacity,
            "Internal_Resistance_Ohm": resistance,
            "Charge_Time_min": charge_time,
            "SOH": soh,
            "Cooling_ON": cooling,
            "Load_Reduced": load_reduced
        }


        with open(
            CSV_FILE,
            "a",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=CSV_COLUMNS
            )

            writer.writerow(csv_row)


        # =================================================
        # Display data
        # =================================================

        print()
        print("=" * 55)

        print(
            "Battery ID    :",
            battery_id
        )

        print(
            "Cycle         :",
            cycle
        )

        print(
            "Voltage       :",
            f"{voltage:.3f} V"
            if voltage is not None
            else "N/A"
        )

        print(
            "Current       :",
            f"{current:.2f} A"
            if current is not None
            else "N/A"
        )

        print(
            "Temperature   :",
            f"{temperature:.2f} °C"
            if temperature is not None
            else "N/A"
        )

        print(
            "Capacity      :",
            f"{capacity:.3f} Ah"
            if capacity is not None
            else "N/A"
        )

        print(
            "Resistance    :",
            f"{resistance:.5f} Ω"
            if resistance is not None
            else "N/A"
        )

        print(
            "Charge Time   :",
            f"{charge_time:.2f} min"
            if charge_time is not None
            else "N/A"
        )

        print(
            "Actual SOH    :",
            f"{soh:.2f}%"
            if soh is not None
            else "N/A"
        )

        print(
            "Cooling       :",
            "ON" if cooling else "OFF"
        )

        print(
            "Load Reduced  :",
            "YES" if load_reduced else "NO"
        )

        print()
        print(
            "Saved to      : battery.db + CSV"
        )

        print("=" * 55)


    except json.JSONDecodeError:

        print()
        print("ERROR: Invalid JSON received.")

        print(
            message.payload.decode(
                "utf-8",
                errors="replace"
            )
        )


    except Exception as e:

        print()
        print("ERROR while processing message:")

        print(
            type(e).__name__,
            ":",
            e
        )


# =========================================================
# MQTT CLIENT
# =========================================================

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="ev_soh_hivemq_receiver"
)


# =========================================================
# MQTT LOGIN
# =========================================================

client.username_pw_set(
    USERNAME,
    PASSWORD
)


# =========================================================
# TLS
# =========================================================

client.tls_set()


# =========================================================
# CALLBACKS
# =========================================================

client.on_connect = on_connect

client.on_disconnect = on_disconnect

client.on_message = on_message


# =========================================================
# START
# =========================================================

print()
print("==============================================")
print(" EV SOH - HiveMQ Receiver")
print("==============================================")

print()
print("Connecting to HiveMQ Cloud...")


try:

    client.connect(
        BROKER,
        PORT,
        60
    )

    client.loop_forever()


except KeyboardInterrupt:

    print()
    print("Receiver stopped by user.")


except Exception as e:

    print()
    print("MQTT ERROR:")

    print(
        type(e).__name__,
        ":",
        e
    )