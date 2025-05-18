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

# ✅ 토큰 발급 함수 (au10001 기준 JSON 방식)
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

# ✅ 일별주가요청 (ka10086)
def request_daily_price(token, code, date=None):
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
        "qry_dt": date if date else datetime.today().strftime("%Y%m%d"),
        "indc_tp": "0"
    }
    r = requests.post(url, headers=headers, json=data)
    if r.status_code != 200:
        raise Exception(f"❌ 데이터 요청 실패: {r.status_code} {r.text}")
    return r.json()

# ✅ 분석 함수 예시 (종가 평균 계산)
def analyze_response_data(response_data):
    prices = response_data.get("daly_stkpc", [])
    if not prices:
        return {"error": "❌ 데이터 수신 실패 또는 데이터 없음."}
    df = pd.DataFrame(prices)
    df["close_pric"] = pd.to_numeric(df["close_pric"], errors="coerce")
    mean_price = df["close_pric"].mean()
    return {
        "조회건수": len(df),
        "종가평균": round(mean_price, 2)
    }

# ✅ 외부 IP 확인 포함 홈 엔드포인트
@app.route("/")
def home():
    try:
        ip = requests.get("https://api.ipify.org").text
    except:
        ip = "외부 IP 조회 실패"
    return Response(
        f"✅ Signal Analysis API is running.\n\n🌐 External IP: {ip}",
        content_type="text/plain; charset=utf-8"
    )

# ✅ 분석 엔드포인트
@app.route("/analyze")
def api_analyze():
    code = request.args.get("symbol", "")
    date = request.args.get("date", None)
    if not code:
        return jsonify({"error": "❗ symbol 파라미터가 필요합니다."}), 400

    try:
        token = get_token()
        data = request_daily_price(token, code, date)
        result = analyze_response_data(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"서버 오류: {e}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

