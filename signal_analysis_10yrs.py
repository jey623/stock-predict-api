import pandas as pd
import FinanceDataReader as fdr
import ta
import numpy as np
import json
import sys

# 종목코드 입력받기 (기본값: 삼성전자)
stock_code = sys.argv[1] if len(sys.argv) > 1 else "005930"

# 간단한 종목명 매핑 (필요시 확장 가능)
code_name_map = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "035420": "NAVER",
    "373220": "LG에너지솔루션",
    "207940": "삼성바이오로직스"
}
stock_name = code_name_map.get(stock_code, "알 수 없음")

try:
    # ✅ 10년치 데이터 불러오기
    df = fdr.DataReader(stock_code, start="2014-01-01")

    # ✅ 주요 기술적 지표 계산
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA10"] = df["Close"].rolling(10).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA40"] = df["Close"].rolling(40).mean()
    df["MA60"] = df["Close"].rolling(60).mean()

    bb = ta.volatility.BollingerBands(close=df["Close"], window=20, window_dev=2)
    df["BB_MID"] = bb.bollinger_mavg()
    df["BB_UPPER"] = bb.bollinger_hband()
    df["BB_LOWER"] = bb.bollinger_lband()

    df["Envelope_Upper"] = df["MA20"] * 1.03
    df["Envelope_Lower"] = df["MA20"] * 0.97

    df["TSF"] = df["Close"].ewm(span=5, adjust=False).mean()  # TSF 근사치

    adx = ta.trend.ADXIndicator(high=df["High"], low=df["Low"], close=df["Close"])
    df["DMI_PLUS"] = adx.adx_pos()
    df["DMI_MINUS"] = adx.adx_neg()
    df["ADX"] = adx.adx()

    df["RSI"] = ta.momentum.RSIIndicator(close=df["Close"], window=14).rsi()
    df["CCI"] = ta.trend.CCIIndicator(high=df["High"], low=df["Low"], close=df["Close"]).cci()

    # ✅ 신호검색 조건 적용 (스크린샷 기반 조건 예시)
    df["Signal_Triggered"] = (
        (df["MA5"] > df["MA20"]) &
        (df["MA5"].shift(1) <= df["MA20"].shift(1)) &
        (df["RSI"] < 30)
    )

    df.dropna(inplace=True)

    # ✅ 최신 데이터 기준 판단
    latest = df.iloc[-1]
    signal = bool(latest["Signal_Triggered"])

    result = {
        "종목명": stock_name,
        "종목코드": stock_code,
        "현재가": float(latest["Close"]),
        "신호발생": signal
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

except Exception as e:
    print("❌ 오류 발생:", str(e))

