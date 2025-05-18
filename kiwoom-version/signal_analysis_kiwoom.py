import os
import requests
import pandas as pd
import ta
from flask import Flask, request, jsonify, Response
from datetime import datetime

app = Flask(__name__)

# ✅ 환경변수에서 AppKey, AppSecret 불러오기 (.strip() 포함)
def load_keys():
    app_key = os.environ.get("APP_KEY", "").strip()
    app_secret = os.environ.get("APP_SECRET", "").strip()
    if not app_key or not app_secret:
        raise Exception("❌ 환경변수 APP_KEY 또는 APP_SECRET이 설정되지 않았습니다.")
    return app_key, app_secret

APP_KEY, APP_SECRET = load_keys()

# ✅ 실전투자용 접근토큰 발급
def get_token():
    url = "https://api.kiwoom.com/oauth2/token"
    headers = {"Content-Type": "application/json;charset=UTF-8"}
    data = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "secretkey": APP_SECRET
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(f"❌ 토큰 발급 실패: {response.status_code} {response.text}")
    return response.json()["token"]

# ✅ 주식 차트 데이터 요청 (TR: ka10081)
def request_chart_data(token, code, base_date):
    url = "https://api.kiwoom.com/api/dostk/chart"
    headers = {
        "authorization": f"Bearer {token}",
        "content-type": "application/json;charset=UTF-8",
        "api-id": "ka10081",
        "cont-yn": "N",
        "next-key": ""
    }
    data = {
        "stk_cd": code,
        "base_dt": base_date,
        "upd_stkpc_tp": "1"
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(f"❌ 데이터 요청 실패: {response.status_code} {response.text}")
    return response.json()

# ✅ 기술적 분석 포함
def analyze_response_data(response_data):
    prices = response_data.get("output2", [])
    if not prices:
        raise Exception("❌ 데이터 수신 실패 또는 데이터 없음.")

    df = pd.DataFrame(prices)
    df["stck_clpr"] = pd.to_numeric(df["stck_clpr"], errors="coerce")
    df["date"] = df["stck_bsop_date"].astype(str)

    # 기술적 지표 계산
    df = df.sort_values("date")
    df["MA20"] = ta.trend.sma_indicator(df["stck_clpr"], window=20)
    df["RSI14"] = ta.momentum.rsi(df["stck_clpr"], window=14)
    df["OBV"] = ta.volume.on_balance_volume(df["stck_clpr"], pd.to_numeric(df["acml_vol"], errors="coerce"))

    # 결과 요약
    result = {
        "조회건수": len(df),
        "평균종가": round(df["stck_clpr"].mean(), 2),
        "최근종가": int(df["stck_clpr"].iloc[-1]),
        "최근MA20": round(df["MA20"].iloc[-1], 2),
        "최근RSI14": round(df["RSI14"].iloc[-1], 2),
        "최근OBV": int(df["OBV"].iloc[-1])
    }
    return result

# ✅ 기본 페이지
@app.route("/")
def home():
    return Response("✅ Kiwoom Signal Analysis API is running.", content_type="text/plain; charset=utf-8")

# ✅ 분석용 API
@app.route("/analyze")
def api_analyze():
    code = request.args.get("symbol", "")
    base_date = request.args.get("date", datetime.today().strftime("%Y%m%d"))
    if not code:
        return jsonify({"error": "❗ symbol 파라미터가 필요합니다."}), 400

    try:
        token = get_token()
        data = request_chart_data(token, code, base_date)
        result = analyze_response_data(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ 실행
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

