import os
import time
import requests
import json
import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
import warnings
warnings.filterwarnings("ignore")

APPKEY = os.getenv("APPKEY")
SECRETKEY = os.getenv("SECRETKEY")

ACCESS_TOKEN = None
TOKEN_EXPIRES_AT = 0

# 🔄 access_token 자동 발급 및 갱신
def fetch_access_token():
    print(f"🛠️ APPKEY: {APPKEY[:8]}******")
    print(f"🛠️ SECRETKEY: {SECRETKEY[:8]}******")

    global ACCESS_TOKEN, TOKEN_EXPIRES_AT

    if ACCESS_TOKEN and time.time() < TOKEN_EXPIRES_AT - 60:
        return ACCESS_TOKEN

    url = "https://api.kiwoom.com/oauth2/token"
    headers = {"Content-Type": "application/json;charset=UTF-8"}
    data = {
        "grant_type": "client_credentials",
        "appkey": APPKEY,
        "secretkey": SECRETKEY
    }

    res = requests.post(url, headers=headers, json=data)
    if res.status_code == 200:
        token = res.json().get("access_token") or res.json().get("token")
        expires_in = int(res.json().get("expires_in", 3600))
        ACCESS_TOKEN = token
        TOKEN_EXPIRES_AT = time.time() + expires_in
        print("✅ access_token 발급 성공")
        return token

    print("❌ access_token 발급 실패:", res.status_code, res.text)
    return None

TICKER_DICT = {
    "삼성전자": "005930",
    "펄어비스": "263750",
    "카카오게임즈": "293490"
}

def get_stock_code_from_name(name):
    try:
        search_url = f"https://finance.naver.com/search/search.naver?query={name}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(search_url, headers=headers, timeout=5)
        if res.status_code != 200:
            raise Exception(f"응답 코드: {res.status_code}")
        soup = BeautifulSoup(res.text, 'html.parser')
        link = soup.select_one('a.tltle')
        if link and 'stock.naver.com' not in link['href']:
            code = link['href'].split('=')[-1]
            print(f"🔎 종목코드 크롤링 성공: {name} → {code}")
            return code
    except Exception as e:
        print(f"⚠️ 크롤링 실패: {e}")
    if name in TICKER_DICT:
        print(f"📦 백업코드 사용: {name} → {TICKER_DICT[name]}")
        return TICKER_DICT[name]
    return None

def get_daily_price_data(token, stock_code, qry_dt, start_date):
    url = "https://api.kiwoom.com/api/dostk/mrkcond"
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {token}',
        'api-id': 'ka10086'
    }
    data = {
        "stk_cd": stock_code,
        "qry_dt": qry_dt,
        "start_dt": start_date,
        "indc_tp": "0"
    }
    res = requests.post(url, headers=headers, json=data)
    if res.status_code == 200:
        output = res.json().get("daly_stkpc", [])
        if not output:
            return pd.DataFrame()
        df = pd.DataFrame(output)
        try:
            df = df[["date", "open_pric", "high_pric", "low_pric", "close_pric", "trde_qty"]]
            df.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                df[col] = df[col].astype(str).str.replace("+", "").str.replace("-", "").astype(float)
            df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d")
            df.sort_values("Date", inplace=True)
            return df
        except Exception as e:
            print("❌ 데이터 파싱 실패:", e)
    return pd.DataFrame()

def get_historical_price_data(token, stock_code, min_days=100, max_iter=10):
    all_data = pd.DataFrame()
    current_qry_dt = datetime.now()
    start_date = (current_qry_dt - timedelta(days=1100)).strftime("%Y%m%d")
    iter_count = 0

    while len(all_data) < min_days and iter_count < max_iter:
        qry_dt_str = current_qry_dt.strftime("%Y%m%d")
        print(f"📅 데이터 요청: qry_dt={qry_dt_str}, start_dt={start_date}")
        df_partial = get_daily_price_data(token, stock_code, qry_dt_str, start_date)
        if df_partial.empty:
            break
        all_data = pd.concat([df_partial, all_data]).drop_duplicates(subset="Date")
        all_data.sort_values("Date", inplace=True)
        iter_count += 1
        if not all_data.empty:
            current_qry_dt = all_data["Date"].min() - timedelta(days=1)

    return all_data

def multi_day_prediction(df, future_days=[1, 5, 20, 40, 60]):
    df = df.copy()
    df["Return"] = df["Close"].pct_change()
    df.dropna(inplace=True)
    X_cols = ["Open", "High", "Low", "Close", "Volume", "Return"]
    latest_input = df[X_cols].iloc[[-1]]
    result = {}
    for day in future_days:
        df["Target"] = df["Close"].shift(-day)
        df_model = df.dropna()
        if df_model.empty:
            result[day] = 0
            continue
        X = df_model[X_cols]
        y = df_model["Target"]
        model = XGBRegressor(n_estimators=100, max_depth=3, verbosity=0)
        model.fit(X, y)
        pred = model.predict(latest_input)[0]
        result[day] = pred
    return result, df["Close"].iloc[-1]

def predict_multi_future_from_api(stock_name):
    stock_code = get_stock_code_from_name(stock_name)
    if not stock_code:
        return {"error": f"❌ 종목 코드 검색 실패: {stock_name}"}

    token = fetch_access_token()
    if not token:
        return {"error": "❌ access_token 발급 실패"}

    df = get_historical_price_data(token, stock_code, min_days=100)
    if df.empty or len(df) < 100:
        return {"error": "❌ 데이터 부족 (예측 최소 100일 필요)"}

    latest_date = df["Date"].max()
    current_price = df.loc[df["Date"] == latest_date, "Close"].iloc[0]
    today = datetime.now().date()
    date_diff = (today - latest_date.date()).days
    warning = None
    if date_diff > 3:
        warning = f"⚠️ 최신 종가 기준일: {latest_date.date()} (오늘과 {date_diff}일 차이)"

    pred_dict, _ = multi_day_prediction(df)

    result = {
        "종목명": stock_name,
        "종목코드": stock_code,
        "예측기준일": latest_date.strftime("%Y-%m-%d"),
        "현재가": int(current_price),
        "예측결과": {f"{day}일후": int(price) for day, price in pred_dict.items()}
    }
    if warning:
        result["주의사항"] = warning
    return result

app = Flask(__name__)

@app.route('/')
def index():
    return "✅ /predict?stock=삼성전자 또는 /get_token 호출하세요"

@app.route('/predict')
def predict():
    stock_name = request.args.get('stock')
    if not stock_name:
        return jsonify({"error": "Missing 'stock' parameter"}), 400
    result = predict_multi_future_from_api(stock_name)
    return jsonify(result)

@app.route('/get_token')
def get_token():
    token = fetch_access_token()
    if token:
        return jsonify({"access_token": token})
    return jsonify({"error": "❌ 토큰 발급 실패"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)


