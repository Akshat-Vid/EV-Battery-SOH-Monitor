import paho.mqtt.client as mqtt

BROKER = "2ed599332c774488978838f91633b9db.s1.eu.hivemq.cloud"
PORT = 8883

USERNAME = "ev_soh_user"
PASSWORD = "Iaj@4793"

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="ev_soh_test"
)

client.username_pw_set(USERNAME, PASSWORD)

client.tls_set()

print("Connecting to HiveMQ Cloud...")

client.connect(BROKER, PORT, 60)

print("Connected successfully to HiveMQ Cloud!")

client.disconnect()

print("Disconnected.")