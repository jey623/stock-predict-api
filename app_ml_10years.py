from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from ta.volatility import BollingerBands
from ta.trend import MACD, CCIIndicator
from ta.momentum import RSIIndicator
import warnings
import traceback

warnings.filterwarnings("ignore")

app = Flask(__name__)

@app.route('/')
def home():
    return '✅ XGBoost 10년 예측 API Live!'

@app.route('/predict', methods=['GET'])
def predict():
    stock_code = request.args.get('stock')
    try:
        print("✅ [1] 종목코드:", stock_code)

        df = fdr.DataReader(stock_code)
        print("✅ [2] 데이터 수집 완료. 총 행 수:", len(df))

        df = df.tail(2520)  # 10년치 기준
        df = df[['Close']].copy()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['RSI'] = RSIIndicator(close=df['Close']).rsi()
        macd = MACD(close=df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        df['CCI'] = CCIIndicator(high=df['Close'], low=df['Close'], close=df['Close']).cci()
        bb = BollingerBands(close=df['Close'])
        df['BB_high'] = bb.bollinger_hband()
        df['BB_low'] = bb.bollinger_lband()

        df.dropna(inplace=True)
        print("✅ [3] 기술적 지표 계산 완료. 사용 가능한 데이터 수:", len(df))

        feature_cols = ['Close', 'MA20', 'MA60', 'RSI', 'MACD', 'MACD_signal', 'CCI', 'BB_high', 'BB_low']
        X, y = [], []

        prediction_days = [1, 2, 5, 10, 20, 40, 60, 80]

        for days in prediction_days:
            for i in range(len(df) - days):
                X.append(df[feature_cols].iloc[i].values)
                y.append(df['Close'].iloc[i + days])

        X = np.array(X)
        y = np.array(y)
        print("✅ [4] 학습 데이터 생성 완료. X:", X.shape, "y:", y.shape)

        model = xgb.XGBRegressor()
        model.fit(X, y)
        print("✅ [5] 모델 학습 완료")

        y_pred = model.predict(X)
        mae = round(mean_absolute_error(y, y_pred), 2)
        mse = round(mean_squared_error(y, y_pred), 2)
        rmse = round(np.sqrt(mse), 2)
        r2 = round(r2_score(y, y_pred), 4)
        print("✅ [6] 성능 평가 완료")

        last_data = df[feature_cols].iloc[-1].values.reshape(1, -1)
        future_preds = model.predict(last_data)[0]
        print("✅ [7] 최종 예측 완료:", future_preds)

        return jsonify({
            "종목명": stock_code,
            "예측종가": round(future_preds, 2),
            "예측일자": prediction_days,
            "오차지표": {
                "MAE": mae,
                "MSE": mse,
                "RMSE": rmse,
                "R2": r2
            }
        })

    except Exception as e:
        print("❌ [Error 발생]:")
        print(traceback.format_exc())
        return jsonify({"error": str(e)})



