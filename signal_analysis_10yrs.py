from datetime import datetime
import pandas as pd, numpy as np, FinanceDataReader as fdr, ta
from flask import Flask, request, jsonify

app = Flask(__name__)
krx = fdr.StockListing("KRX")  # 상장종목 매핑용 -------------------------------------------------

def _name2code(name):
    return krx.loc[krx["Name"] == name, "Code"].squeeze()

def _code2name(code):
    return krx.loc[krx["Code"] == code, "Name"].squeeze()

# ────────────────────────── 핵심 함수 ──────────────────────────
def analyze_stock(symbol, hi=41, lo=5, env_pct=12, rsi_th=30, cci_th=-100):
    # ① 종목 식별
    code = symbol if symbol.isdigit() else _name2code(symbol)
    name = _code2name(code) if symbol.isdigit() else symbol
    if not code or pd.isna(code):  # 예외처리
        return {"error": "❌ 유효하지 않은 종목."}

    # ② 데이터 로드
    df = fdr.DataReader(code, start="2014-01-01").dropna()

    # ③ 기술적 지표 계산
    df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"], 9).cci()
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], 14).rsi()
    adx = ta.trend.ADXIndicator(df["High"], df["Low"], df["Close"], 17)
    df["DI+"], df["DI-"], df["ADX"] = adx.adx_pos(), adx.adx_neg(), adx.adx()

    ma20 = df["Close"].rolling(20).mean()
    env_dn = ma20 * (1 - env_pct / 100)
    df["LowestEnv"] = env_dn.rolling(5).min()
    df["LowestC"] = df["Close"].rolling(5).min()

    # ④ 신호 조건
    df["Signal"] = (
        (df["CCI"] < cci_th) &
        (df["RSI"] < rsi_th) &
        (df["DI-"] > hi) &
        ((df["DI-"] < df["ADX"]) | (df["DI+"] < lo)) &
        (df["LowestEnv"] > df["LowestC"])
    )

    # ⑤ 결과 정리
    cur = float(df["Close"].iat[-1])
    periods = [1, 5, 10, 20, 40, 60, 80]
    pred = {f"{p}일": round(cur * (1 + 0.002 * p), 2) for p in periods}  # 더미 예측
    change = {k: round((v - cur) / cur * 100, 2) for k, v in pred.items()}
    sig_dates = df.index[df["Signal"]].strftime("%Y-%m-%d").tolist()

    return {
        "종목명": name,
        "종목코드": code,
        "현재가": cur,
        "예측가": pred,
        "변화율": change,
        "신호발생": bool(df["Signal"].iloc[-1]),   # <-- 현재 시점만 체크 (마지막 Row)
        "신호발생일자": sig_dates                  # <-- 과거 전체 중 신호 발생한 날짜
    }

# ────────────────────────── Flask 엔드포인트 ──────────────────────────
@app.route("/")
def home():
    return "📈 Signal Analysis API is running."

@app.route("/analyze")
def api_analyze():
    args = request.args
    symbol = args.get("symbol", "")
    if not symbol:
        return jsonify({"error": "Need symbol"}), 400

    hi = float(args.get("hi", 41))
    lo = float(args.get("lo", 5))
    env = float(args.get("env", 12))
    rsi = float(args.get("rsi", 30))
    cci = float(args.get("cci", -100))

    data = analyze_stock(symbol, hi, lo, env, rsi, cci)
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

