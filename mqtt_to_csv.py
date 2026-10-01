import json
import csv
import os
import paho.mqtt.client as mqtt

BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "ev/battery/data"

CSV_FILE = "data/mqtt_battery_data.csv"

CSV_COLUMNS = [
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


def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected to MQTT broker!")
    client.subscribe(TOPIC)
    print(f"Subscribed to: {TOPIC}")


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())

        file_exists = os.path.isfile(CSV_FILE)

        with open(CSV_FILE, "a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)

            if not file_exists:
                writer.writeheader()

            writer.writerow(data)

        print(
            f"Received and saved: "
            f"Battery {int(data['Battery_ID'])}, "
            f"Cycle {int(data['Cycle'])}"
        )

    except Exception as e:
        print("Error:", e)


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="ev_soh_csv_receiver"
)

client.on_connect = on_connect
client.on_message = on_message

print("Connecting to MQTT broker...")

client.connect(BROKER, PORT, 60)

client.loop_forever()