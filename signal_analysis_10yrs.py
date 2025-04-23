import pandas as pd
import numpy as np
import FinanceDataReader as fdr
import ta

# ✅ 10년치 주가 데이터
df = fdr.DataReader('005930', start='2014-01-01')

# ✅ 이동평균선
df['MA5'] = df['Close'].rolling(window=5).mean()
df['MA10'] = df['Close'].rolling(window=10).mean()
df['MA20'] = df['Close'].rolling(window=20).mean()
df['MA40'] = df['Close'].rolling(window=40).mean()
df['MA60'] = df['Close'].rolling(window=60).mean()

# ✅ 볼린저밴드
bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
df['BB_MID'] = bb.bollinger_mavg()
df['BB_UPPER'] = bb.bollinger_hband()
df['BB_LOWER'] = bb.bollinger_lband()

# ✅ 엔벨로프 (기본 ±1%)
df['Envelope_Upper'] = df['Close'] * 1.01
df['Envelope_Lower'] = df['Close'] * 0.99

# ✅ TSF: EMA로 근사 (window=5)
df['TSF'] = ta.trend.EMAIndicator(close=df['Close'], window=5).ema_indicator()

# ✅ DMI/ADX
adx = ta.trend.ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=17)
df['+DI'] = adx.adx_pos()
df['-DI'] = adx.adx_neg()
df['ADX'] = adx.adx()

# ✅ CCI & RSI
df['CCI'] = ta.trend.CCIIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=9).cci()
df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()

# ✅ EnvelopeDown 20,12 계산 및 신호검색 조건 정의
envelope_down = df['MA20'] * (1 - 0.012)
df['Signal_Triggered'] = (
    (df['CCI'] < -100) &
    (df['RSI'] < 30) &
    (df['-DI'] > 41) &
    ((df['-DI'] < df['ADX']) | (df['+DI'] < 5)) &
    (envelope_down.rolling(window=5).min() > df['Close'].rolling(window=5).min())
)

# ✅ 결과 출력
latest = df.iloc[-1]
result = {
    "종목명": "삼성전자",
    "종목코드": "005930",
    "현재가": float(latest['Close']),
    "신호발생": bool(latest['Signal_Triggered'])
}
import json
print(json.dumps(result, ensure_ascii=False, indent=2))

