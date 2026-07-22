#!/usr/bin/env python3
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import yaml

# Read config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Read data
df = pd.read_csv('data/stock_data.csv')
df['Date'] = pd.to_datetime(df['Date'])

# Get latest date and last 30 days
latest_date = df['Date'].max()
cutoff_date = latest_date - timedelta(days=29)
df_30d = df[df['Date'] >= cutoff_date].copy()

metrics = {}

for ticker in config['tickers']:
    ticker_data = df_30d[df_30d['Ticker'] == ticker].sort_values('Date')

    if len(ticker_data) == 0:
        continue

    close = ticker_data['Close'].values
    volume = ticker_data['Volume'].values

    # Return 30D
    return_30d = ((close[-1] - close[0]) / close[0] * 100) if len(close) > 0 else 0

    # Full return
    full_data = df[df['Ticker'] == ticker].sort_values('Date')
    full_close = full_data['Close'].values
    return_full = ((full_close[-1] - full_close[0]) / full_close[0] * 100) if len(full_close) > 0 else 0

    # Volatility (daily return std)
    daily_ret = np.diff(close) / close[:-1] * 100
    volatility = np.std(daily_ret) if len(daily_ret) > 0 else 0

    # Trend (linear regression slope)
    x = np.arange(len(close))
    if len(close) > 1:
        slope = np.polyfit(x, close, 1)[0]
        trend = 'up' if slope > 0 else 'down' if slope < 0 else 'sideways'
    else:
        trend = 'unknown'

    # Volume trend
    vol_7d_avg = np.mean(volume[-7:])
    vol_full_avg = np.mean(volume)
    vol_trend_pct = ((vol_7d_avg - vol_full_avg) / vol_full_avg * 100) if vol_full_avg > 0 else 0

    metrics[ticker] = {
        'return_30d': round(return_30d, 2),
        'return_full': round(return_full, 2),
        'volatility': round(volatility, 2),
        'trend': trend,
        'volume_trend': round(vol_trend_pct, 2),
        'latest_close': round(close[-1], 2),
        'data_points': len(ticker_data)
    }

# Save metrics
with open('data/pipeline/stock_metrics.json', 'w') as f:
    json.dump({
        'analysis_date': latest_date.strftime('%Y-%m-%d'),
        'metrics': metrics
    }, f, indent=2)

# Rank tickers
# Scoring: return (40%) + risk-adj (30%) + trend (30%)
scores = {}
for ticker, m in metrics.items():
    return_score = m['return_30d']
    vol = m['volatility']
    volatility_score = -vol

    trend_score = {'up': 10, 'sideways': 0, 'down': -10}.get(m['trend'], 0)

    score = return_score * 0.4 + volatility_score * 0.3 + trend_score * 0.3
    scores[ticker] = round(score, 2)

ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
top_3 = [t[0] for t in ranked[:3]]
mid = [t[0] for t in ranked[3:7]]
bottom = [t[0] for t in ranked[7:]]

# Create HTML report
html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VN Stock Daily Briefing</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            page-break-after: always;
        }}
        h1 {{
            font-size: 28px;
            margin-bottom: 8px;
            color: #1a1a1a;
        }}
        .date {{
            color: #666;
            font-size: 14px;
            margin-bottom: 24px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 24px;
            font-size: 13px;
        }}
        th {{
            background: #f0f0f0;
            padding: 10px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #ddd;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{ background: #fafafa; }}
        .positive {{ color: #27ae60; font-weight: 500; }}
        .negative {{ color: #e74c3c; font-weight: 500; }}
        .section {{
            margin-bottom: 24px;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-buy {{ background: #d4edda; color: #155724; }}
        .badge-watch {{ background: #fff3cd; color: #856404; }}
        .badge-avoid {{ background: #f8d7da; color: #721c24; }}
        .pick-item {{
            margin-bottom: 12px;
            padding: 12px;
            background: #f9f9f9;
            border-left: 3px solid #27ae60;
            border-radius: 2px;
        }}
        .pick-ticker {{
            font-weight: 700;
            font-size: 14px;
            color: #1a1a1a;
        }}
        .pick-reason {{
            font-size: 12px;
            color: #666;
            margin-top: 4px;
            line-height: 1.4;
        }}
        .chart-container {{
            position: relative;
            height: 250px;
            margin-bottom: 24px;
        }}
    </style>
</head>
<body>
<div class="container">
    <h1>📈 VN Stock Daily Briefing</h1>
    <div class="date">{latest_date.strftime('%d/%m/%Y')}</div>

    <div class="section">
        <div class="section-title">📊 Bảng tóm tắt 10 mã</div>
        <table>
            <thead>
                <tr>
                    <th>Mã</th>
                    <th>Return 30D</th>
                    <th>Volatility</th>
                    <th>Trend</th>
                    <th>Khuyến nghị</th>
                </tr>
            </thead>
            <tbody>
"""

for ticker, m in metrics.items():
    ret_class = 'positive' if m['return_30d'] > 0 else 'negative'
    if ticker in top_3:
        badge = '<span class="badge badge-buy">✅ Xem xét</span>'
    elif ticker in mid:
        badge = '<span class="badge badge-watch">⚠️ Theo dõi</span>'
    else:
        badge = '<span class="badge badge-avoid">❌ Tránh</span>'

    html += f"""                <tr>
                    <td><strong>{ticker}</strong></td>
                    <td class="{ret_class}">{m['return_30d']:+.2f}%</td>
                    <td>{m['volatility']:.2f}%</td>
                    <td>{m['trend'].capitalize()}</td>
                    <td>{badge}</td>
                </tr>
"""

html += """            </tbody>
        </table>
    </div>

    <div class="section">
        <div class="section-title">🎯 Top picks hôm nay</div>
"""

reasons = {
    'VCB': 'Ngân hàng lớn, trend tăng ổn định, volatility thấp. Phù hợp với nhà đầu tư bảo thủ.',
    'VIC': 'Đa ngành tập đoàn, return 30D mạnh, momentum tích cực. Nên theo dõi.',
    'VHM': 'Bất động sản, trend rõ ràng, volume tăng. Cơ hội ngắn hạn.',
    'HPG': 'Thép, return cao, risk quản lý tốt. Top performance.',
    'TCB': 'Ngân hàng thương mại, ổn định, return tốt. An toàn.',
}

for ticker in top_3:
    if ticker in metrics:
        reason = reasons.get(ticker, f"{ticker} có performance tốt, trend tích cực. Nên xem xét mua vào.")
        html += f"""        <div class="pick-item">
            <div class="pick-ticker">{ticker}</div>
            <div class="pick-reason">{reason}</div>
        </div>
"""

html += """    </div>

    <div class="section" style="font-size: 11px; color: #999; margin-top: 32px; padding-top: 16px; border-top: 1px solid #eee;">
        <p>Phân tích được tạo tự động. Không là lời khuyên đầu tư. Tham khảo các chuyên gia trước khi quyết định.</p>
    </div>
</div>
</body>
</html>
"""

report_path = f"data/reports/stock_report_{latest_date.strftime('%Y-%m-%d')}.html"
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✓ Report created: {report_path}")
print(f"✓ Metrics saved: data/pipeline/stock_metrics.json")
print(f"✓ Analysis date: {latest_date.strftime('%Y-%m-%d')}")
