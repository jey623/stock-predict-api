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

def analyze_e_book_signals(df):
    result = {}

    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()

    result['지지선'] = round(df['Close'].rolling(window=20).min().iloc[-1], 2)
    result['저항선'] = round(df['Close'].rolling(window=20).max().iloc[-1], 2)

    golden = (df['MA20'] > df['MA60']) & (df['MA20'].shift() <= df['MA60'].shift())
    dead = (df['MA20'] < df['MA60']) & (df['MA20'].shift() >= df['MA60'].shift())
    result['골든크로스'] = bool(golden.iloc[-1])
    result['데드크로스'] = bool(dead.iloc[-1])

    disparity_20 = (df['Close'] / df['MA20']) * 100
    disparity_60 = (df['Close'] / df['MA60']) * 100
    d20 = disparity_20.iloc[-1]
    d60 = disparity_60.iloc[-1]

    def classify_disparity(val):
        if val < 92:
            return f"과매도({val:.1f}%)"
        elif val > 102:
            return f"과매수({val:.1f}%)"
        else:
            return f"중립({val:.1f}%)"

    result['이격도_20일'] = classify_disparity(d20)
    result['이격도_60일'] = classify_disparity(d60)

    obv_indicator = ta.volume.OnBalanceVolumeIndicator(close=df['Close'], volume=df['Volume'])
    obv = obv_indicator.on_balance_volume()
    obv_trend = obv.rolling(window=5).mean().iloc[-1] - obv.rolling(window=5).mean().iloc[-2]
    price_trend = df['Close'].iloc[-1] - df['Close'].iloc[-2]

    if obv_trend > 0 and price_trend < 0:
        result['OBV_분석'] = "OBV 유지, 주가 하락 → 매집 가능성"
    elif obv_trend < 0 and price_trend > 0:
        result['OBV_분석'] = "OBV 하락, 주가 상승 → 분산 가능성"
    else:
        result['OBV_분석'] = "OBV와 주가 방향 일치"

    # ✅ 일목균형표
    nine_high = df['High'].rolling(window=9).max()
    nine_low = df['Low'].rolling(window=9).min()
    df['전환선'] = (nine_high + nine_low) / 2

    twenty_six_high = df['High'].rolling(window=26).max()
    twenty_six_low = df['Low'].rolling(window=26).min()
    df['기준선'] = (twenty_six_high + twenty_six_low) / 2

    df['선행스팬1'] = ((df['전환선'] + df['기준선']) / 2).shift(26)
    fifty_two_high = df['High'].rolling(window=52).max()
    fifty_two_low = df['Low'].rolling(window=52).min()
    df['선행스팬2'] = ((fifty_two_high + fifty_two_low) / 2).shift(26)

    df['구름하단'] = df[['선행스팬1', '선행스팬2']].min(axis=1)
    df['전기차이'] = abs(df['전환선'] - df['기준선'])

    result['일목_최저점'] = bool((df['Close'].iloc[-1] < df['구름하단'].iloc[-1]) and (df['전기차이'].iloc[-1] < 0.1))
    result['일목_골든크로스'] = bool((df['전환선'].iloc[-1] > df['기준선'].iloc[-1]) and (df['전환선'].iloc[-2] <= df['기준선'].iloc[-2]))

    if result['일목_최저점']:
        result['일목_해석'] = "전환선과 기준선이 평행하고 구름대 아래 위치 → 바닥 시그널 가능"
    elif result['일목_골든크로스']:
        result['일목_해석'] = "전환선이 기준선을 상향 돌파 → 상승 추세 전환 가능"
    else:
        result['일목_해석'] = "일목균형표 기준 특이점 없음"

    return result

def analyze_stock(symbol, **p):
    code = symbol if symbol.isdigit() else _name2code(symbol)
    name = _code2name(code) if symbol.isdigit() else symbol
    if not code or pd.isna(code):
        return {"error": "❌ 유효하지 않은 종목."}

    df = fdr.DataReader(code, start="2014-01-01")
    df = df.dropna().copy()

    df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"], window=p["cci_period"]).cci()
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=p["rsi_period"]).rsi()
    adx = ta.trend.ADXIndicator(df["High"], df["Low"], df["Close"], window=p["di_period"])
    df["DI+"], df["DI-"], df["ADX"] = adx.adx_pos(), adx.adx_neg(), adx.adx()

    ma = df["Close"].rolling(p["env_len"]).mean()
    envd = ma * (1 - p["env_pct"] / 100)
    df["LowestEnv"] = envd.rolling(5).min()
    df["LowestC"] = df["Close"].rolling(5).min()
    df = df.dropna().copy()

    df["Signal"] = (
        (df["CCI"] < p["cci_th"]) &
        (df["RSI"] < p["rsi_th"]) &
        (df["DI-"] > p["hi"]) &
        ((df["DI-"] < df["ADX"]) | (df["DI+"] < p["lo"])) &
        (df["LowestEnv"] > df["LowestC"])
    )

    cur = float(df["Close"].iat[-1])
    periods = [1, 5, 10, 20, 40, 60, 80]
    future_prices, change = {}, {}

    for d in periods:
        future_price = df["Close"].shift(-d)
        valid = ~future_price.isna()
        returns = ((future_price[valid] - df["Close"][valid]) / df["Close"][valid] * 100)
        if not returns.empty:
            avg_ret = round(returns.mean(), 2)
            pred_price = round(cur * (1 + avg_ret / 100), 2)
            change[f"{d}일"] = avg_ret
            future_prices[f"{d}일"] = pred_price

    e_book_signals = analyze_e_book_signals(df)

    return {
        "종목명": name,
        "종목코드": code,
        "현재가": cur,
        "예측가": future_prices,
        "변화율": change,
        "기술적_분석": e_book_signals
    }

@app.route("/")
def home():
    return "✅ Signal Analysis API is running."

@app.route("/analyze")
def api_analyze():
    q = request.args
    symbol = q.get("symbol", "")
    if not symbol:
        return jsonify({"error": "❗ symbol 파라미터가 필요합니다."}), 400
    data = analyze_stock(symbol, **_parse_params(q))
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

