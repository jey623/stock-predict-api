from datetime import datetime
import pandas as pd, FinanceDataReader as fdr, ta
from flask import Flask, request, jsonify

app = Flask(__name__)
krx = fdr.StockListing("KRX")                      # ── 종목 매핑

# ────────────────────────── 유틸 ──────────────────────────
def _name2code(name): return krx.loc[krx["Name"] == name, "Code"].squeeze()
def _code2name(code): return krx.loc[krx["Code"] == code, "Name"].squeeze()

# ────────────────────────── 핵심 분석 함수 ──────────────────────────
def analyze_stock(
    symbol,
    hi=41, lo=5,                          # HighTop / LowBottom
    cci_period=9,   cci_th=-100,          # CCI
    rsi_period=14,  rsi_th=30,            # RSI
    di_period=17,                         # ADX·DI± 기간
    env_len=20, env_pct=12                # Envelope(20, -12 %) 고정
):
    # ① 종목 식별
    code = symbol if symbol.isdigit() else _name2code(symbol)
    name = _code2name(code) if symbol.isdigit() else symbol
    if not code or pd.isna(code):
        return {"error": "❌ 유효하지 않은 종목."}

    # ② 데이터 로드 (dropna X)
    df = fdr.DataReader(code, start="2014-01-01")

    # ③ 지표 계산
    df["CCI"] = ta.trend.CCIIndicator(
        df["High"], df["Low"], df["Close"], window=cci_period
    ).cci()
    df["RSI"] = ta.momentum.RSIIndicator(
        df["Close"], window=rsi_period
    ).rsi()
    adx = ta.trend.ADXIndicator(
        df["High"], df["Low"], df["Close"], window=di_period
    )
    df["DI+"], df["DI-"], df["ADX"] = adx.adx_pos(), adx.adx_neg(), adx.adx()

    # ④ Envelope & Lowest(5)
    ma = df["Close"].rolling(env_len).mean()
    env_dn = ma * (1 - env_pct / 100)
    df["LowestEnv"] = env_dn.rolling(5).min()
    df["LowestC"]   = df["Close"].rolling(5).min()

    # ⑤ NaN 제거(모든 지표 계산 완료 후)
    df = df.dropna().copy()

    # ⑥ 신호 조건 (수식 그대로)
    df["Signal"] = (
        (df["CCI"] < cci_th) &
        (df["RSI"] < rsi_th) &
        (df["DI-"] > hi) &
        ((df["DI-"] < df["ADX"]) | (df["DI+"] < lo)) &
        (df["LowestEnv"] > df["LowestC"])
    )

    # ⑦ 결과 정리
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
        "신호발생": bool(df["Signal"].iloc[-1]),  # 현재 시점만
        "신호발생일자": sig_dates
    }

# ────────────────────────── Flask 엔드포인트 ──────────────────────────
@app.route("/")
def home():
    return "📈 Signal Analysis API is running."

@app.route("/analyze")
def api_analyze():
    q = request.args
    symbol = q.get("symbol", "")
    if not symbol:
        return jsonify({"error": "Need symbol"}), 400

    # ── 파라미터 파싱 (없는 경우 기본값 유지)
    params = dict(
        hi          = float(q.get("hi", 41)),
        lo          = float(q.get("lo", 5)),
        cci_period  = int  (q.get("cci_period", 9)),
        cci_th      = float(q.get("cci_th", -100)),
        rsi_period  = int  (q.get("rsi_period", 14)),
        rsi_th      = float(q.get("rsi_th", 30)),
        di_period   = int  (q.get("di_period", 17)),
        env_len     = int  (q.get("env_len", 20)),
        env_pct     = float(q.get("env_pct", 12))
    )

    data = analyze_stock(symbol, **params)
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


