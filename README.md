# Forecasting Indonesian Consumer Prices

**Wawan Saputra · Time Series & Statistical Modeling · 2026**

An expanding-window comparison of statistical and machine-learning forecasts for Indonesian CPI. The analysis selects a model before evaluating the final three-year holdout.

[Executive summary](outputs/executive_summary.md) · [Backtest tables](outputs/tables/model_comparison.csv) · [Notebooks](notebooks) · [Data attribution](THIRD_PARTY_DATA.md)

## Main finding

**Damped ETS** achieved the lowest rolling-origin RMSE among five fixed candidates. On the separate **2022–2024** holdout:

| Metric | Held-out result |
|---|---:|
| MAE | 4.952 CPI points |
| RMSE | 5.847 CPI points |
| MAPE | 2.90% |

![Historical holdout forecast](outputs/figures/test_forecast.png)

## Question and data

Can annual price-index forecasts improve on simple naive and drift benchmarks? The dataset is **World Bank/IMF CPI for Indonesia, 1970–2024**, 55 annual observations, indicator `FP.CPI.TOTL`, **2010=100**. CPI levels and annual inflation rates are distinct.

The cutoff is deliberately fixed at **2024**. Forecasts for 2025–2027 are retrospective outputs from that cutoff, not a current economic outlook. Raw JSON, retrieval metadata and SHA-256 checksums are retained. See [attribution and CC BY 4.0 terms](THIRD_PARTY_DATA.md).

## Methods and leakage controls

- Naive, log drift, ARIMA(1,1,1) with drift, damped ETS on log CPI, and recursive random forest using three past log-growth lags.
- Expanding origins **2009, 2012, 2015, 2018**, each with a three-year horizon; all end before the final holdout.
- Select by mean rolling-origin RMSE. No random splitting, test-based tuning or future lag values.
- ADF, ACF/PACF, trend/remainder plots, robust growth-anomaly flags and residual Ljung–Box diagnostics.

Annual observations cannot identify within-year seasonality, so no artificial seasonal period, SARIMA seasonality or seasonal decomposition is imposed. Crisis observations are retained.

## Rolling-origin comparison

These are **pre-test averages across origins**, not the final holdout metrics above.

| model              |    mae |   rmse |   mape_pct |
|:-------------------|-------:|-------:|-----------:|
| Damped ETS         |  7.610 |  8.399 |      5.654 |
| Random Forest lags | 10.217 | 11.154 |      7.901 |
| Naive              | 10.366 | 11.163 |      8.068 |
| ARIMA(1,1,1)       | 16.161 | 18.387 |     11.856 |
| Drift              | 18.849 | 20.849 |     13.948 |

## Reproduce

Python 3.11 was tested. From this repository:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m src.run
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Linux/macOS: use `.venv/bin/python`. Direct dependencies are pinned; transitive versions are resolved by pip. Cached raw data are checksum-verified. Three executed notebooks cover EDA, model evaluation and interpretation; set their explicit rebuild switch only when retraining is intended.

## Limitations and Future Work

Only 55 observations, structural breaks and latest-vintage revisions; this is not real-time vintage backtesting. Exponentiated log forecasts are median-scale estimates. The selected ETS outputs are **point forecasts without prediction intervals**. No exogenous predictors or superiority significance test is claimed. Future work: monthly data, uncertainty calibration, additional origins and vintage-aware evaluation.

## Repository guide

`src/run.py` data/model/evaluation functions · `data/` snapshots and processed CPI · `notebooks/` executed walkthroughs · `outputs/tables/` origins, forecasts and diagnostics · `outputs/figures/` plots · `tests/` temporal-integrity checks.
