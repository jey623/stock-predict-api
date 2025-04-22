from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
import FinanceDataReader as fdr

app = Flask(__name__)

# 모델 로드 (반드시 서버 루트에 모델 파일이 있어야 함)
model = tf.keras.models.load_model("lstm_model.h5")

# 입력 형태 맞추기 위한 함수
def preprocess_data(df, sequence_length=60):
    df = df[['Close']]
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df)

    X = []
    for i in range(sequence_length, len(scaled_data)):
        X.append(scaled_data[i-sequence_length:i, 0])
    X = np.array(X)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))

    return X, scaler

@app.route('/')
def home():
    return "✅ 주가 예측 서버 정상 작동 중!"

@app.route('/predict', methods=['GET'])
def predict():
    stock_name = request.args.get('code')

    try:
        df = fdr.DataReader(stock_name, start='2019-01-01')
    except Exception as e:
        return jsonify({'error': f'데이터 수집 실패: {str(e)}'})

    if df is None or df.empty:
        return jsonify({'error': '주가 데이터가 비어 있습니다.'})

    X, scaler = preprocess_data(df)
    prediction = model.predict(np.array([X[-1]]))  # 가장 최근 데이터 기반 예측
    predicted_price = scaler.inverse_transform(prediction)[0][0]

    return jsonify({
        'stock': stock_name,
        'predicted_price': round(float(predicted_price), 2)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

