import os
import json
import pandas as pd
import numpy as np
import tensorflow as tf
from flask import Flask, request, jsonify
from sklearn.preprocessing import MinMaxScaler
from ta.trend import MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import FinanceDataReader as fdr

app = Flask(__name__)

def get_stock_code(name_or_code):
    stock_list = fdr.StockListing('KRX')
    if name_or_code.isdigit():
        return name_or_code
    row = stock_list[stock_list['Name'] == name_or_code]
    if not row.empty:
        return row.iloc[0]['Code']
    else:
        return None

def get_stock_name(code):
    stock_list = fdr.StockListing('KRX')
    row = stock_list[stock_list['Code'] == code]
    if not row.empty:
        return row.iloc[0]['Name']
    else:
        return code

def get_technical_indicators(df):
    indicators = {}
    indicators["MA20"] = df["Close"].rolling(window=20).mean()
    indicators["MA40"] = df["Close"].rolling(window=40).mean()
    indicators["MA60"] = df["Close"].rolling(window=60).mean()

    macd = MACD(close=df["Close"])
    indicators["MACD"] = macd.macd()
    indicators["Signal"] = macd.macd_signal()

    rsi = RSIIndicator(close=df["Close"], window=14)
    indicators["RSI"] = rsi.rsi()

    boll = BollingerBands(close=df["Close"], window=20)
    indicators["Bollinger_High"] = boll.bollinger_hband()
    indicators["Bollinger_Low"] = boll.bollinger_lband()

    adx = ADXIndicator(high=df["High"], low=df["Low"], close=df["Close"])
    indicators["+DI"] = adx.adx_pos()
    indicators["-DI"] = adx.adx_neg()
    indicators["ADX"] = adx.adx()

    envelope_pct = 0.02
    indicators["Envelope_High"] = indicators["MA20"] * (1 + envelope_pct)
    indicators["Envelope_Low"] = indicators["MA20"] * (1 - envelope_pct)

    indicators["TSF"] = df["Close"].rolling(window=10).apply(lambda x: np.poly1d(np.polyfit(range(len(x)), x, 1))(len(x) - 1))

    df_ind = pd.DataFrame(indicators)
    return df_ind

def make_predictions(data, feature_col, days_ahead=1):
    dataset = data[feature_col].values.reshape(-1, 1)
    scaler = MinMaxScaler()
    dataset_scaled = scaler.fit_transform(dataset)

    X = []
    for i in range(len(dataset_scaled) - 60 - days_ahead + 1):
        X.append(dataset_scaled[i:i+60])

    X = np.array(X)
    model = tf.keras.models.Sequential([
        tf.keras.layers.LSTM(units=50, return_sequences=True, input_shape=(X.shape[1], X.shape[2])),
        tf.keras.layers.LSTM(units=50),
        tf.keras.layers.Dense(units=1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    model.fit(X, dataset_scaled[60+days_ahead-1:], epochs=5, batch_size=32, verbose=0)

    last_sequence = dataset_scaled[-60:].reshape(1, 60, 1)
    prediction_scaled = model.predict(last_sequence)
    prediction = scaler.inverse_transform(prediction_scaled)
    return float(prediction[0][0])

@app.route('/predict_lstm', methods=['GET'])
def predict_lstm():
    stock_input = request.args.get('stock')
    code = get_stock_code(stock_input)
    if not code:
        return jsonify({'error': '종목명을 찾을 수 없습니다.'})

    df = fdr.DataReader(code, start='2014-01-01')
    if 'Close' not in df.columns:
        return jsonify({'error': "'Close' 컬럼이 없습니다."})

    df = df.dropna()
    df_ind = get_technical_indicators(df)
    df = pd.concat([df, df_ind], axis=1).dropna()

    result = {}
    for days in [1, 2, 5, 10, 20, 40, 60]:  # ✅ 2일 후 예측도 포함됨
        pred = make_predictions(df, 'Close', days_ahead=days)
        real = df['Close'].iloc[-1]
        result[f'{days}일후'] = {
            '예측가': round(pred, 2),
            '실제가': round(real, 2),
            '오차': round(abs(pred - real), 2)
        }

    return jsonify({
        '종목명': get_stock_name(code),
        '종목코드': code,
        '예측결과': result
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host='0.0.0.0', port=port)

