from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import ta

app = Flask(__name__)

# 🧠 종목명 → 종목코드 매핑
def get_stock_code(stock_name):
    try:
        stock_list = fdr.StockListing('KRX')
        code = stock_list.loc[stock_list['Name'] == stock_name, 'Code'].values[0]
        return code
    except:
        return None

# 📊 기술적 지표 계산 함수
def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['RSI'] = ta.momentum.RSIIndicator(df['Close']).rsi()
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['Signal'] = macd.macd_signal()
    df.dropna(inplace=True)
    return df

@app.route('/get_indicators', methods=['GET'])
def get_indicators():
    stock_name = request.args.get('stock')
    if not stock_name:
        return jsonify({"error": "stock 파라미터를 입력해주세요."}), 400

    code = get_stock_code(stock_name)
    if not code:
        return jsonify({"error": f"{stock_name}의 종목코드를 찾을 수 없습니다."}), 404

    try:
        df = fdr.DataReader(code, start='2022-01-01')
        df = calculate_indicators(df)
        latest = df.iloc[-1]

        result = {
            "종목명": stock_name,
            "종목코드": code,
            "날짜": str(latest.name.date()),
            "현재가": int(latest["Close"]),
            "MA20": round(latest["MA20"], 2),
            "MA60": round(latest["MA60"], 2),
            "RSI": round(latest["RSI"], 2),
            "MACD": round(latest["MACD"], 2),
            "신호선": round(latest["Signal"], 2)
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
