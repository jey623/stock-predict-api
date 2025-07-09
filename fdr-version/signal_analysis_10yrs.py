from flask import Flask, request, jsonify
import pandas as pd
from prophet import Prophet
import FinanceDataReader as fdr

app = Flask(__name__)

# Render Health Check 대응 (루트 URL은 반드시 200 OK)
@app.route('/')
def index():
    return 'OK'

# 예측 엔드포인트 (기본: 10일, period=10)
@app.route('/predict')
def predict():
    symbol = request.args.get('symbol')
    period = int(request.args.get('period', 10))

    # 10년치 데이터 로드 (종목코드/이름 모두 지원)
    try:
        df = fdr.DataReader(symbol)
    except Exception as e:
        return jsonify({"error": f"종목 데이터를 불러오지 못했습니다: {e}"}), 400

    # Prophet 입력 포맷 변환
    data = df.reset_index()[['Date', 'Close']].rename(columns={'Date': 'ds', 'Close': 'y'}).dropna()
    if len(data) < 365:
        return jsonify({"error": "데이터가 1년 미만입니다."}), 400

    # Prophet 모델 학습
    model = Prophet(daily_seasonality=True)
    model.fit(data)

    # 예측 날짜 생성 (거래일 기준)
    future = model.make_future_dataframe(periods=period, freq='B')
    forecast = model.predict(future)

    # 최근 N일 예측값만 반환
    forecast_slice = forecast[['ds', 'yhat']].tail(period)
    predict_list = [
        {"날짜": row.ds.strftime('%Y-%m-%d'), "예측종가": round(row.yhat, 2)}
        for _, row in forecast_slice.iterrows()
    ]

    # 응답 구조
    result = {
        "종목명": symbol,
        "예측종가_10일": predict_list,
        "최신일자_실제종가": float(data.iloc[-1].y),
    }
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)


