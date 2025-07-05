# 최종버전: 통계 + 기술지표(CCI, MA 5/20/60/120 포함) 기반 확률 분석

from datetime import datetime
import pandas as pd, FinanceDataReader as fdr, ta
from flask import Flask, request, jsonify

app = Flask(__name__)
krx = fdr.StockListing("KRX")

def _code2name(code):
    return krx.loc[krx["Code"] == code, "Name"].squeeze()

def _name2code(name):
    return krx.loc[krx["Name"] == name, "Code"].squeeze()

def analyze_stock_prob(code):
    try:
        df = fdr.DataReader(code, start="2014-01-01").dropna().copy()
        df.reset_index(inplace=True)

        count_total = 0
        count_take = 0
        count_stop = 0

        for i in range(len(df) - 5):
            entry = df.loc[i, "Close"]
            high5 = df.loc[i+1:i+5, "High"].max()
            low5 = df.loc[i+1:i+5, "Low"].min()

            target_up = entry * 1.03
            target_down = entry * 0.97

            count_total += 1
            if high5 >= target_up:
                count_take += 1
            if low5 <= target_down:
                count_stop += 1

        prob_take = round((count_take / count_total) * 100, 2)
        prob_stop = round((count_stop / count_total) * 100, 2)

        # 기술 지표 추가
        df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
        df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"], window=20).cci()
        df["OBV"] = ta.volume.OnBalanceVolumeIndicator(df["Close"], df["Volume"]).on_balance_volume()
        df["MA5"] = df["Close"].rolling(window=5).mean()
        df["MA20"] = df["Close"].rolling(window=20).mean()
        df["MA60"] = df["Close"].rolling(window=60).mean()
        df["MA120"] = df["Close"].rolling(window=120).mean()

        rsi = round(df["RSI"].iloc[-1], 2)
        cci = round(df["CCI"].iloc[-1], 2)
        obv_trend = df["OBV"].iloc[-1] - df["OBV"].iloc[-2]
        golden = df["MA5"].iloc[-1] > df["MA20"].iloc[-1]
        dead = df["MA5"].iloc[-1] < df["MA20"].iloc[-1]

        cur = float(df["Close"].iloc[-1])
        ma60 = round(df["MA60"].iloc[-1], 2)
        ma120 = round(df["MA120"].iloc[-1], 2)

        array = sorted([
            ("MA5", df["MA5"].iloc[-1]),
            ("MA20", df["MA20"].iloc[-1]),
            ("MA60", df["MA60"].iloc[-1]),
            ("MA120", df["MA120"].iloc[-1])
        ], key=lambda x: -x[1])
        ma_order = " > ".join([x[0] for x in array])

        return {
            "종목명": _code2name(code),
            "종목코드": code,
            "현재가": cur,
            "익절기준(+3%)": round(cur * 1.03, 2),
            "손절기준(−3%)": round(cur * 0.97, 2),
            "5거래일 내 익절확률(%)": prob_take,
            "5거래일 내 손절확률(%)": prob_stop,
            "기술지표": {
                "RSI": rsi,
                "CCI": cci,
                "OBV 변화": obv_trend,
                "골든크로스": golden,
                "데드크로스": dead,
                "60일선": ma60,
                "120일선": ma120,
                "현재가 vs 60일선": "상단" if cur > ma60 else "하단",
                "현재가 vs 120일선": "상단" if cur > ma120 else "하단",
                "이평선 배열": ma_order
            }
        }
    except:
        return None

@app.route("/analyze")
def api_analyze():
    symbol = request.args.get("symbol")
    if not symbol:
        return jsonify({"error": "symbol 파라미터가 필요합니다."}), 400

    code = symbol if symbol.isdigit() else _name2code(symbol)
    if not code:
        return jsonify({"error": "유효한 종목명 또는 코드가 아닙니다."}), 404

    result = analyze_stock_prob(code)
    return jsonify(result or {"message": "분석에 실패했습니다."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
