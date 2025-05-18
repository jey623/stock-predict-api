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

# ✅ 토큰 발급 함수 (JSON 기반)
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
    res = r.json()
    if "token" not in res:
        raise Exception(f"❌ 토큰 발급 실패: {res}")
    return res["token"]

# ✅ 차트 데이터 요청 함수 (ka10081)
def request_chart_data(token, code):
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
        "upd_stkpc_tp": "1"
    }
    r = requests.post(url, headers=headers, json=data)
    if r.status_code != 200:
        raise Exception(f"❌ 데이터 요청 실패: {r.status_code} {r.text}")
    return r.json()

# ✅ 기술적 분석 함수
def analyze_response_data(response_data):
    prices = response_data.get("output2", [])
    if not prices:
        return {"error": "❌ 데이터 수신 실패 또는 데이터 없음."}

    df = pd.DataFrame(prices)
    df["stck_clpr"] = pd.to_numeric(df["stck_clpr"], errors="coerce")
    df = df.dropna()

    if df.empty:
        return {"error": "❌ 유효한 종가 데이터가 없습니다."}

    df = df.sort_values(by="stck_bsop_date")
    df.set_index("stck_bsop_date", inplace=True)

    # 기술적 지표 추가
    df["MA20"] = df["stck_clpr"].rolling(window=20).mean()
    df["STD20"] = df["stck_clpr"].rolling(window=20).std()
    df["UpperBB"] = df["MA20"] + 2 * df["STD20"]
    df["LowerBB"] = df["MA20"] - 2 * df["STD20"]
    df["RSI"] = ta.momentum.RSIIndicator(close=df["stck_clpr"], window=14).rsi()

    return {
        "조회건수": len(df),
        "최근종가": int(df["stck_clpr"].iloc[-1]),
        "20일 평균": round(df["MA20"].iloc[-1], 2),
        "상단 볼린저밴드": round(df["UpperBB"].iloc[-1], 2),
        "하단 볼린저밴드": round(df["LowerBB"].iloc[-1], 2),
        "RSI": round(df["RSI"].iloc[-1], 2)
    }

# ✅ 루트 응답
@app.route("/")
def home():
    return Response("📡 Kiwoom Signal Analysis API is live.", content_type="text/plain; charset=utf-8")

# ✅ 분석 API
@app.route("/analyze")
def api_analyze():
    code = request.args.get("symbol", "")
    if not code:
        return jsonify({"error": "❗ symbol 파라미터가 필요합니다."}), 400

    try:
        token = get_token()
        data = request_chart_data(token, code)
        result = analyze_response_data(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"서버 오류: {e}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


