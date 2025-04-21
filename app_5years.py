from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import ta
import os

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
    df['MA40'] = df['Close'].rolling(window=40).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
    macd = ta.trend.MACD(close=df['Close'])
    df['MACD'] = macd.macd()
    df['Signal'] = macd.macd_signal()

    # 볼린저 밴드
    bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
    df['Bollinger_High'] = bb.bollinger_hband()
    df['Bollinger_Low'] = bb.bollinger_lband()

    # 엔벨로프
    df['Envelope_High'] = df['MA20'] * 1.02
    df['Envelope_Low'] = df['MA20'] * 0.98

    # ADX 및 DI
    adx = ta.trend.ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
    df['ADX'] = adx.adx()
    df['+DI'] = adx.adx_pos()
    df['-DI'] = adx.adx_neg()

    # TSF (EMA 대체)
    tsf = ta.trend.EMAIndicator(close=df['Close'], window=10)
    df['TSF'] = tsf.ema_indicator()

    return df

@app.route("/get_indicators", methods=["GET"])
def get_indicators():
    stock = request.args.get("stock")
    code, name = get_stock_code(stock)
    if not code:
        return jsonify({"error": "Invalid stock name or code."}), 400

    df = fdr.DataReader(code, start='2020-01-01')
    df = calculate_indicators(df)
    latest = df.dropna().iloc[-1]

    return jsonify({
        "종목명": name,
        "종목코드": code,
        "날짜": latest.name.strftime("%Y-%m-%d"),
        "현재가": int(latest["Close"]),
        "MA20": round(latest["MA20"], 2),
        "MA40": round(latest["MA40"], 2),
        "MA60": round(latest["MA60"], 2),
        "RSI": round(latest["RSI"], 2),
        "MACD": round(latest["MACD"], 2),
        "신호선": round(latest["Signal"], 2),
        "Bollinger_High": round(latest["Bollinger_High"], 2),
        "Bollinger_Low": round(latest["Bollinger_Low"], 2),
        "Envelope_High": round(latest["Envelope_High"], 2),
        "Envelope_Low": round(latest["Envelope_Low"], 2),
        "ADX": round(latest["ADX"], 2),
        "+DI": round(latest["+DI"], 2),
        "-DI": round(latest["-DI"], 2),
        "TSF": round(latest["TSF"], 2)
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)

