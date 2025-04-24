import pandas as pd
import FinanceDataReader as fdr
import ta
import numpy as np
from flask import Flask, request, jsonify

app = Flask(__name__)

krx = fdr.StockListing('KRX')

def get_code_by_name(name):
    row = krx[krx['Name'] == name]
    return row['Code'].values[0] if not row.empty else None

def get_name_by_code(code):
    row = krx[krx['Code'] == code]
    return row['Name'].values[0] if not row.empty else None

def analyze_stock(input_value):
    if input_value.isdigit():
        code = input_value
        name = get_name_by_code(code)
    else:
        name = input_value
        code = get_code_by_name(name)

    if not code:
        return {"error": "❌ 유효하지 않은 종목명 또는 코드입니다."}

    df = fdr.DataReader(code, start='2014-01-01')

    # 기술적 지표 계산
    for window in [5, 10, 20, 40, 60]:
        df[f"MA{window}"] = df["Close"].rolling(window=window).mean()

    df["RSI"] = ta.momentum.RSIIndicator(close=df["Close"], window=14).rsi()
    macd = ta.trend.MACD(close=df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["BB_upper"] = ta.volatility.BollingerBands(close=df["Close"]).bollinger_hband()
    df["BB_lower"] = ta.volatility.BollingerBands(close=df["Close"]).bollinger_lband()
    df["Envelope_high"] = df["MA20"] * 1.03
    df["Envelope_low"] = df["MA20"] * 0.97

    # ✅ 사용자 신호검색 수식 (유지)
    df["Signal_Triggered"] = (
        (df["MA5"] > df["MA20"]) &
        (df["MA5"].shift(1) <= df["MA20"].shift(1)) &
        (df["RSI"] < 30)
    )

    latest = df.iloc[-1]
    signal = bool(latest["Signal_Triggered"])
    current_price = float(latest["Close"])

    # ✅ 전체 데이터 기반 예측
    future_prices = {}
    change_rates = {}
    periods = [1, 5, 10, 20, 40, 60, 80]

    for p in periods:
        returns = []
        for i in df.index:
            future_idx = df.index.get_indexer([i + pd.Timedelta(days=p)], method='nearest')[0]
            if 0 <= future_idx < len(df):
                buy = df.loc[i, "Close"]
                future = df.iloc[future_idx]["Close"]
                change = (future - buy) / buy * 100
                returns.append(change)

        if returns:
            avg_return = round(np.mean(returns), 2)
            predicted_price = round(current_price * (1 + avg_return / 100), 2)
            future_prices[f"{p}일"] = predicted_price
            change_rates[f"{p}일"] = avg_return

    return {
        "종목명": name,
        "종목코드": code,
        "현재가": current_price,
        "예측가": future_prices,
        "변화율": change_rates,
        "신호발생": signal
    }

@app.route('/')
def index():
    return '📈 Signal Analysis API is running.'

@app.route('/analyze', methods=['GET'])
def analyze():
    symbol = request.args.get('symbol', '삼성전자')
    result = analyze_stock(symbol)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)

