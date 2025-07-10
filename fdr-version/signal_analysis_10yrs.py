from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
import numpy as np

app = Flask(__name__)

# 종목명 → 코드 자동 변환 함수
def name_to_code(name):
    kospi = fdr.StockListing('KOSPI')
    kosdaq = fdr.StockListing('KOSDAQ')
    all_stocks = pd.concat([kospi, kosdaq])
    match = all_stocks[all_stocks['Name'] == name]
    if not match.empty:
        return match.iloc[0]['Code']
    return None

# ARIMA 모델 예측 함수 (향후 10일)
def predict_arima(ts, periods=10):
    ts = ts.dropna()
    model = ARIMA(ts, order=(5, 1, 0))  # 단순 예시: (p,d,q) = (5,1,0)
    model_fit = model.fit()
    forecast = model_fit.forecast(steps=periods)
    return forecast.tolist()

# 백테스트: 10년 데이터에서 10일 내 +3% 수익 성공률 계산
def backtest_success_rate(ts, threshold=0.03, window=10):
    ts = ts.dropna().reset_index(drop=True)
    success = 0
    total = len(ts) - window
    for i in range(total):
        base = ts[i]
        future_window = ts[i+1:i+1+window]
        if any((future_window - base) / base >= threshold):
            success += 1
    rate = (success / total) * 100 if total > 0 else 0
    return round(rate, 2)

@app.route('/predict', methods=['GET'])
def predict():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({'error': 'symbol 카목이 필요합니다.'}), 400

    # 종목명이면 코드로 변환
    if not symbol.isdigit():
        converted = name_to_code(symbol)
        if converted:
            symbol = converted
        else:
            return jsonify({'error': f'\uc885\ubaa9\uba85 \ubc1c\uacac \ubd88\uac00: {symbol}'}), 400

    try:
        end = pd.Timestamp.today()
        start = end - pd.DateOffset(years=10)
        df = fdr.DataReader(symbol, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        df = df.dropna()

        ts = df['Close']

        # ARIMA 예측
        forecast = predict_arima(ts, periods=10)
        forecast_dates = pd.date_range(start=df.index[-1] + pd.Timedelta(days=1), periods=10, freq='B')
        forecast_data = [
            {"date": d.strftime('%Y-%m-%d'), "predicted_close": round(p, 2)}
            for d, p in zip(forecast_dates, forecast)
        ]

        # 백테스트: 10일 내 +3% 도달 성공률
        success_rate = backtest_success_rate(ts, threshold=0.03, window=10)

        # 현재가 가져오기 (가장 최신 종가)
        current_price = round(ts.iloc[-1], 2)

        return jsonify({
            'symbol': symbol,
            'latest_date': df.index[-1].strftime('%Y-%m-%d'),
            'latest_close': current_price,
            'current_price': current_price,
            'forecast': forecast_data,
            'success_rate_3pct_10days': success_rate
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


