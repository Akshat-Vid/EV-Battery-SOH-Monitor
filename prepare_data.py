import pandas as pd

# Load the synthetic dataset
df = pd.read_csv("data/synthetic_ev_battery_soh.csv")

print("Original dataset shape:")
print(df.shape)


# --------------------------------
# Select input features
# --------------------------------

features = [
    "Voltage_V",
    "Current_A",
    "Temperature_C",
    "Capacity_Ah",
    "Internal_Resistance_Ohm",
    "Charge_Time_min"
]


# --------------------------------
# Create X and y
# --------------------------------

X = df[features]

y = df["SOH"]


# --------------------------------
# Display information
# --------------------------------

print("\nInput features (X):")
print(X.head())

print("\nTarget variable (y):")
print(y.head())


# --------------------------------
# Check missing values
# --------------------------------

print("\nMissing values in X:")
print(X.isnull().sum())

print("\nMissing values in y:")
print(y.isnull().sum())


# --------------------------------
# Display shapes
# --------------------------------

print("\nShape of X:")
print(X.shape)

print("\nShape of y:")
print(y.shape)


# --------------------------------
# Display selected features
# --------------------------------

print("\nFeatures used for ML:")
for feature in features:
    print("-", feature)

print("\nTarget:")
print("- SOH")
