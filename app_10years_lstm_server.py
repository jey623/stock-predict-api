from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM
import FinanceDataReader as fdr
import datetime as dt

app = Flask(__name__)

def get_stock_data(stock_code):
    start_date = (dt.datetime.today() - dt.timedelta(days=365*10)).strftime('%Y-%m-%d')
    df = fdr.DataReader(stock_code, start=start_date)
    df = df[['Close']].dropna()
    return df

def create_dataset(data, look_back):
    X, Y = [], []
    for i in range(len(data) - look_back - 60):
        X.append(data[i:(i + look_back), 0])
        Y.append([data[i + d, 0] for d in [1, 2, 5, 10, 20, 40, 60]])
    return np.array(X), np.array(Y)

def build_model(input_shape):
    model = Sequential()
    model.add(LSTM(64, input_shape=input_shape))
    model.add(Dense(6))
    model.compile(loss='mean_squared_error', optimizer='adam')
    return model

@app.route('/predict_lstm', methods=['GET'])
def predict_lstm():
    stock = request.args.get('stock')
    try:
        df = get_stock_data(stock)
    except Exception as e:
        return jsonify({'error': str(e)})

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(df.values)

    look_back = 60
    X, Y = create_dataset(scaled_data, look_back)

    if len(X) == 0:
        return jsonify({'error': 'Not enough data for training'})

    X = np.reshape(X, (X.shape[0], X.shape[1], 1))
    model = build_model((look_back, 1))
    model.fit(X, Y, epochs=10, batch_size=32, verbose=0)

    last_data = scaled_data[-look_back:]
    input_data = np.reshape(last_data, (1, look_back, 1))
    prediction = model.predict(input_data)[0]

    predicted_prices = scaler.inverse_transform(prediction.reshape(-1, 1)).flatten()

    periods = ['1일후', '2일후', '5일후', '10일후', '20일후', '40일후', '60일후']
    result = {period: round(price, 2) for period, price in zip(periods, predicted_prices)}

    return jsonify({
        '종목명': stock,
        '예측결과': result
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=True)

