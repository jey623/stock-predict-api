from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from xgboost import XGBRegressor
import datetime

app = Flask(__name__)

PREDICT_DAYS = [1, 2, 5, 10, 20, 40, 60, 80]

def get_stock_code(name_or_code):
    try:
        df_krx = fdr.StockListing('KRX')
        match = df_krx[df_krx['Name'] == name_or_code]
        if match.empty:
            match = df_krx[df_krx['Code'] == name_or_code]
        if not match.empty:
            return match.iloc[0]['Code'], match.iloc[0]['Name']
        return None, None
    except:
        return None, None

def fetch_data(code):
    today = datetime.datetime.today()
    past = today - datetime.timedelta(days=365 * 10)
    df = fdr.DataReader(code, past.strftime('%Y-%m-%d'))
    return df.dropna()

def create_features_targets(df, days):
    X, y = [], []
    for i in range(len(df) - max(days)):
        features = df['Close'].values[i:i+60]  # 최근 60일 종가 사용
        if len(features) < 60:
            continue
        for d in days:
            target_index = i + 60 + d - 1
            if target_index < len(df):
                X.append(features)
                y.append(df['Close'].values[target_index])
    return np.array(X), np.array(y)

@app.route("/")
def home():
    return "XGBoost 10년치 머신러닝 주가 예측 서버"

@app.route("/predict", methods=["GET"])
def predict():
    stock = request.args.get("stock")
    if not stock:
        return jsonify({"error": "Missing 'stock' parameter"}), 400

    code, name = get_stock_code(stock)
    if not code:
        return jsonify({"error": f"{stock} 종목명을 찾을 수 없습니다."}), 400

    df = fetch_data(code)
    if len(df) < 500:
        return jsonify({"error": f"데이터가 충분하지 않습니다 ({len(df)}일치)."})

    X, y = create_features_targets(df, PREDICT_DAYS)
    if X.shape[0] == 0:
        return jsonify({"error": "학습할 수 있는 데이터가 없습니다."})

    model = XGBRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)

    recent_60 = df['Close'].values[-60:]
    pred_input = recent_60.reshape(1, -1)
    prediction = model.predict(pred_input)[0]

    results = {
        "종목명": f"{name} ({code})",
        "예측일자": PREDICT_DAYS,
        "예측종가": float(round(prediction, 2))
    }
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
