import numpy as np
import pandas as pd

np.random.seed(42)

# Number of batteries
num_batteries = 100

# Number of cycles for each battery
cycles_per_battery = 500

data = []

for battery in range(1, num_batteries + 1):

    # Initial capacity of the battery
    initial_capacity = np.random.uniform(2.4, 3.2)

    # Battery-specific degradation rate
    degradation_rate = np.random.uniform(0.00015, 0.00045)

    for cycle in range(1, cycles_per_battery + 1):

        # Battery capacity degradation
        degradation = degradation_rate * cycle

        capacity = initial_capacity * (1 - degradation)

        # Measurement noise
        capacity += np.random.normal(0, 0.015)

        # Avoid unrealistic capacity
        capacity = max(
            capacity,
            initial_capacity * 0.70
        )

        # Calculate SOH
        soh = (capacity / initial_capacity) * 100

        # Battery voltage
        voltage = (
            4.15
            - 0.00025 * cycle
            + np.random.normal(0, 0.015)
        )

        voltage = np.clip(voltage, 3.6, 4.2)

        # Battery current
        current = np.random.uniform(1.0, 3.0)

        # Battery temperature
        temperature = (
            25
            + 2.0 * current
            + 0.008 * cycle
            + np.random.normal(0, 0.8)
        )

        # Internal resistance
        resistance = (
            0.045
            + 0.00005 * cycle
            + np.random.normal(0, 0.003)
        )

        resistance = max(resistance, 0.03)

        # Charging time
        charge_time = (
            90
            + 0.05 * cycle
            + np.random.normal(0, 2)
        )

        charge_time = max(charge_time, 70)

        data.append([
            battery,
            cycle,
            voltage,
            current,
            temperature,
            capacity,
            resistance,
            charge_time,
            soh
        ])


# Create DataFrame
columns = [
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

df = pd.DataFrame(data, columns=columns)

# Limit SOH
df["SOH"] = df["SOH"].clip(70, 100)

# Save dataset
df.to_csv(
    "data/synthetic_ev_battery_soh.csv",
    index=False
)

print("====================================")
print("Synthetic dataset created!")
print("====================================")

print("Number of rows:", len(df))
print("Number of columns:", len(df.columns))

print("\nFirst 5 rows:")
print(df.head())

print("\nSOH statistics:")
print(df["SOH"].describe())