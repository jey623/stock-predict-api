import os
import requests
import pandas as pd
import ta
from flask import Flask, request, jsonify, Response
from datetime import datetime

app = Flask(__name__)

# ✅ 키 로드
def load_keys():
    app_key = os.environ.get("APP_KEY", "").strip()
    app_secret = os.environ.get("APP_SECRET", "").strip()
    if not app_key or not app_secret:
        raise Exception("❌ APP_KEY 또는 APP_SECRET 환경변수가 누락됨")
    return app_key, app_secret

APP_KEY, APP_SECRET = load_keys()

# ✅ 토큰 발급
def get_token():
    url = "https://api.kiwoom.com/oauth2/token"
    headers = {"Content-Type": "application/json;charset=UTF-8"}
    data = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "secretkey": APP_SECRET
    }
    res = requests.post(url, headers=headers, json=data)
    if res.status_code != 200 or "token" not in res.json():
        raise Exception(f"❌ 토큰 발급 실패: {res.status_code} {res.text}")
    return res.json()["token"]

# ✅ 주식일봉차트조회요청 (ka10081)
def request_ka10081(token, code, base_date):
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
    res = requests.post(url, headers=headers, json=data)
    if res.status_code != 200:
        raise Exception(f"❌ ka10081 실패: {res.status_code} {res.text}")
    return res.json()

# ✅ 일별주가요청 (ka10086) - 대체 호출
def request_ka10086(token, code, base_date):
    url = "https://api.kiwoom.com/api/dostk/mrkcond"
    headers = {
        "authorization": f"Bearer {token}",
        "content-type": "application/json;charset=UTF-8",
        "api-id": "ka10086",
        "cont-yn": "N",
        "next-key": ""
    }
    data = {
        "stk_cd": code,
        "qry_dt": base_date,
        "indc_tp": "0"
    }
    res = requests.post(url, headers=headers, json=data)
    if res.status_code != 200:
        raise Exception(f"❌ ka10086 실패: {res.status_code} {res.text}")
    return res.json()

# ✅ 분석 함수 (기술적 분석 유지)
def analyze_price_data(prices):
    df = pd.DataFrame(prices)
    df["stck_clpr"] = pd.to_numeric(df.get("stck_clpr") or df.get("close_pric"), errors="coerce")
    if df.empty or df["stck_clpr"].isnull().all():
        return {"error": "📭 유효한 가격 데이터 없음"}
    
    df["rsi"] = ta.momentum.RSIIndicator(df["stck_clpr"]).rsi()
    df["ma20"] = ta.trend.sma_indicator(df["stck_clpr"], window=20)
    
    return {
        "종가 평균": round(df["stck_clpr"].mean(), 2),
        "RSI 최근": round(df["rsi"].dropna().iloc[-1], 2) if not df["rsi"].dropna().empty else None,
        "MA20 최근": round(df["ma20"].dropna().iloc[-1], 2) if not df["ma20"].dropna().empty else None,
        "데이터 수": len(df)
    }

# ✅ 기본 엔드포인트
@app.route("/")
def home():
    return Response("📡 Kiwoom Signal API is live", content_type="text/plain; charset=utf-8")

# ✅ 분석 API
@app.route("/analyze")
def api_analyze():
    code = request.args.get("symbol", "")
    base_date = request.args.get("date", datetime.today().strftime("%Y%m%d"))
    if not code:
        return jsonify({"error": "❗ symbol 파라미터 필요"}), 400

    try:
        token = get_token()
        try:
            data = request_ka10081(token, code, base_date)
            prices = data.get("output2", [])
            if not prices:
                raise ValueError("⚠️ ka10081 결과 없음")
        except:
            data = request_ka10086(token, code, base_date)
            prices = data.get("daly_stkpc", [])

        result = analyze_price_data(prices)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"서버 오류: {e}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

