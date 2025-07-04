# 최종 버전: 수익률 기반 + 기술 지표 보조 조건 퀀트 스캐너

from datetime import datetime
import pandas as pd, FinanceDataReader as fdr, ta
from flask import Flask, jsonify

app = Flask(__name__)
krx = fdr.StockListing("KRX")

def _code2name(code):
    return krx.loc[krx["Code"] == code, "Name"].squeeze()

def analyze_stock(code):
    try:
        df = fdr.DataReader(code, start="2014-01-01").dropna()
        cur = float(df["Close"].iloc[-1])

        # 기본 수익률 계산
        future = df["Close"].shift(-5)
        valid = ~future.isna()
        returns = ((future[valid] - df["Close"][valid]) / df["Close"][valid]) * 100
        if returns.empty:
            return None

        avg_ret = round(returns.mean(), 2)
        if avg_ret < 3:
            return None  # 5일 수익률이 3% 미만이면 제외

        # 기술 지표 보조 조건
        df = df.copy()
        df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
        df["OBV"] = ta.volume.OnBalanceVolumeIndicator(df["Close"], df["Volume"]).on_balance_volume()

        rsi = df["RSI"].iloc[-1]
        obv_trend = df["OBV"].rolling(window=3).mean().iloc[-1] - df["OBV"].rolling(window=3).mean().iloc[-2]

        # RSI 과열 제외, OBV 하락 제외
        if rsi > 70 or obv_trend < 0:
            return None

        return {
            "code": code,
            "name": _code2name(code),
            "close": cur,
            "5일예상수익률(%)": avg_ret,
            "RSI": round(rsi, 2),
            "OBV추세": round(obv_trend, 2)
        }
    except:
        return None

def scan_stocks():
    results = []
    for code in krx["Code"][:300]:
        r = analyze_stock(code)
        if r:
            results.append(r)

    # 수익률 기준 정렬
    results.sort(key=lambda x: x["5일예상수익률(%)"], reverse=True)
    return results[:10]

@app.route("/scan")
def api_scan():
    data = scan_stocks()
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

