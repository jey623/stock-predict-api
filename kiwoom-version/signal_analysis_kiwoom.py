# recommend_generator.py
# 전자책 기반 바닥권 전략 + 2년치 데이터 분석 + 전체 종목 분할 분석 + 종목명/코드 직접 출력

import FinanceDataReader as fdr
import pandas as pd
import ta
import datetime
import time

# 1. 날짜 설정 (최근 2년)
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=365 * 2)

# 2. 전체 KRX (코스피+코스닥) 종목 리스트 불러오기
krx_listed = fdr.StockListing('KRX')
codes = krx_listed['Code'].tolist()

recommendations = []

# 3. 바닥권 전략 조건 분석 함수
def analyze_stock(code, name):
    try:
        df = fdr.DataReader(code, start=start_date, end=end_date)
        if df.shape[0] < 100:
            return None

        # 기술적 지표 계산
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['Disparity'] = df['Close'] / df['MA5'] * 100
        df['OBV'] = ta.volume.OnBalanceVolumeIndicator(close=df['Close'], volume=df['Volume']).on_balance_volume()
        df['OBV_diff'] = df['OBV'].diff()

        recent = df.iloc[-5:]

        # 전자책 바닥권 전략 조건
        cond_disparity = recent['Disparity'].iloc[-1] < 92
        cond_golden = (
            recent['MA5'].iloc[-1] > recent['MA20'].iloc[-1]
            and recent['MA5'].iloc[-2] <= recent['MA20'].iloc[-2]
        )
        cond_obv = (recent['OBV_diff'] > 0).sum() >= 3
        cond_volume = recent['Volume'].iloc[-1] > df['Volume'].rolling(window=20).mean().iloc[-1]

        if cond_disparity and cond_golden and cond_obv and cond_volume:
            return {
                '종목명': name,
                '종목코드': code,
                '현재가': round(df['Close'].iloc[-1], 2)
            }
    except:
        return None

# 4. 전체 종목 분할 분석 (100개씩 나누기)
batch_size = 100
for i in range(0, len(krx_listed), batch_size):
    batch = krx_listed.iloc[i:i+batch_size]
    for idx, row in batch.iterrows():
        result = analyze_stock(row['Code'], row['Name'])
        if result:
            recommendations.append(result)
    time.sleep(1)

# 5. 자연어 형태로 결과 출력
print("\n📈 바닥권 전략 추천 종목 ({} 기준):".format(end_date.date()))

if recommendations:
    for i, stock in enumerate(recommendations, 1):
        print(f"{i}. {stock['종목명']} ({stock['종목코드']}) - 현재가: {stock['현재가']}원")
else:
    print("오늘은 조건에 맞는 종목이 없습니다.")


