from datetime import datetime
import pandas as pd
import FinanceDataReader as fdr
import ta
from flask import Flask, request, jsonify

app = Flask(__name__)
krx = fdr.StockListing("KRX")  # ── 종목 매핑

def _name2code(name):
    return krx.loc[krx["Name"] == name, "Code"].squeeze()

def _code2name(code):
    return krx.loc[krx["Code"] == code, "Name"].squeeze()

def _parse_params(q):
    return dict(
        hi=float(q.get("hi", 41)),
        lo=float(q.get("lo", 5)),
        cci_period=int(q.get("cci_period", 9)),
        cci_th=float(q.get("cci_th", -100)),
        rsi_period=int(q.get("rsi_period", 14)),
        rsi_th=float(q.get("rsi_th", 30)),
        di_period=int(q.get("di_period", 17)),
        env_len=int(q.get("env_len", 20)),
        env_pct=float(q.get("env_pct", 12))
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

    return result

def analyze_ichimoku(df):
    result = {}
    high_9 = df['High'].rolling(window=9).max()
    low_9 = df['Low'].rolling(window=9).min()
    df['전환선'] = (high_9 + low_9) / 2

    high_26 = df['High'].rolling(window=26).max()
    low_26 = df['Low'].rolling(window=26).min()
    df['기준선'] = (high_26 + low_26) / 2

    df['선행스팬1'] = ((df['전환선'] + df['기준선']) / 2).shift(26)

    high_52 = df['High'].rolling(window=52).max()
    low_52 = df['Low'].rolling(window=52).min()
    df['선행스팬2'] = ((high_52 + low_52) / 2).shift(26)

    df['후행스팬'] = df['Close'].shift(-26)

    # 일목균형표 해석
    try:
        current_close = df['Close'].iloc[-1]
        current_전환선 = df['전환선'].iloc[-1]
        current_기준선 = df['기준선'].iloc[-1]
        current_선행스팬1 = df['선행스팬1'].iloc[-1]
        current_선행스팬2 = df['선행스팬2'].iloc[-1]
        current_후행스팬 = df['후행스팬'].iloc[-1]

        # 전환선과 기준선의 위치
        if current_전환선 > current_기준선:
            result['전환선_기준선'] = "상승 신호"
        elif current_전환선 < current_기준선:
            result['전환선_기준선'] = "하락 신호"
        else:
            result['전환선_기준선'] = "중립"

        # 현재가와 구름대(선행스팬1, 선행스팬2)의 위치
        if current_close > max(current_선행스팬1, current_선행스팬2):
            result['구름대_위치'] = "상승 추세"
        elif current_close < min(current_선행스팬1, current_선행스팬2):
            result['구름대_위치'] = "하락 추세"
        else:
            result['구름대_위치'] = "중립 추세"

        # 후행스팬과 현재가의 위치
        if current_후행스팬 > current_close:
            result['후행스팬_위치'] = "상승 모멘텀"
        elif current_후행스팬 < current_close:
            result['후행스팬_위치'] = "하락 모멘텀"
        else:
            result['후행스팬_위치'] = "중립 모멘텀"

    except Exception as e:
        result['일목균형표_오류'] = str(e)

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

