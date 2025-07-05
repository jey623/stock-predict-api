# signal_analysis_kiwoom.py

from flask import Flask, request, jsonify
import pandas as pd
import FinanceDataReader as fdr
import talib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import datetime

app = Flask(__name__)

def get_technical_indicators(df):
    df = df.copy()
    df['RSI'] = talib.RSI(df['Close'], timeperiod=14)
    df['CCI'] = talib.CCI(df['High'], df['Low'], df['Close'], timeperiod=20)
    df['OBV'] = talib.OBV(df['Close'], df['Volume'])
    df['Disparity'] = df['Close'] / talib.MA(df['Close'], timeperiod=5) * 100
    df['MA5'] = talib.MA(df['Close'], timeperiod=5)
    df['MA20'] = talib.MA(df['Close'], timeperiod=20)
    df['MA60'] = talib.MA(df['Close'], timeperiod=60)
    df['MA120'] = talib.MA(df['Close'], timeperiod=120)
    return df.dropna()

def predict_next_prices(df, days=5):
    df = df.copy()
    df['Target'] = df['Close'].shift(-days)
    df = df.dropna()
    features = ['RSI','CCI','OBV','Disparity','MA5','MA20','MA60','MA120']
    X = df[features]
    y = df['Target']
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    last_row = df.iloc[-1:][features]
    preds = []
    for i in range(days):
        pred = model.predict(last_row)[0]
        preds.append(pred)
        # update features for next day
        last_row = last_row.shift(1)
        last_row.iloc[0] = pred
    start_date = df.index[-1]
    results = []
    for i, val in enumerate(preds, 1):
        next_date = (start_date + pd.Timedelta(days=i)).strftime('%Y-%m-%d')
        results.append({'날짜': next_date, '예측종가': float(val)})
    return results

@app.route('/full_analysis', methods=['GET'])
def full_analysis():
    symbol = request.args.get('symbol')
    period = int(request.args.get('period', 1))
    if not symbol:
        return jsonify({'error': 'symbol 파라미터가 필요합니다'}), 400
    if period < 1 or period > 10:
        return jsonify({'error': 'period는 1~10 사이의 정수여야 합니다'}), 400
    
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=365*period)
    try:
        df = fdr.DataReader(symbol, start, end)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    if df.empty:
        return jsonify({'error': '데이터 조회 실패'}), 404
    
    df_ti = get_technical_indicators(df)
    indicators = df_ti.iloc[-1][['RSI','CCI','OBV','Disparity','MA5','MA20','MA60','MA120']].to_dict()
    preds = predict_next_prices(df_ti, days=5)
    
    return jsonify({
        'symbol': symbol,
        'period_years': period,
        '기술지표': {k: float(v) for k, v in indicators.items()},
        '예측종가_5일': preds
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
