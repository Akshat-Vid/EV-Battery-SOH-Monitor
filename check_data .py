import pandas as pd

# Load dataset
df = pd.read_csv("data/synthetic_ev_battery_soh.csv")

print("========== DATASET INFO ==========")

print("\nShape:")
print(df.shape)

print("\nColumn names:")
print(df.columns.tolist())

print("\nMissing values:")
print(df.isnull().sum())

print("\nDuplicate rows:")
print(df.duplicated().sum())

print("\nData types:")
print(df.dtypes)

print("\n========== STATISTICS ==========")

print(df.describe())

print("\n========== SOH RANGE ==========")

print("Minimum SOH:", df["SOH"].min())
print("Maximum SOH:", df["SOH"].max())

print("\n========== SAMPLE DATA ==========")

print(df.head(10))