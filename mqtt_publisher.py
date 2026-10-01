import os
import json
import time
import random
import ssl
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# ============================================================
# LOAD HIVE MQ CREDENTIALS
# ============================================================

load_dotenv()

BROKER = os.getenv("HIVEMQ_HOST")
PORT = int(os.getenv("HIVEMQ_PORT", "8883"))
USERNAME = os.getenv("HIVEMQ_USERNAME")
PASSWORD = os.getenv("HIVEMQ_PASSWORD")

DATA_TOPIC = "ev/battery/data"
CONTROL_TOPIC = "ev/battery/control"

# ============================================================
# BATTERY INITIAL VALUES
# ============================================================

battery_id = 1
cycle = 1

voltage = 4.15
current = 5.0
temperature = 28.0

soh = 100.0
capacity = 2.90
internal_resistance = 0.048
charge_time = 88.0

# ============================================================
# CONTROL STATES
# ============================================================

cooling_on = False
load_reduced = False

temperature_boost = 0.0
current_boost = 0.0

# ============================================================
# MQTT CALLBACK
# ============================================================

def on_connect(client, userdata, flags, reason_code, properties):

    if reason_code == 0:

        print("Connected to HiveMQ Cloud!")
        print("Listening for control commands...")
        print("Control topic:", CONTROL_TOPIC)

        client.subscribe(CONTROL_TOPIC)

    else:

        print("Connection failed.")
        print("Reason code:", reason_code)


def on_message(client, userdata, msg):

    global cooling_on
    global load_reduced
    global temperature_boost
    global current_boost
    global soh
    global capacity
    global internal_resistance
    global charge_time

    try:

        message = msg.payload.decode()

        print("\nCONTROL COMMAND RECEIVED:")
        print(message)

        command_data = json.loads(message)

        command = command_data.get("command")

        # ----------------------------------------------------
        # COOLING ON
        # ----------------------------------------------------

        if command == "COOLING_ON":

            cooling_on = True

            print("Cooling system: ON")

        # ----------------------------------------------------
        # COOLING OFF
        # ----------------------------------------------------

        elif command == "COOLING_OFF":

            cooling_on = False

            print("Cooling system: OFF")

        # ----------------------------------------------------
        # REDUCE LOAD
        # ----------------------------------------------------

        elif command == "REDUCE_LOAD":

            load_reduced = True

            print("Load reduction: ON")

        # ----------------------------------------------------
        # RESTORE LOAD
        # ----------------------------------------------------

        elif command == "RESTORE_LOAD":

            load_reduced = False

            print("Load reduction: OFF")

        # ----------------------------------------------------
        # TEST HIGH TEMPERATURE
        # ----------------------------------------------------

        elif command == "TEST_HIGH_TEMP":

            temperature_boost = 15.0

            print("TEST MODE: High temperature activated")

        # ----------------------------------------------------
        # TEST OVER CURRENT
        # ----------------------------------------------------

        elif command == "TEST_OVER_CURRENT":

            current_boost = 12.0

            print("TEST MODE: Over-current activated")

        # ----------------------------------------------------
        # RESET TEST CONDITIONS
        # ----------------------------------------------------

        elif command == "RESET":

            temperature_boost = 0.0
            current_boost = 0.0
            cooling_on = False
            load_reduced = False

            print("Battery simulation reset.")

        else:

            print("Unknown command:", command)

    except Exception as e:

        print("Control command error:", e)


# ============================================================
# CREATE MQTT CLIENT
# ============================================================

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="ev_live_battery_simulator"
)

client.username_pw_set(
    USERNAME,
    PASSWORD
)

client.tls_set(
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)

client.on_connect = on_connect
client.on_message = on_message

# ============================================================
# CONNECT
# ============================================================

print("========================================")
print(" LIVE EV BATTERY SIMULATOR")
print("========================================")

print("Connecting to HiveMQ Cloud...")

client.connect(
    BROKER,
    PORT,
    60
)

# Start MQTT network loop in background
client.loop_start()

print("Simulator started.")
print("Publishing live battery data...")
print("")


# ============================================================
# MAIN SIMULATION LOOP
# ============================================================

try:

    while True:

        # ----------------------------------------------------
        # CURRENT
        # ----------------------------------------------------

        if load_reduced:

            current = random.uniform(1.0, 4.0)

        else:

            current = random.uniform(2.0, 12.0)

        # Add test over-current condition
        current += current_boost

        # ----------------------------------------------------
        # TEMPERATURE
        # ----------------------------------------------------

        # Temperature naturally changes with current
        temperature_change = (
            (current * 0.12)
            + random.uniform(-0.8, 0.8)
        )

        temperature += (
            temperature_change * 0.15
        )

        # Add test temperature condition
        temperature += temperature_boost * 0.05

        # Cooling effect
        if cooling_on:

            temperature -= 1.5

        # Keep temperature in realistic simulation range
        temperature = max(
            20.0,
            min(55.0, temperature)
        )

        # ----------------------------------------------------
        # VOLTAGE
        # ----------------------------------------------------

        voltage = (
            4.18
            - (current * 0.018)
            + random.uniform(-0.025, 0.025)
        )

        voltage = max(
            3.30,
            min(4.20, voltage)
        )

        # ----------------------------------------------------
        # SOH
        # ----------------------------------------------------

        # Very slow degradation
        soh -= random.uniform(
            0.001,
            0.005
        )

        soh = max(
            70.0,
            min(100.0, soh)
        )

        # ----------------------------------------------------
        # CAPACITY
        # ----------------------------------------------------

        capacity = 2.90 * (
            soh / 100.0
        )

        # Small natural fluctuation
        capacity += random.uniform(
            -0.01,
            0.01
        )

        # ----------------------------------------------------
        # INTERNAL RESISTANCE
        # ----------------------------------------------------

        internal_resistance = (
            0.048
            + ((100.0 - soh) * 0.0008)
        )

        internal_resistance += random.uniform(
            -0.0005,
            0.0005
        )

        # ----------------------------------------------------
        # CHARGE TIME
        # ----------------------------------------------------

        charge_time = (
            88
            + ((100.0 - soh) * 0.8)
        )

        charge_time += random.uniform(
            -1.0,
            1.0
        )

        # ----------------------------------------------------
        # CREATE DATA PAYLOAD
        # ----------------------------------------------------

        payload = {

            "Battery_ID": battery_id,

            "Cycle": cycle,

            "Voltage_V": round(
                voltage,
                4
            ),

            "Current_A": round(
                current,
                4
            ),

            "Temperature_C": round(
                temperature,
                2
            ),

            "Capacity_Ah": round(
                capacity,
                4
            ),

            "Internal_Resistance_Ohm": round(
                internal_resistance,
                5
            ),

            "Charge_Time_min": round(
                charge_time,
                2
            ),

            "SOH": round(
                soh,
                2
            ),

            "Cooling_ON": cooling_on,

            "Load_Reduced": load_reduced

        }

        # ----------------------------------------------------
        # CONVERT TO JSON
        # ----------------------------------------------------

        message = json.dumps(payload)

        # ----------------------------------------------------
        # PUBLISH
        # ----------------------------------------------------

        result = client.publish(
            DATA_TOPIC,
            message
        )

        result.wait_for_publish()

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        print("----------------------------------------")

        print(
            f"Battery ID    : {battery_id}"
        )

        print(
            f"Cycle         : {cycle}"
        )

        print(
            f"Voltage       : {voltage:.3f} V"
        )

        print(
            f"Current       : {current:.2f} A"
        )

        print(
            f"Temperature   : {temperature:.2f} °C"
        )

        print(
            f"Capacity      : {capacity:.3f} Ah"
        )

        print(
            f"Resistance    : "
            f"{internal_resistance:.5f} Ω"
        )

        print(
            f"Charge Time   : "
            f"{charge_time:.2f} min"
        )

        print(
            f"Actual SOH    : {soh:.2f}%"
        )

        print(
            f"Cooling       : "
            f"{'ON' if cooling_on else 'OFF'}"
        )

        print(
            f"Load Reduced  : "
            f"{'YES' if load_reduced else 'NO'}"
        )

        # ----------------------------------------------------
        # NEXT CYCLE
        # ----------------------------------------------------

        cycle += 1

        time.sleep(1)


except KeyboardInterrupt:

    print("\n")
    print("Stopping battery simulator...")

finally:

    client.loop_stop()

    client.disconnect()

    print("Disconnected from HiveMQ.")