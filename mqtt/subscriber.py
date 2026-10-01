import os
import ssl
import json
import sqlite3
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Load .env
load_dotenv()

# HiveMQ settings
BROKER = os.getenv("HIVEMQ_HOST")
PORT = int(os.getenv("HIVEMQ_PORT", "8883"))
USERNAME = os.getenv("HIVEMQ_USERNAME")
PASSWORD = os.getenv("HIVEMQ_PASSWORD")

# MQTT topic
TOPIC = "ev/battery/data"

# SQLite database
DB_NAME = "battery.db"


# ---------------- DATABASE ----------------

def create_database():
    conn = sqlite3.connect(DB_NAME)
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

    print("SQLite database ready.")


def save_data(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    battery_id = None
    cycle = None

    # Try to read JSON data
    try:
        data = json.loads(message)

        battery_id = data.get("battery_id")
        cycle = data.get("cycle")

    except Exception:
        # If publisher sends normal text instead of JSON,
        # save the complete message anyway.
        pass

    cursor.execute("""
        INSERT INTO battery_data
        (battery_id, cycle, raw_data)
        VALUES (?, ?, ?)
    """, (battery_id, cycle, message))

    conn.commit()
    conn.close()

    print("Saved to SQLite database.")


# ---------------- MQTT ----------------

def on_connect(client, userdata, flags, reason_code, properties):

    if reason_code == 0:
        print("Connected to HiveMQ successfully!")
        print("Subscribing to:", TOPIC)

        client.subscribe(TOPIC)

        print("Waiting for battery data...")

    else:
        print("Connection failed. Reason code:", reason_code)


def on_message(client, userdata, msg):

    message = msg.payload.decode()

    print("\n------------------------------")
    print("Received battery data:")
    print("Topic:", msg.topic)
    print("Data:", message)

    save_data(message)


# ---------------- START ----------------

create_database()

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="ev_battery_database_subscriber"
)

client.username_pw_set(USERNAME, PASSWORD)

client.tls_set(
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)

client.on_connect = on_connect
client.on_message = on_message

print("Connecting to HiveMQ...")

client.connect(BROKER, PORT, 60)

client.loop_forever()