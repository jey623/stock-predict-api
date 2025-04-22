# 📁 app_ml_10years.py
from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import xgboost as xgb
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator
from ta.trend import MACD
import datetime

app = Flask(__name__)

@app.route('/predict', methods=['GET'])
def predict():
    stock = request.args.get('stock')  # 예: '삼성전자'

    try:
        # 종목코드 자동 변환
        code_df = fdr.StockListing('KRX')
        row = code_df[code_df['Name'] == stock]
        if row.empty:
            return jsonify({'error': f'{stock} 종목명을 찾을 수 없습니다.'}), 400

        code = row.iloc[0]['Code']

        # 10년치 데이터 수집
        end = datetime.datetime.today()
        start = end - datetime.timedelta(days=365*10)
        df = fdr.DataReader(code, start, end)

        # 기술적 지표 추가
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
        macd = MACD(close=df['Close'])
        df['MACD'] = macd.macd()
        df['Signal'] = macd.macd_signal()

        df = df.dropna()

        # 특성(X), 레이블(y) 준비
        X = df[['MA20', 'MA60', 'RSI', 'MACD', 'Signal']].values
        y = df['Close'].shift(-1).dropna().values[:-1]
        X = X[:-1]

        model = xgb.XGBRegressor()
        model.fit(X, y)

        last_data = df[['MA20', 'MA60', 'RSI', 'MACD', 'Signal']].iloc[-1].values.reshape(1, -1)
        predicted_price = model.predict(last_data)[0]
        current_price = df['Close'].iloc[-1]

        return jsonify({
            '종목명': stock,
            '현재가': round(current_price, 2),
            '다음날 예측가': round(predicted_price, 2),
            '예상 상승률(%)': round((predicted_price - current_price) / current_price * 100, 2)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run()
