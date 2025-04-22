import os
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from flask import Flask, request, jsonify
from ta.trend import MACD, SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from ta.trend import ADXIndicator
from ta.trend import CCIIndicator
from ta.trend import PSARIndicator
from ta.trend import EMAIndicator
from ta.trend import WMAIndicator
from ta.trend import STCIndicator
from ta.trend import KSTIndicator
from ta.trend import DPOIndicator
from ta.trend import VortexIndicator
from ta.trend import IchimokuIndicator
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

app = Flask(__name__)

def get_stock_data(stock_code):
    df = fdr.DataReader(stock_code, start='2014-01-01')
    df = df.dropna()
    return df

def add_indicators(df):
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA40'] = df['Close'].rolling(window=40).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
    macd = MACD(close=df['Close'])
    df['MACD'] = macd.macd_diff()
    bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
    df['Bollinger_High'] = bb.bollinger_hband()
    df['Bollinger_Low'] = bb.bollinger_lband()
    df['Envelope_High'] = df['MA20'] * 1.02
    df['Envelope_Low'] = df['MA20'] * 0.98
    adx = ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
    df['ADX'] = adx.adx()
    df['+DI'] = adx.adx_pos()
    df['-DI'] = adx.adx_neg()
    df['TSF'] = df['Close'].rolling(window=5).mean()  # 간이 TSF 흉내
    return df

def create_lstm_model(input_shape):
    model = Sequential()
    model.add(LSTM(64, input_shape=input_shape))
    model.add(Dense(1))
    model.compile(optimizer='adam', loss='mse')
    return model

def predict_future_prices(df, days_list):
    df = add_indicators(df)
    df = df.dropna()

    features = ['Close', 'MA20', 'MA40', 'MA60', 'RSI', 'MACD', 'Bollinger_High',
                'Bollinger_Low', 'Envelope_High', 'Envelope_Low', 'ADX', '+DI', '-DI', 'TSF']

    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df[features])
    X = []
    y = []

    for i in range(60, len(scaled_data)):
        X.append(scaled_data[i-60:i])
        y.append(scaled_data[i][0])

    X = np.array(X)
    y = np.array(y)

    model = create_lstm_model((X.shape[1], X.shape[2]))
    model.fit(X, y, epochs=10, batch_size=32, verbose=0)

    predictions = {}
    for days in days_list:
        future_input = scaled_data[-60:].copy()
        for _ in range(days):
            input_seq = np.expand_dims(future_input[-60:], axis=0)
            pred = model.predict(input_seq, verbose=0)[0][0]
            next_row = future_input[-1].copy()
            next_row[0] = pred
            future_input = np.vstack([future_input, next_row])

        predicted_scaled_price = future_input[-1][0]
        predicted_price = scaler.inverse_transform([[predicted_scaled_price] + [0]*(len(features)-1)])[0][0]
        real_price = df['Close'].iloc[-1]  # 실제 현재가
        predictions[f'{days}일후'] = {
            '예측가': round(predicted_price, 2),
            '실제가': round(real_price, 2),
            '오차': round(abs(real_price - predicted_price), 2)
        }

    return predictions

@app.route('/predict_lstm', methods=['GET'])
def predict_lstm():
    stock = request.args.get('stock')
    try:
        df = get_stock_data(stock)
        preds = predict_future_prices(df, [1, 5, 20, 40, 60])
        return jsonify({
            '종목명': stock,
            '종목코드': stock,
            '예측결과': preds
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/get_indicators', methods=['GET'])
def get_indicators():
    stock = request.args.get('stock')
    try:
        df = get_stock_data(stock)
        df = add_indicators(df)
        latest = df.iloc[-1]
        return jsonify({
            '종목명': stock,
            '종목코드': stock,
            '현재가': round(latest['Close'], 2),
            '날짜': str(latest.name.date()),
            'MA20': round(latest['MA20'], 2),
            'MA40': round(latest['MA40'], 2),
            'MA60': round(latest['MA60'], 2),
            'RSI': round(latest['RSI'], 2),
            'MACD': round(latest['MACD'], 2),
            'Bollinger_High': round(latest['Bollinger_High'], 2),
            'Bollinger_Low': round(latest['Bollinger_Low'], 2),
            'Envelope_High': round(latest['Envelope_High'], 2),
            'Envelope_Low': round(latest['Envelope_Low'], 2),
            'ADX': round(latest['ADX'], 2),
            '+DI': round(latest['+DI'], 2),
            '-DI': round(latest['-DI'], 2),
            'TSF': round(latest['TSF'], 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# ✅ Render에서 포트 자동 인식되게 아래 설정 필수
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))


