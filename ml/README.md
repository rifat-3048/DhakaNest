# DhakaNest ML Workspace

This directory contains the complete machine-learning workflow for the
DhakaNest rent-prediction system.

## Dataset

The original dataset is stored at:

data/raw/houserentdhaka.csv

The raw dataset must never be edited manually.

## Notebooks

- 00_DhakaNest_Data_Preparation.ipynb
- 01_DhakaNest_Random_Forest.ipynb
- 02_DhakaNest_XGBoost.ipynb
- 03_DhakaNest_CatBoost.ipynb
- 04_DhakaNest_Model_Comparison_and_Export.ipynb

## Evaluation Metrics

Rent-prediction candidates are evaluated using:

- MAE
- RMSE
- R²
- MAPE
- Median Absolute Error
- P90 Absolute Error

## Fixed Configuration

- Random state: 42
- Training split: 70%
- Validation split: 15%
- Test split: 15%
