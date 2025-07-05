from flask import Flask, request, jsonify
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import pandas as pd
import ta
from sklearn.preprocessing import MinMaxScaler
import torch
import torch.nn as nn
import numpy as np

app = Flask(__name__)

# DLinear 모델 정의
class DLinear(nn.Module):
    def __init__(self, input_size, pred_len):
        super(DLinear, self).__init__()
        self.linear = nn.Linear(input_size, pred_len)

    def forward(self, x):
        return self.linear(x)

# 모델 학습 함수
def train_dlinear_model(series, input_len=60, pred_len=5):
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(series.reshape(-1, 1)).flatten()

    X, y = [], []
    for i in range(len(scaled) - input_len - pred_len):
        X.append(scaled[i:i+input_len])
        y.append(scaled[i+input_len:i+input_len+pred_len])

    X, y = np.array(X), np.array(y)
    X_tensor = torch.tensor(X, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32)

    model = DLinear(input_len, pred_len)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    criterion = nn.MSELoss()

    for _ in range(100):  # 에폭 수 줄임
        model.train()
        optimizer.zero_grad()
        output = model(X_tensor)
        loss = criterion(output, y_tensor)
        loss.backward()
        optimizer.step()

    return model, scaler

# 예측 함수
def predict_next_5_days(model, scaler, series, input_len=60):
    scaled = scaler.transform(series.reshape(-1, 1)).flatten()
    last_input = torch.tensor(scaled[-input_len:], dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        pred_scaled = model(last_input).numpy().flatten()
    pred = scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()

    last_date = series.index[-1]
    prediction_dates = pd.bdate_range(last_date + timedelta(days=1), periods=5)

    return [
        {"날짜": date.strftime('%Y-%m-%d'), "예측종가": round(price, 2)}
        for date, price in zip(prediction_dates, pred)
    ]

@app.route('/full_analysis', methods=['GET'])
def get_stock_technical_data():
    symbol = request.args.get('symbol')
    if not symbol:
        return "symbol 파라미터는 필수입니다.", 400

    try:
        end_date = datetime.today()
        start_date = end_date - timedelta(days=5*365)  # 최근 5년치 데이터로 변경
        df = fdr.DataReader(symbol, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        df.reset_index(inplace=True)

        df['RSI'] = ta.momentum.RSIIndicator(close=df['Close']).rsi()
        df['CCI'] = ta.trend.cci(high=df['High'], low=df['Low'], close=df['Close'])
        df['OBV'] = ta.volume.OnBalanceVolumeIndicator(close=df['Close'], volume=df['Volume']).on_balance_volume()

        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['MA120'] = df['Close'].rolling(window=120).mean()
        df['Disparity'] = df['Close'] / df['MA20'] * 100

        df.dropna(inplace=True)
        df.set_index('Date', inplace=True)

        close_series = df['Close']
        model, scaler = train_dlinear_model(close_series.values)
        prediction = predict_next_5_days(model, scaler, close_series)

        technicals = {
            "RSI": round(df['RSI'].iloc[-1], 2),
            "CCI": round(df['CCI'].iloc[-1], 2),
            "OBV": int(df['OBV'].iloc[-1]),
            "Disparity": round(df['Disparity'].iloc[-1], 2),
            "MA5": round(df['MA5'].iloc[-1], 2),
            "MA20": round(df['MA20'].iloc[-1], 2),
            "MA60": round(df['MA60'].iloc[-1], 2),
            "MA120": round(df['MA120'].iloc[-1], 2)
        }

        return jsonify({
            "기술지표": technicals,
            "예측종가_5일": prediction
        })

    except Exception as e:
        return f"분석 중 오류 발생: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
