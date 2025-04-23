import pandas as pd
import FinanceDataReader as fdr
import ta
import numpy as np
import json
import sys

# ✅ 전체 상장 종목 불러오기 (자동 종목명 매핑용)
krx = fdr.StockListing('KRX')

# ✅ 종목명 → 종목코드
def get_code_by_name(name):
    row = krx[krx['Name'] == name]
    return row['Code'].values[0] if not row.empty else None

# ✅ 종목코드 → 종목명
def get_name_by_code(code):
    row = krx[krx['Code'] == code]
    return row['Name'].values[0] if not row.empty else None

# ✅ 입력 (종목명 또는 종목코드)
input_value = "삼성전자"  # ← 여기에 "005930"도 가능

# ✅ 종목명 또는 코드 자동 인식
if input_value.isdigit():
    code = input_value
    name = get_name_by_code(code)
else:
    name = input_value
    code = get_code_by_name(name)

if not code:
    print("❌ 유효하지 않은 종목명 또는 코드입니다.")
    sys.exit()

# ✅ 10년치 데이터 수집
df = fdr.DataReader(code, start='2014-01-01')

# ✅ 이동평균선 (5, 10, 20, 40, 60)
for window in [5, 10, 20, 40, 60]:
    df[f'MA{window}'] = df['Close'].rolling(window=window).mean()

# ✅ 주요 기술적 지표 추가
df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
macd = ta.trend.MACD(close=df['Close'])
df['MACD'] = macd.macd()
df['MACD_signal'] = macd.macd_signal()
df['BB_upper'] = ta.volatility.BollingerBands(close=df['Close']).bollinger_hband()
df['BB_lower'] = ta.volatility.BollingerBands(close=df['Close']).bollinger_lband()
df['Envelope_high'] = df['MA20'] * 1.03
df['Envelope_low'] = df['MA20'] * 0.97

# ✅ 신호검색 수식 조건 (예시)
df['Signal_Triggered'] = (
    (df['MA5'] > df['MA20']) &
    (df['MA5'].shift(1) <= df['MA20'].shift(1)) &
    (df['RSI'] < 30)
)

# ✅ 마지막 데이터 기준
latest = df.iloc[-1]
signal = bool(latest['Signal_Triggered'])

# ✅ 결과 출력
result = {
    "종목명": name,
    "종목코드": code,
    "현재가": float(latest['Close']),
    "신호발생": signal
}

print(json.dumps(result, ensure_ascii=False, indent=2))


