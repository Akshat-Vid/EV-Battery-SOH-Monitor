import pandas as pd
from sklearn.model_selection import train_test_split

# --------------------------------
# Load dataset
# --------------------------------

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

X = df[features]
y = df["SOH"]

# --------------------------------
# Split batteries, not individual rows
# --------------------------------

battery_ids = df["Battery_ID"].unique()

train_batteries, test_batteries = train_test_split(
    battery_ids,
    test_size=0.20,
    random_state=42
)

# --------------------------------
# Create train/test datasets
# --------------------------------

train_mask = df["Battery_ID"].isin(train_batteries)
test_mask = df["Battery_ID"].isin(test_batteries)

X_train = X[train_mask]
X_test = X[test_mask]

y_train = y[train_mask]
y_test = y[test_mask]

# --------------------------------
# Display results
# --------------------------------

print("\nNumber of training batteries:")
print(len(train_batteries))

print("\nNumber of testing batteries:")
print(len(test_batteries))

print("\nTraining data shape:")
print(X_train.shape)

print("\nTesting data shape:")
print(X_test.shape)

print("\nTraining target shape:")
print(y_train.shape)

print("\nTesting target shape:")
print(y_test.shape)

print("\nMissing values in training data:")
print(X_train.isnull().sum())

print("\nMissing values in testing data:")
print(X_test.isnull().sum())

print("\nStep 6 completed successfully!")