import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor
import numpy as np
import joblib

# --------------------------------
# Load dataset
# --------------------------------

df = pd.read_csv("data/synthetic_ev_battery_soh.csv")

# --------------------------------
# Select features
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
# Split by Battery_ID
# --------------------------------

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

# --------------------------------
# Create XGBoost model
# --------------------------------

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

# --------------------------------
# Train model
# --------------------------------

print("Training XGBoost model...")

model.fit(X_train, y_train)

print("Training completed!")

# --------------------------------
# Save trained model
# --------------------------------

joblib.dump(model, "xgboost_soh_model.pkl")

print("Model saved as: xgboost_soh_model.pkl")

# --------------------------------
# Make predictions
# --------------------------------

y_pred = model.predict(X_test)

# --------------------------------
# Evaluate model
# --------------------------------

mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

# --------------------------------
# Display results
# --------------------------------

print("\nXGBoost Results")
print("================")

print(f"MAE  : {mae:.4f}")
print(f"RMSE : {rmse:.4f}")
print(f"R2   : {r2:.4f}")

# --------------------------------
# Sample predictions
# --------------------------------

results = pd.DataFrame({
    "Actual_SOH": y_test.values[:10],
    "Predicted_SOH": y_pred[:10]
})

print("\nSample Predictions:")
print(results)