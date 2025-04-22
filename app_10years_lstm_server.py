from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from keras.models import load_model
import datetime

app = Flask(__name__)

@app.route("/", methods=["GET", "HEAD"])
def healthcheck():
    return "OK", 200


def load_stock_data(stock_code, years=5):
    end = datetime.datetime.today()
    start = end - datetime.timedelta(days=365 * years)
    df = fdr.DataReader(stock_code, start, end)
    return df[['Close']]


def prepare_lstm_data(df, lookback=60):
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df)
    last_sequence = scaled_data[-lookback:]
    X = np.array([last_sequence])
    return X, scaler


@app.route("/predict", methods=["GET"])
def predict():
    stock_code = request.args.get("code")
    if not stock_code:
        return jsonify({"error": "code 파라미터가 필요합니다."}), 400

    try:
        df = load_stock_data(stock_code)
        X, scaler = prepare_lstm_data(df)
        model = load_model("lstm_model.h5")
        prediction = model.predict(X)
        predicted_price = scaler.inverse_transform(prediction)[0][0]
        return jsonify({
            "stock_code": stock_code,
            "predicted_price": round(float(predicted_price), 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


