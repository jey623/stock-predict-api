# signal_analysis_kiwoom.py
from flask import Flask, request, jsonify
import pandas as pd
import FinanceDataReader as fdr
import ta
from sklearn.ensemble import RandomForestRegressor
import datetime
import os

app = Flask(__name__)

def get_technical_indicators(df):
    df = df.copy()
    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
    df['CCI'] = ta.trend.CCIIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=20).cci()
    df['OBV'] = ta.volume.OnBalanceVolumeIndicator(close=df['Close'], volume=df['Volume']).on_balance_volume()
    df['Disparity'] = df['Close'] / df['Close'].rolling(window=5).mean() * 100
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    return df.dropna()

def predict_next_prices(df, days=5):
    df = df.copy()
    df['Target'] = df['Close'].shift(-1)
    df = df.dropna()
    features = ['RSI','CCI','OBV','Disparity','MA5','MA20','MA60','MA120']
    X = df[features]
    y = df['Target']
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    last_row = df.iloc[-1:][features].copy()
    preds = []
    next_date = df.index[-1]
    for _ in range(days):
        pred = model.predict(last_row)[0]
        preds.append({'날짜': next_date.strftime('%Y-%m-%d'), '예측종가': int(pred)})
        next_date = pd.date_range(next_date, periods=2, freq='B')[1]
        last_row.iloc[0] = pred
    return preds

@app.route('/full_analysis', methods=['GET'])
def full_analysis():
    symbol = request.args.get('symbol')
    period = int(request.args.get('period', 1))
    if not symbol:
        return jsonify({'error': 'symbol 파라미터가 필요합니다'}), 400
    if period < 1 or period > 10:
        return jsonify({'error': 'period는 1~10 사이의 정수여야 합니다'}), 400

    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=365 * period)
    try:
        df = fdr.DataReader(symbol, start, end)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    if df.empty:
        return jsonify({'error': '데이터 조회 실패'}), 404

    df_ti = get_technical_indicators(df)
    indicators = df_ti[['RSI','CCI','OBV','Disparity','MA5','MA20','MA60','MA120']].dropna().tail(30)
    preds = predict_next_prices(df_ti, days=5)

    return jsonify({
        'symbol': symbol,
        'period_years': period,
        '기술지표_최근30일': indicators.reset_index().to_dict(orient='records'),
        '예측종가_5거래일': preds
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))


