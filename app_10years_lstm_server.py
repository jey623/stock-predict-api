from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
import FinanceDataReader as fdr
import datetime

app = Flask(__name__)

# 🔹 헬스체크용 루트 라우터 (Render 포트 인식용)
@app.route("/", methods=["GET", "HEAD"])
def healthcheck():
    return "OK", 200

# 🔹 유틸: 주가 데이터 로딩
def load_stock_data(stock_name, years=5):
    end_date = datetime.datetime.today()
    start_date = end_date - datetime.timedelta(days=365 * years)
    df = fdr.DataReader(stock_name, start=start_date, end=end_date)
    df = df[['Close']]
    df.dropna(inplace=True)
    return df

# 🔹 유틸: 데이터 전처리 + LSTM 입력 데이터 생성
def prepare_lstm_data(df, lookback=60):
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df)
    X = []
    for i in range(lookback, len(scaled)):
        X.append(scaled[i - lookback:i, 0])
    X = np.array(X)
    X = X.reshape((X.shape[0], X.shape[1], 1))
    return X, scaler

# 🔹 예측 API
@app.route("/predict", methods=["GET"])
def predict():
    stock = request.args.get("stock")
    if not stock:
        return jsonify({"error": "종목명을 지정해주세요. 예: /predict?stock=삼성전자"})

    try:
        df = load_stock_data(stock)
        X, scaler = prepare_lstm_data(df)
        model = load_model("lstm_model.h5")  # 모델 파일명은 서버에 따라 변경 가능

        # 가장 최근 입력 데이터를 예측
        last_input = X[-1].reshape(1, 60, 1)
        predicted_scaled = model.predict(last_input)
        predicted_price = scaler.inverse_transform(predicted_scaled)[0][0]

        current_price = df['Close'].iloc[-1]
        predicted_change = round((predicted_price - current_price) / current_price * 100, 2)

        return jsonify({
            "종목명": stock,
            "현재가": round(current_price, 2),
            "예측가": round(predicted_price, 2),
            "예상등락률(%)": predicted_change
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# 🔹 Flask 실행 설정은 Render가 자동 처리 (gunicorn)

