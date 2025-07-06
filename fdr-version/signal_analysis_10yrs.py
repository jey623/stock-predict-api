from flask import Flask, request, jsonify
import pandas as pd
import FinanceDataReader as fdr
import ta
from xgboost import XGBRegressor
import datetime
import os

app = Flask(__name__)

def compute_technical_indicators(df):
    df = df.copy()
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
    model = XGBRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    last_feat = df.iloc[-1:][features].copy()
    preds = []
    for _ in range(days):
        p = model.predict(last_feat)[0]
        preds.append(p)
        last_feat.iloc[0, 0] = p  # 단순히 예측값을 RSI에 대입 (대체 아님)
    return preds

@app.route('/predict', methods=['GET'])
def predict():
    symbol = request.args.get('symbol')
    period = int(request.args.get('period', 5))
    period = max(1, min(period, 10))

    if not symbol:
        return jsonify({'error': 'symbol 파라미터가 필요합니다'}), 400

    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=365 * period)

    try:
        df = fdr.DataReader(symbol, start, end)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    if df.empty:
        return jsonify({'error': '데이터가 없습니다'}), 404

    df_ti = compute_technical_indicators(df)
    preds = predict_future(df_ti, days=5)

    latest = df_ti.iloc[-1][['RSI','CCI','OBV','Disparity','MA5','MA20','MA60','MA120']].to_dict()
    latest_close = df['Close'].iloc[-1]  # 현재가

    # 다음 5거래일 날짜 계산
    dates = []
    last_date = df.index[-1]
    cnt = 1
    while len(dates) < 5:
        next_day = last_date + datetime.timedelta(days=cnt)
        if next_day.weekday() < 5:
            dates.append(next_day.strftime('%Y-%m-%d'))
        cnt += 1

    return jsonify({
        '종목코드': symbol,
        '종목명': symbol,  # 종목명 자동 매핑 기능이 있다면 변경
        '기간_년': period,
        '현재가': round(float(latest_close), 2),
        '최신지표': {k: round(float(v), 4) for k, v in latest.items()},
        '예측종가_5일': [
            {'날짜': d, '예측종가': round(float(p), 2)}
            for d, p in zip(dates, preds)
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))

