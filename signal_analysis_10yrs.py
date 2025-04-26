import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from ta.momentum import RSIIndicator
from ta.trend import CCIIndicator, ADXIndicator
from flask import Flask, request, jsonify

app = Flask(__name__)

def calculate_technical_indicators(df):
    df['CCI'] = CCIIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=9).cci()
    df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
    adx = ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=17)
    df['DI+'] = adx.adx_pos()
    df['DI-'] = adx.adx_neg()
    df['ADX'] = adx.adx()

    envelope_down = df['Close'].rolling(window=20).mean() * (1 - 0.12)
    df['EnvelopeDown'] = envelope_down
    df['LowestEnvelope'] = envelope_down.rolling(window=5).min()
    df['LowestC'] = df['Close'].rolling(window=5).min()
    return df

def detect_signals(df):
    HighTop = 41
    LowBottom = 5
    signal = (
        (df['CCI'] < -100) &
        (df['RSI'] < 30) &
        (df['DI-'] > HighTop) &
        ((df['DI-'] < df['ADX']) | (df['DI+'] < LowBottom)) &
        (df['LowestEnvelope'] > df['LowestC'])
    )
    df['Signal'] = signal
    signal_dates = df[signal].index.strftime('%Y-%m-%d').tolist()
    latest_signal = signal.iloc[-1] if not signal.empty else False
    return df, bool(latest_signal), signal_dates

@app.route("/analyze", methods=["GET"])
def analyze():
    symbol = request.args.get("symbol", "")
    if not symbol:
        return jsonify({"error": "No symbol provided"}), 400

    try:
        df = fdr.DataReader(symbol)
        df = df[-2520:].copy()
        df = calculate_technical_indicators(df)
        df, signal_triggered, signal_dates = detect_signals(df)

        current_price = df['Close'].iloc[-1]
        forecast_days = [1, 5, 10, 20, 40, 60, 80]
        predicted_prices = {}
        predicted_changes = {}

        for day in forecast_days:
            if len(df) > day:
                future_price = df['Close'].iloc[-1] * (1 + 0.002 * day)  # dummy model
                predicted_prices[f"{day}일"] = round(future_price, 2)
                predicted_changes[f"{day}일"] = round((future_price - current_price) / current_price * 100, 2)

        result = {
            "종목명": symbol,
            "종목코드": df.iloc[-1].name.strftime('%Y%m%d'),
            "현재가": round(current_price, 2),
            "예측가": predicted_prices,
            "변화율": predicted_changes,
            "신호발생": signal_triggered,
            "신호발생일자": signal_dates
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return "📈 Signal Analysis API is running."

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

