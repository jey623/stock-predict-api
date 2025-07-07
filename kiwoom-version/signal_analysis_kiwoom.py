from flask import Flask, jsonify
import FinanceDataReader as fdr
import pandas as pd
import ta
import datetime
import time

app = Flask(__name__)

# 분석 대상 기간: 최근 1년
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=365)

# 추천 종목 분석 함수
def get_recommendations():
    krx_listed = fdr.StockListing('KRX')
    recommendations = []

    def analyze_stock(code, name):
        try:
            df = fdr.DataReader(code, start=start_date, end=end_date)
            if df.shape[0] < 100:
                return None

            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['Disparity'] = df['Close'] / df['MA5'] * 100
            df['OBV'] = ta.volume.OnBalanceVolumeIndicator(close=df['Close'], volume=df['Volume']).on_balance_volume()
            df['OBV_diff'] = df['OBV'].diff()
            recent = df.iloc[-5:]

            cond_disparity = recent['Disparity'].iloc[-1] < 92
            cond_golden = recent['MA5'].iloc[-1] > recent['MA20'].iloc[-1] and recent['MA5'].iloc[-2] <= recent['MA20'].iloc[-2]
            cond_obv = (recent['OBV_diff'] > 0).sum() >= 3
            cond_volume = recent['Volume'].iloc[-1] > df['Volume'].rolling(window=20).mean().iloc[-1]

            if cond_disparity and cond_golden and cond_obv and cond_volume:
                success_count = 0
                check_count = 0

                for i in range(len(df) - 15):
                    past = df.iloc[i:i+5]
                    cond1 = past['Close'].iloc[-1] / past['Close'].rolling(window=5).mean().iloc[-1] * 100 < 92
                    cond2 = past['MA5'].iloc[-1] > past['MA20'].iloc[-1] and past['MA5'].iloc[-2] <= past['MA20'].iloc[-2]
                    cond3 = (past['OBV'].diff() > 0).sum() >= 3
                    cond4 = past['Volume'].iloc[-1] > df['Volume'].rolling(window=20).mean().iloc[i+4]

                    if cond1 and cond2 and cond3 and cond4:
                        entry_price = df['Close'].iloc[i+4]
                        max_high = df['High'].iloc[i+5:i+15].max()
                        if max_high >= entry_price * 1.03:
                            success_count += 1
                        check_count += 1

                probability = round((success_count / check_count * 100), 1) if check_count > 0 else None

                if probability is not None and probability >= 80:
                    return {
                        '종목명': name,
                        '종목코드': code,
                        '현재가': round(df['Close'].iloc[-1], 2),
                        '익절3%도달확률': f"{probability}%"
                    }
        except:
            return None

    # 50개씩 분할 분석
    batch_size = 50
    for i in range(0, len(krx_listed), batch_size):
        batch = krx_listed.iloc[i:i+batch_size]
        for _, row in batch.iterrows():
            result = analyze_stock(row['Code'], row['Name'])
            if result:
                recommendations.append(result)
            if len(recommendations) >= 3:
                break
        time.sleep(0.2)
        if len(recommendations) >= 3:
            break

    return recommendations

# 상태 확인용 기본 경로
@app.route('/')
def home():
    return '✅ 바닥권 전략 추천 API가 정상 작동 중입니다.'

# 추천 종목 API
@app.route('/recommend')
def recommend():
    results = get_recommendations()
    if not results:
        return jsonify({'message': '오늘은 조건에 맞는 종목이 없습니다.'})
    else:
        return jsonify(results)

# 아래 코드는 gunicorn 실행 시 필요 없음
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=10000)

