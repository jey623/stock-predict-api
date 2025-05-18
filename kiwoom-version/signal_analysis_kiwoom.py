import os
import requests
import pandas as pd
import ta
from flask import Flask, request, jsonify, Response
from datetime import datetime

app = Flask(__name__)

# ✅ 환경변수에서 APP_KEY, APP_SECRET 불러오기
def load_keys():
    app_key = os.environ.get("APP_KEY", "").strip()
    app_secret = os.environ.get("APP_SECRET", "").strip()
    if not app_key or not app_secret:
        raise Exception("❌ 환경변수 APP_KEY 또는 APP_SECRET이 설정되지 않았습니다.")
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
    r = requests.post(url, headers=headers, json=data)
    if r.status_code != 200:
        raise Exception(f"❌ 토큰 발급 실패: {r.status_code} {r.text}")
    return r.json()["token"]  # ✅ 키움 REST는 token 필드임

# ✅ 차트 데이터 요청 (일봉)
def request_chart_data(token, code, base_date=None):
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
    if base_date:
        data["base_dt"] = base_date

    r = requests.post(url, headers=headers, json=data)
    if r.status_code != 200:
        raise Exception(f"❌ 데이터 요청 실패: {r.status_code} {r.text}")
    return r.json()

# ✅ 기술적 분석 함수 (TA-lib 기반)
def analyze_response_data(response_data):
    prices = response_data.get("output2", [])
    if not prices:
        return {"error": "❌ 데이터 수신 실패 또는 데이터 없음."}

    df = pd.DataFrame(prices)
    df["stck_clpr"] = pd.to_numeric(df["stck_clpr"], errors="coerce")
    df["tradd_vol"] = pd.to_numeric(df["tradd_vol"], errors="coerce")

    # 최신 60일 기준
    df = df.sort_values("stck_bsop_date").reset_index(drop=True)
    df = df.tail(60)

    result = {}

    # 이동평균
    df["MA5"] = df["stck_clpr"].rolling(window=5).mean()
    df["MA20"] = df["stck_clpr"].rolling(window=20).mean()
    result["이동평균선"] = {
        "5일": round(df["MA5"].iloc[-1], 2),
        "20일": round(df["MA20"].iloc[-1], 2)
    }

    # 이격도
    result["이격도"] = {
        "5일": f'{df["stck_clpr"].iloc[-1] / df["MA5"].iloc[-1] * 100:.2f}%',
        "20일": f'{df["stck_clpr"].iloc[-1] / df["MA20"].iloc[-1] * 100:.2f}%'
    }

    # OBV
    df["OBV"] = ta.volume.OnBalanceVolumeIndicator(close=df["stck_clpr"], volume=df["tradd_vol"]).obv()
    result["OBV"] = f"{int(df['OBV'].iloc[-1])}"

    # 현재가
    result["현재가"] = int(df["stck_clpr"].iloc[-1])

    return result

# ✅ 기본 확인용
@app.route("/")
def home():
    return Response("✅ Kiwoom Signal Analysis API is running.", content_type="text/plain; charset=utf-8")

# ✅ 분석 요청 API
@app.route("/analyze")
def api_analyze():
    code = request.args.get("symbol", "")
    base_date = request.args.get("date", "")  # optional

    if not code:
        return jsonify({"error": "❗ 'symbol' 파라미터가 필요합니다."}), 400

    try:
        token = get_token()
        data = request_chart_data(token, code, base_date if base_date else None)
        result = analyze_response_data(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"{e}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

