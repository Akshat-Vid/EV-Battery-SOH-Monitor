import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor
import numpy as np

# Load dataset
df = pd.read_csv("data/synthetic_ev_battery_soh.csv")

# Features
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

# Split by Battery_ID
battery_ids = df["Battery_ID"].unique()

train_batteries, test_batteries = train_test_split(
    battery_ids,
    test_size=0.20,
    random_state=42
)

train_mask = df["Battery_ID"].isin(train_batteries)
test_mask = df["Battery_ID"].isin(test_batteries)

X_train = X[train_mask]
X_test = X[test_mask]

y_train = y[train_mask]
y_test = y[test_mask]

# XGBoost model
model = XGBRegressor(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    random_state=42,
    n_jobs=-1
)

print("Training XGBoost...")

model.fit(X_train, y_train)

print("Training completed!")

# Predictions
y_pred = model.predict(X_test)

# Metrics
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("\nXGBoost Evaluation")
print("==================")
print(f"MAE  : {mae:.4f}")
print(f"RMSE : {rmse:.4f}")
print(f"R²   : {r2:.4f}")

# Actual vs Predicted graph
plt.figure(figsize=(8, 6))

plt.scatter(y_test, y_pred, alpha=0.4)

min_value = min(y_test.min(), y_pred.min())
max_value = max(y_test.max(), y_pred.max())

plt.plot(
    [min_value, max_value],
    [min_value, max_value],
    linestyle="--"
)

plt.xlabel("Actual SOH (%)")
plt.ylabel("Predicted SOH (%)")
plt.title("XGBoost: Actual vs Predicted SOH")
plt.grid(True)
plt.tight_layout()

plt.show()