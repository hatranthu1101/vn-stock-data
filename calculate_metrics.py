#!/usr/bin/env python3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import yaml

# Read config
with open('config.yaml') as f:
    config = yaml.safe_load(f)

tickers = config['tickers']

# Read CSV
df = pd.read_csv('data/stock_data.csv')
df['Date'] = pd.to_datetime(df['Date'])

# Get latest date
latest_date = df['Date'].max()
print(f"Latest date in data: {latest_date.date()}")

# Calculate metrics for each ticker
metrics = {}

for ticker in tickers:
    ticker_data = df[df['Ticker'] == ticker].sort_values('Date').reset_index(drop=True)

    if len(ticker_data) == 0:
        print(f"⚠️  {ticker}: No data")
        continue

    # Get last 30 days of data
    last_30 = ticker_data.tail(30)

    if len(last_30) == 0:
        print(f"⚠️  {ticker}: Not enough data")
        continue

    # Return 30D
    first_close = last_30['Close'].iloc[0]
    last_close = last_30['Close'].iloc[-1]
    return_30d = ((last_close - first_close) / first_close) * 100

    # Volatility: std dev of daily returns
    daily_returns = last_30['Close'].pct_change() * 100
    volatility = daily_returns.std()

    # Trend: linear regression slope over 30d
    x = np.arange(len(last_30))
    y = last_30['Close'].values
    coeffs = np.polyfit(x, y, 1)
    trend_slope = coeffs[0]
    trend = "Tăng" if trend_slope > 0 else ("Giảm" if trend_slope < 0 else "Sideway")

    # Volume trend: avg volume last 7 days vs all 30 days
    vol_7d_avg = last_30['Volume'].tail(7).mean()
    vol_30d_avg = last_30['Volume'].mean()
    vol_trend = (vol_7d_avg / vol_30d_avg - 1) * 100 if vol_30d_avg > 0 else 0

    # Return full period if more data
    first_close_all = ticker_data['Close'].iloc[0]
    last_close_all = ticker_data['Close'].iloc[-1]
    return_all = ((last_close_all - first_close_all) / first_close_all) * 100

    metrics[ticker] = {
        'return_30d': round(return_30d, 2),
        'return_all': round(return_all, 2),
        'volatility': round(volatility, 2),
        'trend': trend,
        'trend_slope': round(trend_slope, 4),
        'volume_trend': round(vol_trend, 2),
        'last_close': round(last_close, 2),
        'data_points': len(last_30)
    }

    print(f"✓ {ticker}: Return30D={return_30d:.2f}%, Vol={volatility:.2f}%, Trend={trend}")

# Save to JSON
with open('data/pipeline/stock_metrics.json', 'w') as f:
    json.dump({
        'timestamp': latest_date.isoformat(),
        'metrics': metrics
    }, f, indent=2, ensure_ascii=False)

print(f"\n✓ Saved {len(metrics)} tickers to data/pipeline/stock_metrics.json")
