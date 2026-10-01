import pandas as pd

# Model results
results = pd.DataFrame({
    "Model": ["Random Forest", "XGBoost"],
    "MAE": [2.0609, 2.0079],
    "RMSE": [2.6843, 2.6141],
    "R2": [0.7087, 0.7238]
})

print("MODEL COMPARISON")
print("================")

print(results.to_string(index=False))

print("\nInterpretation:")
print("Lower MAE is better.")
print("Lower RMSE is better.")
print("Higher R² is better.")