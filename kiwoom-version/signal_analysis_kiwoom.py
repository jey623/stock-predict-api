from flask import Flask, request, jsonify
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta

app = Flask(__name__)

# 분석 함수 정의
def analyze_signal(df):
    result = {}

    ma5 = df["Close"].rolling(window=5).mean()
    ma20 = df["Close"].rolling(window=20).mean()

    obv = [0]
    for i in range(1, len(df)):
        if df["Close"][i] > df["Close"][i - 1]:
            obv.append(obv[-1] + df["Volume"][i])
        elif df["Close"][i] < df["Close"][i - 1]:
            obv.append(obv[-1] - df["Volume"][i])
        else:
            obv.append(obv[-1])
    df["OBV"] = obv

    obv_trend = df["OBV"].iloc[-1] - df["OBV"].iloc[-5]
    price_trend = df["Close"].iloc[-1] - df["Close"].iloc[-5]

    if obv_trend > 0 and price_trend < 0:
        result['OBV_분석'] = "OBV 유지, 주가 하락 → 매집 가능성"
    elif obv_trend > 0:
        result['OBV_분석'] = "OBV 상승 → 세력 매집 중일 가능성"
    else:
        result['OBV_분석'] = "OBV 감소 → 세력 이탈 가능성"

    if ma5.iloc[-1] > ma20.iloc[-1] and ma5.iloc[-1] > ma5.iloc[-3] and ma20.iloc[-1] > ma20.iloc[-3]:
        result["이평선분석"] = "5일선 > 20일선, 둘 다 상승"
    else:
        result["이평선분석"] = "이평선 약세 또는 하락 전환"

    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    cci = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std())
    result["CCI"] = round(cci.iloc[-1], 2)

    candle = df.iloc[-1]
    body = abs(candle["Close"] - candle["Open"])
    avg_range = (df["High"] - df["Low"]).mean()
    is_bull_short = (candle["Close"] > candle["Open"]) and (body < avg_range * 0.5)
    is_bear = candle["Close"] < candle["Open"]
    result["캔들조건"] = "음봉 또는 짧은 양봉" if is_bull_short or is_bear else "비적합"

    future_returns = {}
    for day in range(1, 6):
        future_price = df["Close"].shift(-day)
        valid = ~future_price.isnull()
        returns = ((future_price[valid] - df["Close"][valid]) / df["Close"][valid]) * 100
        future_returns[f"{day}일"] = round(returns.mean(), 2)

    result["단기예측"] = future_returns

    return result

@app.route('/analyze', methods=['GET'])
def analyze_from_symbol():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "symbol 파라미터가 필요합니다"}), 400

    start_date = (datetime.now() - timedelta(days=3650)).strftime("%Y-%m-%d")
    df = fdr.DataReader(symbol, start=start_date)
    df = df.reset_index()

    try:
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        result = analyze_signal(df)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)


