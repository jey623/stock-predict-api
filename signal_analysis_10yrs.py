from datetime import datetime
import pandas as pd, FinanceDataReader as fdr, ta
from flask import Flask, request, jsonify

app = Flask(__name__)
krx = fdr.StockListing("KRX")                      # ── 종목 매핑

# ────────────────────────── 유틸 ──────────────────────────
def _name2code(name): return krx.loc[krx["Name"] == name, "Code"].squeeze()
def _code2name(code): return krx.loc[krx["Code"] == code, "Name"].squeeze()

# ────────────────────────── 공통 파라미터 파싱 ──────────────────────────
def _parse_params(q):
    return dict(
        hi         = float(q.get("hi", 41)),   # DI- 임계값
        lo         = float(q.get("lo", 5)),    # DI+ 임계값
        cci_period = int  (q.get("cci_period", 9)),
        cci_th     = float(q.get("cci_th", -100)),
        rsi_period = int  (q.get("rsi_period", 14)),
        rsi_th     = float(q.get("rsi_th", 30)),
        di_period  = int  (q.get("di_period", 17)),
        env_len    = int  (q.get("env_len", 20)),
        env_pct    = float(q.get("env_pct", 12))
    )

# ────────────────────────── 핵심 분석 함수 ──────────────────────────
def analyze_stock(symbol, **p):
    code = symbol if symbol.isdigit() else _name2code(symbol)
    name = _code2name(code) if symbol.isdigit() else symbol
    if not code or pd.isna(code):
        return {"error": "❌ 유효하지 않은 종목."}

    # ── 데이터
    df = fdr.DataReader(code, start="2014-01-01")

    # ── 지표
    df["CCI"] = ta.trend.CCIIndicator(
        df["High"], df["Low"], df["Close"], window=p["cci_period"]).cci()
    df["RSI"] = ta.momentum.RSIIndicator(
        df["Close"], window=p["rsi_period"]).rsi()
    adx = ta.trend.ADXIndicator(
        df["High"], df["Low"], df["Close"], window=p["di_period"])
    df["DI+"], df["DI-"], df["ADX"] = adx.adx_pos(), adx.adx_neg(), adx.adx()

    ma   = df["Close"].rolling(p["env_len"]).mean()
    envd = ma * (1 - p["env_pct"] / 100)
    df["LowestEnv"] = envd.rolling(5).min()
    df["LowestC"]   = df["Close"].rolling(5).min()

    df = df.dropna().copy()

    # ── 신호
    df["Signal"] = (
        (df["CCI"] < p["cci_th"]) &
        (df["RSI"] < p["rsi_th"]) &
        (df["DI-"] > p["hi"]) &
        ((df["DI-"] < df["ADX"]) | (df["DI+"] < p["lo"])) &
        (df["LowestEnv"] > df["LowestC"])
    )

    cur = float(df["Close"].iat[-1])
    periods = [1, 5, 10, 20, 40, 60, 80]
    pred = {f"{x}일": round(cur * (1 + 0.002 * x), 2) for x in periods}
    change = {k: round((v - cur) / cur * 100, 2) for k, v in pred.items()}
    sig_dates = df.index[df["Signal"]].strftime("%Y-%m-%d").tolist()

    return {
        "종목명": name,
        "종목코드": code,
        "현재가": cur,
        "예측가": pred,
        "변화율": change,
        "신호발생": bool(df["Signal"].iloc[-1]),   # 현재 일자 신호 여부
        "신호발생일자": sig_dates                  # 과거 10년 신호 리스트
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
    data = analyze_stock(symbol, **_parse_params(q))
    return jsonify(data)

# === DEBUG : 단계별 필터링 건수 확인 =================================
@app.route("/analyze_debug")
def api_analyze_debug():
    q = request.args
    symbol = q.get("symbol", "")
    if not symbol:
        return jsonify({"error": "Need symbol"}), 400
    p = _parse_params(q)
    code = symbol if symbol.isdigit() else _name2code(symbol)
    df = fdr.DataReader(code, start="2014-01-01")

    # 동일 지표 계산
    df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"],
                                      df["Close"], p["cci_period"]).cci()
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"],
                                         window=p["rsi_period"]).rsi()
    adx = ta.trend.ADXIndicator(df["High"], df["Low"],
                                df["Close"], p["di_period"])
    df["DI+"], df["DI-"], df["ADX"] = adx.adx_pos(), adx.adx_neg(), adx.adx()
    ma = df["Close"].rolling(p["env_len"]).mean()
    envd = ma * (1 - p["env_pct"] / 100)
    df["LowestEnv"] = envd.rolling(5).min()
    df["LowestC"]   = df["Close"].rolling(5).min()
    df = df.dropna()

    c1 = df["CCI"] < p["cci_th"]
    c2 = df["RSI"] < p["rsi_th"]
    c3 = df["DI-"] > p["hi"]
    c4 = (df["DI-"] < df["ADX"]) | (df["DI+"] < p["lo"])
    c5 = df["LowestEnv"] > df["LowestC"]

    counts = {
        "전체":           len(df),
        "① CCI":         int(c1.sum()),
        "② +RSI":        int((c1 & c2).sum()),
        "③ +DI-":        int((c1 & c2 & c3).sum()),
        "④ +ADX/DI+":    int((c1 & c2 & c3 & c4).sum()),
        "⑤ +Envelope":   int((c1 & c2 & c3 & c4 & c5).sum())
    }
    return jsonify(counts)
# ====================================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


