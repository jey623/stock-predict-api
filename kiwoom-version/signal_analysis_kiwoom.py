from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import ta

app = Flask(__name__)
krx = fdr.StockListing("KRX")

def _code2name(code):
    return krx.loc[krx["Code"] == code, "Name"].squeeze()

def _name2code(name):
    return krx.loc[krx["Name"] == name, "Code"].squeeze()

def analyze_full_stock(code):
    try:
        df = fdr.DataReader(code, start="2014-01-01").dropna().copy()
        df.reset_index(inplace=True)

        # 확률 계산
        total, take, stop = 0, 0, 0
        for i in range(len(df) - 5):
            close = df.loc[i, "Close"]
            high5 = df.loc[i+1:i+5, "High"].max()
            low5 = df.loc[i+1:i+5, "Low"].min()
            if high5 >= close * 1.03:
                take += 1
            if low5 <= close * 0.97:
                stop += 1
            total += 1
        prob_take = round((take / total) * 100, 2)
        prob_stop = round((stop / total) * 100, 2)

        # 기술 지표
        df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
        df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"], window=20).cci()
        df["OBV"] = ta.volume.OnBalanceVolumeIndicator(df["Close"], df["Volume"]).on_balance_volume()
        df["MA5"] = df["Close"].rolling(window=5).mean()
        df["MA20"] = df["Close"].rolling(window=20).mean()
        df["MA60"] = df["Close"].rolling(window=60).mean()
        df["MA120"] = df["Close"].rolling(window=120).mean()

        cur = float(df["Close"].iloc[-1])
        ma_array = sorted([
            ("MA5", df["MA5"].iloc[-1]),
            ("MA20", df["MA20"].iloc[-1]),
            ("MA60", df["MA60"].iloc[-1]),
            ("MA120", df["MA120"].iloc[-1])
        ], key=lambda x: -x[1])
        ma_order = " > ".join([x[0] for x in ma_array])

        return {
            "종목명": _code2name(code),
            "종목코드": code,
            "현재가": cur,
            "익절기준(+3%)": round(cur * 1.03, 2),
            "손절기준(−3%)": round(cur * 0.97, 2),
            "5거래일 내 익절확률(%)": prob_take,
            "5거래일 내 손절확률(%)": prob_stop,
            "기술지표": {
                "RSI": {"값": round(df["RSI"].iloc[-1], 2), "해석": "과매수 경계" if df["RSI"].iloc[-1] > 70 else "정상"},
                "CCI": {"값": round(df["CCI"].iloc[-1], 2), "해석": "단기 급등 흐름" if df["CCI"].iloc[-1] > 100 else "중립"},
                "OBV 변화": int(df["OBV"].iloc[-1] - df["OBV"].iloc[-2]),
                "이동평균": f"{ma_order} (추세 확인용)",
                "현재가 vs 60일선": "상단" if cur > df["MA60"].iloc[-1] else "하단",
                "현재가 vs 120일선": "상단" if cur > df["MA120"].iloc[-1] else "하단"
            },
            "요약": "상승 흐름 지속 중. RSI 과열 주의." if df["RSI"].iloc[-1] > 70 else "단기 안정 흐름."
        }
    except:
        return None

@app.route("/full_analysis")
@app.route("/analyze")
def full_analysis():
    symbol = request.args.get("symbol")
    code = symbol if symbol.isdigit() else _name2code(symbol)
    if not code:
        return jsonify({"error": "유효한 종목명 또는 코드가 아닙니다."}), 404
    result = analyze_full_stock(code)
    return jsonify(result or {"message": "분석에 실패했습니다."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


