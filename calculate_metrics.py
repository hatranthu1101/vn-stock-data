#!/usr/bin/env python3
"""Calculate stock metrics from CSV data."""

import csv
import json
import math
from datetime import datetime, timedelta
from collections import defaultdict
import yaml

def load_tickers_from_config():
    """Load tickers from config.yaml"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config.get('tickers', [])

def load_csv_data():
    """Load stock data from CSV"""
    data = defaultdict(list)
    with open('data/stock_data.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row['Ticker']
            date = row['Date']
            data[ticker].append({
                'date': date,
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume'])
            })
    return data

def get_latest_date(data_by_ticker):
    """Get the latest date from all data"""
    latest = None
    for ticker_data in data_by_ticker.values():
        if ticker_data:
            for record in ticker_data:
                if latest is None or record['date'] > latest:
                    latest = record['date']
    return latest

def calculate_metrics(ticker, ticker_data):
    """Calculate metrics for a single ticker"""
    if not ticker_data:
        return None

    # Sort by date
    sorted_data = sorted(ticker_data, key=lambda x: x['date'])

    # Get last 30 days data
    last_30 = sorted_data[-30:] if len(sorted_data) >= 30 else sorted_data

    # Full period data
    full_data = sorted_data

    # Return 30D (last 30 days)
    if len(last_30) >= 2:
        close_30_start = last_30[0]['close']
        close_30_end = last_30[-1]['close']
        return_30d = ((close_30_end - close_30_start) / close_30_start) * 100
    else:
        return_30d = 0

    # Return full period
    if len(full_data) >= 2:
        close_start = full_data[0]['close']
        close_end = full_data[-1]['close']
        return_full = ((close_end - close_start) / close_start) * 100
    else:
        return_full = 0

    # Volatility (standard deviation of daily returns)
    daily_returns = []
    for i in range(1, len(last_30)):
        r = ((last_30[i]['close'] - last_30[i-1]['close']) / last_30[i-1]['close']) * 100
        daily_returns.append(r)

    if daily_returns:
        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
        volatility = math.sqrt(variance)
    else:
        volatility = 0

    # Trend (linear regression slope on close prices)
    if len(last_30) >= 2:
        x = list(range(len(last_30)))
        y = [d['close'] for d in last_30]
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
        if denominator != 0:
            slope = numerator / denominator
            trend = 'up' if slope > 0.5 else 'down' if slope < -0.5 else 'sideway'
        else:
            trend = 'sideway'
    else:
        trend = 'sideway'

    # Volume trend (last 7 days vs full period)
    if len(last_30) >= 7:
        vol_last_7 = sum(d['volume'] for d in last_30[-7:]) / 7
        vol_full = sum(d['volume'] for d in last_30) / len(last_30)
        vol_trend = (vol_last_7 / vol_full - 1) * 100 if vol_full > 0 else 0
    else:
        vol_trend = 0

    # Current price and last close
    current_price = last_30[-1]['close']
    last_date = last_30[-1]['date']

    return {
        'ticker': ticker,
        'current_price': round(current_price, 2),
        'last_date': last_date,
        'return_30d': round(return_30d, 2),
        'return_full': round(return_full, 2),
        'volatility': round(volatility, 2),
        'trend': trend,
        'volume_trend': round(vol_trend, 2),
        'data_points': len(last_30)
    }

def rank_stocks(metrics_list):
    """Rank stocks and classify into categories"""
    # Sort by return_30d and volatility
    scored = []
    for m in metrics_list:
        if m:
            # Score: return - penalty for volatility
            score = m['return_30d'] - (m['volatility'] * 0.5)
            scored.append((score, m))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Classify
    top_3 = [m for _, m in scored[:3]]
    mid = [m for _, m in scored[3:7]]
    bottom = [m for _, m in scored[7:]]

    return {
        'top_picks': top_3,
        'watch': mid,
        'avoid': bottom,
        'all_ranked': [m for _, m in scored]
    }

if __name__ == '__main__':
    tickers = load_tickers_from_config()
    all_data = load_csv_data()
    latest_date = get_latest_date(all_data)

    # Calculate metrics
    metrics = []
    for ticker in tickers:
        ticker_data = all_data.get(ticker, [])
        m = calculate_metrics(ticker, ticker_data)
        if m:
            metrics.append(m)

    # Rank
    ranked = rank_stocks(metrics)

    # Save metrics
    output = {
        'timestamp': datetime.now().isoformat(),
        'latest_date': latest_date,
        'metrics': ranked['all_ranked'],
        'classification': {
            'top_picks': ranked['top_picks'],
            'watch': ranked['watch'],
            'avoid': ranked['avoid']
        }
    }

    import os
    os.makedirs('data/pipeline', exist_ok=True)
    with open('data/pipeline/stock_metrics.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✓ Metrics saved to data/pipeline/stock_metrics.json")
    print(f"Latest date: {latest_date}")
    print(f"Total stocks analyzed: {len(metrics)}")
    print(f"Top 3 picks: {[m['ticker'] for m in ranked['top_picks']]}")
