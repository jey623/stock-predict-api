# signal_analysis_kiwoom_v2.py
from flask import Flask, request, jsonify
import pandas as pd
import FinanceDataReader as fdr
import ta
from sklearn.ensemble import RandomForestRegressor
import datetime
import os

app = Flask(__name__)

def compute_technical_indicators(df):
    df = df.copy()
    # RSI, CCI, OBV, Disparity, 이동평균
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
    df['CCI'] = ta.trend.CCIIndicator(df['High'], df['Low'], df['Close'], window=20).cci()
    df['OBV'] = ta.volume.OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()
    df['Disparity'] = df['Close'] / df['Close'].rolling(5).mean() * 100
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    df['MA120'] = df['Close'].rolling(120).mean()
    return df.dropna()

def predict_future(df_ti, days=5):
    df = df_ti.copy()
    df['Target'] = df['Close'].shift(-days)
    df = df.dropna()
    features = ['RSI','CCI','OBV','Disparity','MA5','MA20','MA60','MA120']
    X, y = df[features], df['Target']
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    last_feat = df.iloc[-1:][features].copy()
    preds = []
    for i in range(days):
        p = model.predict(last_feat)[0]
        preds.append(p)
        last_feat.iloc[0] = p  # 최근 피처에 예측가 반영 (단, 단순 대입)
    return preds

@app.route('/full_analysis', methods=['GET'])
def full_analysis():
    symbol = request.args.get('symbol')
    period = int(request.args.get('period', 5))
    period = max(1, min(period, 10))
    if not symbol:
        return jsonify({'error': 'symbol 파라미터가 필요합니다'}), 400

    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=365*period)
    try:
        df = fdr.DataReader(symbol, start, end)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    if df.empty:
        return jsonify({'error': '데이터가 없습니다'}), 404

    df_ti = compute_technical_indicators(df)
    preds = predict_future(df_ti, days=5)

    # 오늘 기준 최신 피처들
    latest = df_ti.iloc[-1][['RSI','CCI','OBV','Disparity','MA5','MA20','MA60','MA120']].to_dict()

    dates = []
    last_date = df_ti.index[-1]
    cnt = 0
    while len(dates) < 5:
        next_day = last_date + datetime.timedelta(days=1 + cnt)
        if next_day.weekday() < 5:  # 평일만
            dates.append(next_day.strftime('%Y-%m-%d'))
        cnt += 1

    return jsonify({
        'symbol': symbol,
        'period_years': period,
        'latest_indicators': {k: float(v) for k, v in latest.items()},
        'predicted_close_next_5': [
            {'date': d, 'predicted_close': float(p)}
            for d, p in zip(dates, preds)
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))


