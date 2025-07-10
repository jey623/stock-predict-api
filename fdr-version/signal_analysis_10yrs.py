import FinanceDataReader as fdr
import pandas as pd
import datetime
from flask import Flask, jsonify

app = Flask(__name__)

MIN_VOLUME = 1_000_000_000
LOOKBACK_DAYS = 250
MIN_HIGHS_DAYS = 120
MAX_MARKETCAP = 2_000_000_000_000  # 2조

def check_candidate(df):
    if df.shape[0] < LOOKBACK_DAYS:
        return False
    last = df.iloc[-1]
    if last['Volume'] * last['Close'] < MIN_VOLUME:
        return False
    box_low = df['Low'][-LOOKBACK_DAYS:].min()
    prev_high = df['High'][-MIN_HIGHS_DAYS:].max()
    if (last['Close'] > box_low * 1.15) and (last['High'] >= prev_high):
        return True
    return False

@app.route('/recommend')
def recommend():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=LOOKBACK_DAYS + 5)

    # KRX 전체 종목 및 시가총액 정보 불러오기
    krx = fdr.StockListing('KRX')
    # 2조 이하 필터 적용
    krx = krx[krx['Marcap'] <= MAX_MARKETCAP].reset_index(drop=True)

    results = []
    # 거래대금 집계용 리스트
    trading_list = []
    for idx, row in krx.iterrows():
        code = row['Code']
        name = row['Name']
        try:
            df = fdr.DataReader(code, start=start_date, end=end_date)
            if df.shape[0] < LOOKBACK_DAYS:
                continue
            last = df.iloc[-1]
            trading_list.append({'code': code, 'name': name, 'df': df, 'trading_value': last['Close'] * last['Volume']})
        except:
            continue

    # 거래대금 상위 50위만 남김
    trading_list = sorted(trading_list, key=lambda x: x['trading_value'], reverse=True)[:50]

    # 각 후보 조건 체크
    for stock in trading_list:
        if check_candidate(stock['df']):
            last = stock['df'].iloc[-1]
            results.append({
                '종목명': stock['name'],
                '종목코드': stock['code'],
                '현재가': int(last['Close']),
                '추천사유': "박스권 저점 돌파, 전고점 경신, 거래대금 상위 50위, 시가총액 2조 이하"
            })

    if not results:
        return jsonify({"message": "오늘 조건에 맞는 추천 종목이 없습니다."}), 200
    return jsonify(results), 200

if __name__ == "__main__":
    app.run()


