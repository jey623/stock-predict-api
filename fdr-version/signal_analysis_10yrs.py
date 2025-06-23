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

    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()

    result['지지선'] = round(df['Close'].rolling(window=20).min().iloc[-1], 2)
    result['저항선'] = round(df['Close'].rolling(window=20).max().iloc[-1], 2)

    golden = (df['MA20'] > df['MA60']) & (df['MA20'].shift() <= df['MA60'].shift())
    dead = (df['MA20'] < df['MA60']) & (df['MA20'].shift() >= df['MA60'].shift())
    result['골든크로스'] = bool(golden.iloc[-1])
    result['데드크로스'] = bool(dead.iloc[-1])

    for ma, label in zip(['MA20', 'MA60', 'MA120'], ['이격도_20일', '이격도_60일', '이격도_120일']):
        disparity = (df['Close'] / df[ma]) * 100
        val = disparity.iloc[-1]
        if val < 92:
            result[label] = f"과매도({val:.1f}%)"
        elif val > 102:
            result[label] = f"과매수({val:.1f}%)"
        else:
            result[label] = f"중립({val:.1f}%)"

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

    result['박스권_형성'] = False
    result['박스권_돌파'] = False
    for box_period in range(10, 61, 10):
        box_high = df['High'].rolling(window=box_period).max().iloc[-2]
        box_low = df['Low'].rolling(window=box_period).min().iloc[-2]
        box_range = (box_high - box_low) / box_low
        close = df['Close'].iloc[-1]

        if box_range < 0.10:
            result['박스권_형성'] = True
            if close > box_high * 1.02:
                result['박스권_돌파'] = True
                result['박스권_해석'] = f"{box_period}일 박스권({box_low:.2f}~{box_high:.2f}) 돌파"
                break
            else:
                result['박스권_해석'] = f"{box_period}일 박스권 내 형성 중"
                break

    return result


