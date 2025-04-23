from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import traceback

app = Flask(__name__)

@app.route("/predict", methods=["GET"])
def predict():
    stock_code = request.args.get("stock")
    if not stock_code:
        return jsonify({"error": "Missing 'stock' parameter"}), 400

    try:
        print(f"✅ [1] 입력된 종목코드: {stock_code}")

        # 최근 5년간 데이터만 사용 (메모리 절약)
        df = fdr.DataReader(stock_code, start="2020-01-01")
        print(f"✅ [2] 데이터 수집 완료. 총 행 수: {len(df)}")

        # 기술적 지표 계산
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['RSI'] = compute_rsi(df['Close'], 14)
        df.dropna(inplace=True)
        print(f"✅ [3] 기술적 지표 적용 및 결측 제거 완료. 사용 행 수: {len(df)}")

        # 모델 로드
        model = joblib.load("model/xgb_model.pkl")
        feature_cols = ['Close', 'MA20', 'MA60', 'RSI']

        # 예측 수행
        predictions = []
        for i in range(len(df)):
            try:
                row = df[feature_cols].iloc[i].values.reshape(1, -1)
                pred = model.predict(row)[0]
                predictions.append(pred)
            except Exception as e:
                print(f"❌ 예측 오류 (i={i}): {e}")
                continue

        # 마지막 종가 및 예측값
        last_close = df.iloc[-1]['Close']
        predicted = predictions[-1]
        expected_return = round((predicted - last_close) / last_close * 100, 2)

        return jsonify({
            "stock": stock_code,
            "last_close": round(last_close),
            "predicted_close": round(predicted, 2),
            "expected_return(%)": expected_return
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


