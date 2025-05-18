import os
import requests
import pandas as pd
import ta
from flask import Flask, request, jsonify, Response
from datetime import datetime

app = Flask(__name__)

# ✅ 환경변수에서 AppKey, AppSecret 불러오기
def load_keys():
    app_key = os.environ.get("APP_KEY", "").strip()
    app_secret = os.environ.get("APP_SECRET", "").strip()
    if not app_key or not app_secret:
        raise Exception("❌ 환경변수 APP_KEY 또는 APP_SECRET이 설정되지 않았습니다.")
    return app_key, app_secret

APP_KEY, APP_SECRET = load_keys()

# ✅ 접근 토큰 발급
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

# ✅ 주식 차트 데이터 조회 (ka10081)
def get_chart_data(token, symbol, base_date):
    url = "https://api.kiwoom.com/api/dostk/chart"
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "cont-yn": "N",
        "next-key": "",
        "api-id": "ka10081",
    }
    data = {
        "stk_cd": symbol,
        "base_dt": base_date,
        "upd_stkpc_tp": "1"
    }
    r = requests.post(url, headers=headers, json=data)
    if r.status_code != 200:
        raise Exception(f"❌ 데이터 수신 실패: {r.status_code} {r.text}")
    return r.json()

# ✅ 기술적 분석
def analyze_technical_indicators(raw_json):
    prices = raw_json.get("output2", [])
    if not prices:
        return {"error": "❌ 데이터 수신 실패 또는 데이터 없음."}

    df = pd.DataFrame(prices)
    df["일자"] = pd.to_datetime(df["stck_bsop_date"], format="%Y%m%d")
    df = df.sort_values("일자").reset_index(drop=True)

    df["종가"] = pd.to_numeric(df["stck_clpr"], errors="coerce")
    df["고가"] = pd.to_numeric(df["stck_hgpr"], errors="coerce")
    df["저가"] = pd.to_numeric(df["stck_lwpr"], errors="coerce")
    df["시가"] = pd.to_numeric(df["stck_oprc"], errors="coerce")
    df["거래량"] = pd.to_numeric(df["acml_vol"], errors="coerce")

    # 기술적 지표 예시
    df["MA20"] = df["종가"].rolling(window=20).mean()
    df["MA60"] = df["종가"].rolling(window=60).mean()
    df["이격도_20일"] = (df["종가"] / df["MA20"]) * 100
    df["이격도_60일"] = (df["종가"] / df["MA60"]) * 100

    rsi = ta.momentum.RSIIndicator(close=df["종가"], window=14)
    df["RSI"] = rsi.rsi()

    obv = ta.volume.OnBalanceVolumeIndicator(close=df["종가"], volume=df["거래량"]).on_balance_volume()
    df["OBV"] = obv

    latest = df.iloc[-1]
    result = {
        "현재일자": latest["일자"].strftime("%Y-%m-%d"),
        "현재가": round(latest["종가"], 2),
        "이격도_20일": f"{latest['이격도_20일']:.1f}%",
        "이격도_60일": f"{latest['이격도_60일']:.1f}%",
        "RSI": round(latest["RSI"], 2),
        "OBV": round(latest["OBV"], 2),
    }
    return result

# ✅ 루트 경로
@app.route("/")
def home():
    return Response("📈 Kiwoom Signal Analysis API is running.", content_type="text/plain; charset=utf-8")

# ✅ 분석 API
@app.route("/analyze")
def api_analyze():
    symbol = request.args.get("symbol", "")
    date = request.args.get("date", datetime.today().strftime("%Y%m%d"))
    if not symbol:
        return jsonify({"error": "❗ symbol 파라미터가 필요합니다."}), 400
    try:
        token = get_token()
        raw_data = get_chart_data(token, symbol, date)
        result = analyze_technical_indicators(raw_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"서버 내부 오류: {e}"}), 500

# ✅ 실행
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

