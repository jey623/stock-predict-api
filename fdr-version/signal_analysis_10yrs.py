from flask import Flask, request, jsonify
import pandas as pd
import FinanceDataReader as fdr
import ta
from xgboost import XGBRegressor
import datetime
import os

app = Flask(__name__)

# 종목명 → 코드, 코드 → 종목명 매핑 생성
krx = fdr.StockListing("KRX")
name_to_code = krx.set_index("Name")["Code"].to_dict()
code_to_name = krx.set_index("Code")["Name"].to_dict()

def resolve_symbol(symbol):
    """종목명 → 코드 변환"""
    return symbol if symbol.isdigit() else name_to_code.get(symbol)

def compute_indicators(df):
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

def predict_next_5_days(df_ti):
    df = df_ti.copy()
    df['Target'] = df['Close'].shift(-5)
    df = df.dropna()
    features = ['RSI','CCI','OBV','Disparity','MA5','MA20','MA60','MA120']
    X, y = df[features], df['Target']

    model = XGBRegressor(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        objective='reg:squarederror',
        random_state=42,
        verbosity=0
    )
    model.fit(X, y)

    last = df.iloc[-1:][features]
    preds = []
    for _ in range(5):
        p = model.predict(last)[0]
        preds.append(p)
        last.iloc[0, features.index('MA5')] = p
        last.iloc[0, features.index('MA20')] = p
        last.iloc[0, features.index('MA60')] = p
        last.iloc[0, features.index('MA120')] = p
    return preds

@app.route('/')
def home():
    return '📈 Stock Prediction API is running. Try /predict?symbol=삼성전자'

@app.route('/predict', methods=['GET'])
def predict():
    symbol_input = request.args.get('symbol')
    period_years = int(request.args.get('period', 5))

    if not symbol_input:
        return jsonify({'error': 'symbol 파라미터가 필요합니다'}), 400

    symbol = resolve_symbol(symbol_input)
    if not symbol:
        return jsonify({'error': f'종목명 또는 코드 "{symbol_input}"을 찾을 수 없습니다'}), 404

    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=365 * period_years)

    try:
        df = fdr.DataReader(symbol, start, end)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    if df.empty:
        return jsonify({'error': '데이터가 없습니다'}), 404

    df_ti = compute_indicators(df)
    preds = predict_next_5_days(df_ti)

    latest = df_ti.iloc[-1][['RSI','CCI','OBV','Disparity','MA5','MA20','MA60','MA120']].to_dict()
    last_date = df_ti.index[-1]
    dates = []
    i = 1
    while len(dates) < 5:
        d = last_date + datetime.timedelta(days=i)
        if d.weekday() < 5:
            dates.append(d.strftime('%Y-%m-%d'))
        i += 1

    return jsonify({
        'symbol': symbol,
        'symbol_name': code_to_name.get(symbol, 'Unknown'),
        'period_years': period_years,
        'latest_indicators': {k: float(v) for k, v in latest.items()},
        'predicted_close_next_5': [
            {'date': d, 'predicted_close': float(p)}
            for d, p in zip(dates, preds)
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))

