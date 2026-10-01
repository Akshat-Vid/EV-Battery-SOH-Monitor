import pandas as pd
import matplotlib.pyplot as plt

# Load dataset
df = pd.read_csv("data/synthetic_ev_battery_soh.csv")

# -----------------------------
# 1. Cycle vs SOH
# -----------------------------

plt.figure(figsize=(10, 6))

plt.scatter(
    df["Cycle"],
    df["SOH"],
    s=2,
    alpha=0.3
)

plt.xlabel("Cycle Number")
plt.ylabel("SOH (%)")
plt.title("Battery SOH vs Cycle Number")
plt.grid(True)

plt.show()


# -----------------------------
# 2. Cycle vs Capacity
# -----------------------------

plt.figure(figsize=(10, 6))

plt.scatter(
    df["Cycle"],
    df["Capacity_Ah"],
    s=2,
    alpha=0.3
)

plt.xlabel("Cycle Number")
plt.ylabel("Capacity (Ah)")
plt.title("Battery Capacity vs Cycle Number")
plt.grid(True)

plt.show()


# -----------------------------
# 3. Cycle vs Internal Resistance
# -----------------------------

plt.figure(figsize=(10, 6))

plt.scatter(
    df["Cycle"],
    df["Internal_Resistance_Ohm"],
    s=2,
    alpha=0.3
)

plt.xlabel("Cycle Number")
plt.ylabel("Internal Resistance (Ohm)")
plt.title("Internal Resistance vs Cycle Number")
plt.grid(True)

plt.show()


# -----------------------------
# 4. Temperature distribution
# -----------------------------

plt.figure(figsize=(10, 6))

plt.hist(
    df["Temperature_C"],
    bins=40
)

plt.xlabel("Temperature (°C)")
plt.ylabel("Number of Measurements")
plt.title("Battery Temperature Distribution")
plt.grid(True)

plt.show()