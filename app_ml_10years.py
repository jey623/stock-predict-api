from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import ta
import xgboost as xgb
import os
from datetime import datetime, timedelta

app = Flask(__name__)

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

def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
    macd = ta.trend.MACD(close=df['Close'])
    df['MACD'] = macd.macd()
    df['Signal'] = macd.macd_signal()
    return df.dropna()

def train_and_predict(df):
    df = calculate_indicators(df)
    df['Target'] = df['Close'].shift(-1)
    df = df.dropna()

    X = df[['MA20', 'RSI', 'MACD', 'Signal']]
    y = df['Target']

    model = xgb.XGBRegressor()
    model.fit(X[:-1], y[:-1])  # 마지막은 테스트용
    prediction = model.predict(X[-1:].values)[0]
    return round(prediction, 2), int(df['Close'].iloc[-1])

@app.route("/predict", methods=["GET"])
def predict():
    stock = request.args.get("stock")
    code, name = get_stock_code(stock)
    if not code:
        return jsonify({"error": "Invalid stock name or code."}), 400

    start_date = (datetime.today() - timedelta(days=365 * 10)).strftime('%Y-%m-%d')
    df = fdr.DataReader(code, start=start_date)

    pred_price, current_price = train_and_predict(df)
    return jsonify({
        "종목명": name,
        "종목코드": code,
        "현재가": current_price,
        "내일 예측가": pred_price,
        "예상 변동": f"{round(pred_price - current_price, 2)}원"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)

