from datetime import datetime
import pandas as pd, FinanceDataReader as fdr, ta
from flask import Flask, request, jsonify

app = Flask(__name__)
krx = fdr.StockListing("KRX")

def _name2code(name): return krx.loc[krx["Name"] == name, "Code"].squeeze()
def _code2name(code): return krx.loc[krx["Code"] == code, "Name"].squeeze()

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

def analyze_stock(symbol, **p):
    code = symbol if symbol.isdigit() else _name2code(symbol)
    name = _code2name(code) if symbol.isdigit() else symbol
    if not code or pd.isna(code):
        return {"error": "❌ 유효하지 않은 종목."}

    df = fdr.DataReader(code, start="2014-01-01")

    df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"], window=p["cci_period"]).cci()
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=p["rsi_period"]).rsi()
    adx = ta.trend.ADXIndicator(df["High"], df["Low"], df["Close"], window=p["di_period"])
    df["DI+"], df["DI-"], df["ADX"] = adx.adx_pos(), adx.adx_neg(), adx.adx()

    ma = df["Close"].rolling(p["env_len"]).mean()
    envd = ma * (1 - p["env_pct"] / 100)
    df["LowestEnv"] = envd.rolling(5).min()
    df["LowestC"]   = df["Close"].rolling(5).min()

    df = df.dropna().copy()

    df["Signal"] = (
        (df["CCI"] < p["cci_th"]) &
        (df["RSI"] < p["rsi_th"]) &
        (df["DI-"] > p["hi"]) &
        ((df["DI-"] < df["ADX"]) | (df["DI+"] < p["lo"])) &
        (df["LowestEnv"] > df["LowestC"])
    )

    cur = float(df["Close"].iat[-1])

    # 실제 과거 신호 기준 수익률 평균 계산
    periods = [1, 5, 10, 20, 40, 60, 80]
    future_returns = {p: [] for p in periods}

    signal_indices = df.index[df["Signal"]]
    for idx in signal_indices:
        for p in periods:
            if idx + pd.Timedelta(days=p) in df.index:
                future_price = df.loc[idx + pd.Timedelta(days=p), "Close"]
                now_price = df.loc[idx, "Close"]
                ret = (future_price - now_price) / now_price * 100
                future_returns[p].append(ret)

    avg_returns = {f"{p}일": round(sum(future_returns[p])/len(future_returns[p]), 2) if future_returns[p] else 0 for p in periods}
    pred = {f"{p}일": round(cur * (1 + avg_returns[f"{p}일"] / 100), 2) for p in periods}

    sig_dates = signal_indices.strftime("%Y-%m-%d").tolist()

    return {
        "종목명": name,
        "종목코드": code,
        "현재가": cur,
        "예측가": pred,
        "변화율": avg_returns,
        "신호발생": bool(df["Signal"].iloc[-1]),
        "신호발생일자": sig_dates
    }

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


