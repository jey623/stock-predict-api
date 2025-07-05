# 최종버전: 사용자가 종목 입력 → 5거래일 내 익절(+3%), 손절(−3%) 확률 분석 API

from datetime import datetime
import pandas as pd, FinanceDataReader as fdr
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
        count_take = 0  # 익절
        count_stop = 0  # 손절

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

        cur = float(df["Close"].iloc[-1])

        return {
            "종목명": _code2name(code),
            "종목코드": code,
            "현재가": cur,
            "익절기준(+3%)": round(cur * 1.03, 2),
            "손절기준(−3%)": round(cur * 0.97, 2),
            "5거래일 내 익절확률(%)": prob_take,
            "5거래일 내 손절확률(%)": prob_stop
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
