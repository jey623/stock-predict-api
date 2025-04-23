from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import FinanceDataReader as fdr
import xgboost as xgb
import traceback

app = Flask(__name__)

@app.route('/predict', methods=['GET'])
def predict():
    try:
        stock_code = request.args.get('stock')
        if not stock_code:
            return jsonify({"error": "No stock code provided"}), 400

        print(f"✅ [1] 입력된 종목코드: {stock_code}")

        # 5년치 데이터만 수집
        today = datetime.today()
        start_date = today - timedelta(days=365 * 5)
        df = fdr.DataReader(stock_code, start_date, today)
        print(f"✅ [2] 데이터 수집 완료. 총 행 수: {len(df)}")

        # 기술적 지표 계산
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['RSI'] = compute_rsi(df['Close'])
        df = df.dropna()
        print(f"✅ [3] 기술적 지표 적용 및 결측 제거 완료. 사용 행 수: {len(df)}")

        # 예측에 사용할 피처 설정
        feature_cols = ['Close', 'MA20', 'MA60', 'RSI']
        X = []
        for i in range(len(df) - 1):
            X.append(df[feature_cols].iloc[i].values)
        X = np.array(X)

        # 타겟 (다음날 종가)
        y = df['Close'].shift(-1).dropna().values

        # 모델 학습 및 예측
        model = xgb.XGBRegressor(n_estimators=100)
        model.fit(X, y)
        y_pred = model.predict(X)

        # 마지막 예측 결과 반환
        result = {
            "stock": stock_code,
            "last_close": float(df['Close'].iloc[-2]),
            "predicted_close": float(y_pred[-1]),
            "expected_return(%)": round(((y_pred[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100, 2)
        }
        return jsonify(result)

    except Exception as e:
        print("❌ 예측 중 오류 발생:")
        traceback.print_exc()
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

if __name__ == '__main__':
    app.run(debug=True)


