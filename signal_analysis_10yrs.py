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
        hi         = float(q.get("hi", 41)),
        lo         = float(q.get("lo", 5)),
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

    # ── 데이터 (10 년치 일봉)
    df = fdr.DataReader(code, start="2014-01-01")

    # ── 지표 계산
    df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"],
                                      window=p["cci_period"]).cci()
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"],
                                         window=p["rsi_period"]).rsi()
    adx = ta.trend.ADXIndicator(df["High"], df["Low"], df["Close"],
                                window=p["di_period"])
    df["DI+"], df["DI-"], df["ADX"] = adx.adx_pos(), adx.adx_neg(), adx.adx()

    ma   = df["Close"].rolling(p["env_len"]).mean()
    envd = ma * (1 - p["env_pct"] / 100)
    df["LowestEnv"] = envd.rolling(5).min()
    df["LowestC"]   = df["Close"].rolling(5).min()
    df = df.dropna().copy()

    # ── 신호 판정
    df["Signal"] = (
        (df["CCI"] < p["cci_th"]) &
        (df["RSI"] < p["rsi_th"]) &
        (df["DI-"] > p["hi"]) &
        ((df["DI-"] < df["ADX"]) | (df["DI+"] < p["lo"])) &
        (df["LowestEnv"] > df["LowestC"])
    )

    # ── 현재가
    cur = float(df["Close"].iat[-1])

    # ── 예측가 & 변화율 : 과거 모든 날짜의 실제 미래 수익률 평균
    periods = [1, 5, 10, 20, 40, 60, 80]
    future_prices, change = {}, {}

    for d in periods:
        # 각 날짜별 d일 후 가격이 존재할 때만 수익률 계산
        future_price = df["Close"].shift(-d)
        valid = ~future_price.isna()
        returns = ((future_price[valid] - df["Close"][valid]) / df["Close"][valid] * 100)
        if not returns.empty:
            avg_ret = round(returns.mean(), 2)                      # 평균 변화율 %
            pred_price = round(cur * (1 + avg_ret / 100), 2)        # 예상 가격
            change[f"{d}일"] = avg_ret
            future_prices[f"{d}일"] = pred_price

    return {
        "종목명": name,
        "종목코드": code,
        "현재가": cur,
        "예측가": future_prices,
        "변화율": change,
        "신호발생": bool(df["Signal"].iloc[-1])   # 오늘(가장 최근) 신호 여부
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

