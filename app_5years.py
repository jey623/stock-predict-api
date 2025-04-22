from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import ta
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
import os

app = Flask(__name__)

# 종목코드 변환 함수
def get_stock_code(name_or_code):
    try:
        stock_list = fdr.StockListing('KRX')
        if name_or_code.isdigit():
            row = stock_list[stock_list['Code'] == name_or_code]
        else:
            row = stock_list[stock_list['Name'] == name_or_code]
        if not row.empty:
            return row.iloc[0]['Code'], row.iloc[0]['Name']
        else:
            return None, None
    except:
        return None, None

# 고급 기술적 지표 10개 계산
def add_features(df):
    df['MA20'] = ta.trend.SMAIndicator(df['Close'], window=20).sma_indicator()
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    adx = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14)
    df['+DI'] = adx.adx_pos()
    df['-DI'] = adx.adx_neg()
    tsf = ta.trend.EMAIndicator(close=df['Close'], window=10)
    df['TSF'] = tsf.ema_indicator()
    bb = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['Bollinger_High'] = bb.bollinger_hband()
    df['Bollinger_Low'] = bb.bollinger_lband()
    df['Envelope_High'] = df['MA20'] * 1.02
    df['Envelope_Low'] = df['MA20'] * 0.98
    return df.dropna()

# 시퀀스 데이터 생성
def create_sequences(data, window_size, horizon_list):
    X, Y_dict = [], {h: [] for h in horizon_list}
    for i in range(len(data) - window_size - max(horizon_list)):
        seq_x = data[i:i+window_size]
        X.append(seq_x)
        for h in horizon_list:
            Y_dict[h].append(data[i+window_size+h-1][0])  # 종가 예측
    return np.array(X), {h: np.array(Y) for h, Y in Y_dict.items()}

# 모델 생성
def build_model(input_shape):
    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=input_shape),
        LSTM(64),
        Dense(32, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
    return model

# 기술적 지표 API
@app.route("/get_indicators", methods=["GET"])
def get_indicators():
    stock = request.args.get("stock")
    code, name = get_stock_code(stock)
    if not code:
        return jsonify({"error": "Invalid stock name or code."}), 400

    df = fdr.DataReader(code, start='2014-01-01')
    df = add_features(df)
    latest = df.iloc[-1]

    return jsonify({
        "종목명": name,
        "종목코드": code,
        "날짜": latest.name.strftime("%Y-%m-%d"),
        "현재가": float(round(latest["Close"], 2)),
        "MA20": float(round(latest["MA20"], 2)),
        "RSI": float(round(latest["RSI"], 2)),
        "MACD": float(round(latest["MACD"], 2)),
        "+DI": float(round(latest["+DI"], 2)),
        "-DI": float(round(latest["-DI"], 2)),
        "TSF": float(round(latest["TSF"], 2)),
        "Bollinger_High": float(round(latest["Bollinger_High"], 2)),
        "Bollinger_Low": float(round(latest["Bollinger_Low"], 2)),
        "Envelope_High": float(round(latest["Envelope_High"], 2)),
        "Envelope_Low": float(round(latest["Envelope_Low"], 2))
    })

# 예측 API
@app.route("/predict_lstm", methods=["GET"])
def predict_lstm():
    stock = request.args.get("stock")
    code, name = get_stock_code(stock)
    if not code:
        return jsonify({"error": "Invalid stock name or code."}), 400

    df = fdr.DataReader(code, start='2014-01-01')
    df = add_features(df)[['Close', 'MA20', 'RSI', 'MACD', '+DI', '-DI', 'TSF',
                           'Bollinger_High', 'Bollinger_Low', 'Envelope_High', 'Envelope_Low']]
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df)

    window_size = 60
    horizon_list = [1, 5, 20, 40, 60]
    X, Y_dict = create_sequences(scaled, window_size, horizon_list)

    if len(X) == 0:
        return jsonify({"error": "Not enough data for prediction."}), 400

    predictions = {}
    for h in horizon_list:
        model = build_model((window_size, X.shape[2]))
        model.fit(X, Y_dict[h], epochs=50, batch_size=16, verbose=0)
        pred = model.predict(X[-1].reshape(1, window_size, X.shape[2]))
        pred_price = scaler.inverse_transform(
            np.concatenate([pred, np.zeros((1, scaled.shape[1] - 1))], axis=1)
        )[0][0]
        true_price = scaler.inverse_transform(
            np.concatenate([Y_dict[h][-1].reshape(1, 1), np.zeros((1, scaled.shape[1] - 1))], axis=1)
        )[0][0]
        predictions[f"{h}일후"] = {
            "예측가": float(round(pred_price, 2)),
            "실제가": float(round(true_price, 2)),
            "오차": float(round(abs(pred_price - true_price), 2))
        }

    return jsonify({
        "종목명": name,
        "종목코드": code,
        "예측결과": predictions
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)


