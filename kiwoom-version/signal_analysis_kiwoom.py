import os
import requests
import pandas as pd
import numpy as np
import ta
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ----------------------------- ✅ 환경변수에서 키 불러오기 -----------------------------
def load_keys():
    app_key = os.environ.get("APP_KEY", "").strip()
    app_secret = os.environ.get("APP_SECRET", "").strip()
    if not app_key or not app_secret:
        raise Exception("❌ 환경변수 APP_KEY 또는 APP_SECRET이 누락되었습니다.")
    return app_key, app_secret

APP_KEY, APP_SECRET = load_keys()

# ----------------------------- ✅ 토큰 발급 함수 -----------------------------
def get_token():
    url = "https://api.kiwoom.com/oauth2/token"
    headers = {"Content-Type": "application/json;charset=UTF-8"}
    data = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "secretkey": APP_SECRET
    }
    r = requests.post(url, headers=headers, json=data)
    if r.status_code != 200:
        raise Exception(f"❌ 토큰 발급 실패: {r.status_code} {r.text}")
    return r.json().get("token")

# ----------------------------- ✅ 일별 주가 요청 (ka10086) -----------------------------
def request_kiwoom_daily_data(token, code, qry_date, indc_tp='0'):
    url = "https://api.kiwoom.com/api/dostk/mrkcond"
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10086",
        "cont-yn": "N",
        "next-key": ""
    }
    data = {
        "stk_cd": code,
        "qry_dt": qry_date,
        "indc_tp": indc_tp
    }
    r = requests.post(url, headers=headers, json=data)
    if r.status_code != 200:
        raise Exception(f"❌ 요청 실패: {r.status_code}, {r.text}")
    js = r.json()
    if "daly_stkpc" not in js:
        raise Exception(f"❌ 데이터 없음 또는 형식 오류: {js}")
    df = pd.DataFrame(js["daly_stkpc"])
    df.rename(columns={
        "date": "Date", "open_pric": "Open", "high_pric": "High",
        "low_pric": "Low", "close_pric": "Close", "trde_qty": "Volume"
    }, inplace=True)
    df[["Open", "High", "Low", "Close", "Volume"]] = df[["Open", "High", "Low", "Close", "Volume"]].apply(pd.to_numeric, errors='coerce')
    df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d")
    df = df.sort_values("Date").reset_index(drop=True)
    return df.tail(300)

# ----------------------------- ✅ 기술적 분석 함수 -----------------------------
def analyze_e_book_signals(df):
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA60"] = df["Close"].rolling(window=60).mean()
    df["DIS20"] = (df["Close"] / df["MA20"]) * 100
    df["OBV"] = ta.volume.OnBalanceVolumeIndicator(df["Close"], df["Volume"]).on_balance_volume()
    df.dropna(inplace=True)
    return {
        "골든크로스": bool((df["MA20"].iloc[-2] < df["MA60"].iloc[-2]) and (df["MA20"].iloc[-1] > df["MA60"].iloc[-1])),
        "데드크로스": bool((df["MA20"].iloc[-2] > df["MA60"].iloc[-2]) and (df["MA20"].iloc[-1] < df["MA60"].iloc[-1])),
        "이격도": f"{df['DIS20'].iloc[-1]:.2f}%",
        "OBV_방향": "상승" if df['OBV'].iloc[-1] > df['OBV'].iloc[-2] else "하락",
    }

# ----------------------------- ✅ 예측 계산 -----------------------------
def calculate_predictions(df):
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df.dropna(subset=["Close"], inplace=True)
    result = {}
    for days in [1, 5, 10, 20, 40, 60, 80]:
        if len(df) > days:
            change = ((df["Close"].iloc[-1] - df["Close"].iloc[-days]) / df["Close"].iloc[-days]) * 100
            result[f"{days}일변화율"] = round(change, 2)
            result[f"{days}일예측가"] = round(df["Close"].iloc[-1] * (1 + change / 100), 2)
    return result

# ----------------------------- ✅ API 엔드포인트 -----------------------------
@app.route("/")
def home():
    return "✅ Signal Analysis API is running."

@app.route("/analyze")
def analyze():
    code = request.args.get("symbol", "005930")
    today = datetime.today().strftime("%Y%m%d")
    try:
        token = get_token()
        df = request_kiwoom_daily_data(token, code, today)
        tech = analyze_e_book_signals(df)
        pred = calculate_predictions(df)
        return jsonify({"기술적분석": tech, "변화율_및_예측가": pred})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

