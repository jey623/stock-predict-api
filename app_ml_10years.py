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
warnings.filterwarnings("ignore")

app = Flask(__name__)

@app.route('/')
def home():
    return '✅ XGBoost 10년 예측 API Live!'

@app.route('/predict', methods=['GET'])
def predict():
    stock_code = request.args.get('stock')
    try:
        df = fdr.DataReader(stock_code)
        df = df.tail(2520)  # 10년 기준 거래일 252*10

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

        feature_cols = ['Close', 'MA20', 'MA60', 'RSI', 'MACD', 'MACD_signal', 'CCI', 'BB_high', 'BB_low']
        X, y = [], []

        prediction_days = [1, 2, 5, 10, 20, 40, 60, 80]

        for days in prediction_days:
            for i in range(len(df) - days):
                X.append(df[feature_cols].iloc[i].values)
                y.append(df['Close'].iloc[i + days])

        X = np.array(X)
        y = np.array(y)

        model = xgb.XGBRegressor()
        model.fit(X, y)
        y_pred = model.predict(X)

        mae = round(mean_absolute_error(y, y_pred), 2)
        mse = round(mean_squared_error(y, y_pred), 2)
        rmse = round(np.sqrt(mse), 2)
        r2 = round(r2_score(y, y_pred), 4)

        last_data = df[feature_cols].iloc[-1].values.reshape(1, -1)
        future_preds = model.predict(last_data)[0]

        return jsonify({
            "종목명": f"{stock_code}",
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
        return jsonify({"error": str(e)})

