import pandas as pd
import numpy as np
import requests
import ta
from datetime import datetime
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# 🔐 APP_KEY, APP_SECRET을 텍스트 파일에서 안전하게 불러오기
def load_keys():
    with open("56499501_appkey.txt", "r") as f:
        app_key = f.read().strip()
    with open("56499501_secretkey.txt", "r") as f:
        app_secret = f.read().strip()
    return app_key, app_secret

APP_KEY, APP_SECRET = load_keys()
BASE_URL = 'https://api.kiwoom.com'
access_token_global = None

# ✅ Access Token 자동 발급
def get_access_token():
    global access_token_global
    if access_token_global:
        return access_token_global

    url = f"{BASE_URL}/oauth2/tokenP"
    headers = {"content-type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    res = requests.post(url, headers=headers, data=data)
    access_token_global = res.json().get('access_token')
    print('\n🔑 발급받은 access_token:', access_token_global)
    return access_token_global

# ✅ Kiwoom에서 500일 일봉 데이터 조회
def get_ohlcv_kiwoom(code):
    access_token = get_access_token()
    url = f"{BASE_URL}/api/dostk/chart"
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {access_token}",
        "api-id": "ka10081"
    }

    today = datetime.now()
    base_dt = today.strftime('%Y%m%d')

    data = {
        "stk_cd": code,
        "base_dt": base_dt,
        "prdt_type_cd": "1",
        "out_cnt": "500",
        "cont_yn": "N",
        "next_key": ""
    }

    res = requests.post(url, headers=headers, json=data)
    result = res.json()

    print('\n📡 Kiwoom API 응답:', json.dumps(result, indent=2, ensure_ascii=False))

    if result.get('return_code') != 0:
        return pd.DataFrame()

    rows = result.get('stk_dt_pole_chart_qry', [])
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.rename(columns={"dt": "Date", "cur_prc": "Close", "high_prc": "High", "low_prc": "Low"})
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)
    df = df[["High", "Low", "Close"]]
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.dropna()
    df = df.sort_index()
    return df

# ✅ 분석 함수: 기술적 지표 계산 + 신호 수식 적용
def analyze_stock(symbol):
    code = symbol if symbol.isdigit() else None
    if not code:
        return {"error": "❌ 종목코드를 입력해주세요."}

    df = get_ohlcv_kiwoom(code)
    if df.empty:
        return {"error": "❌ 데이터 조회 실패 또는 빈 데이터입니다."}

    # 기술적 지표 계산
    df["CCI"] = ta.trend.CCIIndicator(high=df["High"], low=df["Low"], close=df["Close"], window=9).cci()
    df["RSI"] = ta.momentum.RSIIndicator(close=df["Close"], window=14).rsi()
    adx = ta.trend.ADXIndicator(high=df["High"], low=df["Low"], close=df["Close"], window=17)
    df["DI+"] = adx.adx_pos()
    df["DI-"] = adx.adx_neg()
    df["ADX"] = adx.adx()

    ma20 = df["Close"].rolling(window=20).mean()
    envelope_dn = ma20 * (1 - 0.12)
    df["EnvelopeDown"] = envelope_dn
    df["LowestEnv5"] = envelope_dn.rolling(window=5).min()
    df["LowestClose5"] = df["Close"].rolling(window=5).min()

    df = df.dropna()

    # 신호 수식 적용
    df["Signal_Triggered"] = (
        (df["CCI"] < -100) &
        (df["RSI"] < 30) &
        (df["DI-"] > 41) &
        ((df["DI-"] < df["ADX"]) | (df["DI+"] < 5)) &
        (df["LowestEnv5"] > df["LowestClose5"])
    )

    latest = df.iloc[-1]
    signal = bool(latest["Signal_Triggered"])
    current_price = float(latest["Close"])

    # 예측가 및 변화율 계산
    future_prices = {}
    change_rates = {}
    periods = [1, 5, 10, 20, 40, 60, 80]
    for p in periods:
        pred_price = round(current_price * (1 + 0.002 * p), 2)
        future_prices[f"{p}일"] = pred_price
        change_rates[f"{p}일"] = round((pred_price - current_price) / current_price * 100, 2)

    signal_dates = df.index[df["Signal_Triggered"]].strftime("%Y-%m-%d").tolist()

    return {
        "종목명": symbol,
        "종목코드": code,
        "현재가": current_price,
        "예측가": future_prices,
        "변화율": change_rates,
        "신호발생": signal,
        "신호발생일자": signal_dates
    }

# ✅ Flask API 라우팅
@app.route('/')
def index():
    return '📈 Signal Analysis API is running.'

@app.route('/analyze', methods=['GET'])
def api_analyze():
    symbol = request.args.get('symbol', '')
    if not symbol:
        return jsonify({"error": "❌ 종목코드(symbol)가 필요합니다."}), 400
    result = analyze_stock(symbol)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)


