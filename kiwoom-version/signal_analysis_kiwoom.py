import os
import requests
import pandas as pd
import ta
from flask import Flask, request, jsonify, Response
from datetime import datetime

app = Flask(__name__)

# ✅ AppKey, AppSecret 환경변수에서 불러오기
def load_keys():
    app_key = os.environ.get("APP_KEY", "").strip()
    app_secret = os.environ.get("APP_SECRET", "").strip()
    if not app_key or not app_secret:
        raise Exception("❌ 환경변수 APP_KEY 또는 APP_SECRET이 설정되지 않았습니다.")
    return app_key, app_secret

APP_KEY, APP_SECRET = load_keys()

# ✅ 토큰 발급 함수
def get_token():
    url = "https://oauth.kiwoom.com/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    r = requests.post(url, headers=headers, data=data)
    if r.status_code != 200:
        raise Exception(f"❌ 토큰 발급 실패: {r.status_code} {r.text}")
    return r.json()["access_token"]

# ✅ 데이터 요청 함수 (예: ka10081)
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
    r = requests.post(url, headers=headers, json=data)
    if r.status_code != 200:
        raise Exception(f"❌ 데이터 요청 실패: {r.status_code} {r.text}")
    return r.json()

# ✅ 분석 함수 예시 (단순 종가 평균)
def analyze_response_data(response_data):
    prices = response_data.get("output2", [])
    if not prices:
        return {"error": "데이터 없음"}
    df = pd.DataFrame(prices)
    df["stck_clpr"] = pd.to_numeric(df["stck_clpr"], errors="coerce")
    mean_price = df["stck_clpr"].mean()
    return {
        "조회건수": len(df),
        "종가평균": round(mean_price, 2)
    }

# ✅ 루트 응답
@app.route("/")
def home():
    return Response("Signal Analysis API is running.", content_type="text/plain; charset=utf-8")

# ✅ 분석 API
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
        return jsonify({"error": f"서버 내부 오류: {e}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
