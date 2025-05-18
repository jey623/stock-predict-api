import os
import json
import requests
from datetime import datetime
import pandas as pd
import ta
from flask import Flask, request, jsonify

# ==================== 🔐 API 키 로드 ====================

def load_keys():
    appkey = os.getenv("APP_KEY", "").strip()
    appsecret = os.getenv("APP_SECRET", "").strip()
    if not appkey or not appsecret:
        raise Exception("❌ 환경변수 APP_KEY 또는 APP_SECRET이 설정되지 않았습니다.")
    return appkey, appsecret

# ==================== 🔑 토큰 발급 ====================

def get_access_token():
    appkey, appsecret = load_keys()
    url = "https://openapi.kiwoom.com:9443/oauth2/tokenP"
    headers = {"Content-Type": "application/json"}
    payload = {
        "grant_type": "client_credentials",
        "appkey": appkey,
        "appsecret": appsecret
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"❌ 토큰 발급 실패: {response.status_code} {response.text}")
    return response.json()["access_token"]

# ==================== 📈 일봉 데이터 조회 ====================

def get_ohlcv_kiwoom(stk_cd: str, base_dt: str = None):
    token = get_access_token()
    url = "https://openapi.kiwoom.com:9443/api/v1/quotations/daily-price"
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": os.getenv("APP_KEY").strip(),
        "appsecret": os.getenv("APP_SECRET").strip(),
        "tr_id": "FHKST01010400",
    }

    if base_dt is None:
        base_dt = datetime.now().strftime("%Y%m%d")

    body = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": stk_cd,
        "fid_input_date_1": base_dt,
        "fid_org_adj_prc": "1",
    }

    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        raise Exception(f"❌ 일봉 조회 실패: {response.status_code} {response.text}")

    items = response.json().get("output2", [])
    if not items:
        raise Exception("❌ 데이터가 없습니다.")

    df = pd.DataFrame(items)
    df["날짜"] = pd.to_datetime(df["stck_bsop_date"])
    df.set_index("날짜", inplace=True)
    df = df.sort_index()
    df = df.astype({
        "stck_oprc": float,
        "stck_hgpr": float,
        "stck_lwpr": float,
        "stck_clpr": float,
        "acml_vol": float
    })
    df.rename(columns={
        "stck_oprc": "Open",
        "stck_hgpr": "High",
        "stck_lwpr": "Low",
        "stck_clpr": "Close",
        "acml_vol": "Volume"
    }, inplace=True)
    return df

# ==================== 📊 기술적 분석 (일목균형표 포함) ====================

def analyze_ichimoku(df):
    result = {}

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()
    result["지지선"] = round(df["Close"].rolling(20).min().iloc[-1], 2)
    result["저항선"] = round(df["Close"].rolling(20).max().iloc[-1], 2)

    golden = (df["MA20"] > df["MA60"]) & (df["MA20"].shift() <= df["MA60"].shift())
    dead = (df["MA20"] < df["MA60"]) & (df["MA20"].shift() >= df["MA60"].shift())
    result["골든크로스"] = bool(golden.iloc[-1])
    result["데드크로스"] = bool(dead.iloc[-1])

    d20 = (df["Close"] / df["MA20"] * 100).iloc[-1]
    d60 = (df["Close"] / df["MA60"] * 100).iloc[-1]

    def classify_disparity(val):
        if val < 92:
            return f"과매도({val:.1f}%)"
        elif val > 102:
            return f"과매수({val:.1f}%)"
        else:
            return f"중립({val:.1f}%)"

    result["이격도_20일"] = classify_disparity(d20)
    result["이격도_60일"] = classify_disparity(d60)

    obv = ta.volume.OnBalanceVolumeIndicator(df["Close"], df["Volume"]).on_balance_volume()
    obv_trend = obv.rolling(5).mean().iloc[-1] - obv.rolling(5).mean().iloc[-2]
    price_trend = df["Close"].iloc[-1] - df["Close"].iloc[-2]

    if obv_trend > 0 and price_trend < 0:
        result["OBV_분석"] = "OBV 유지, 주가 하락 → 매집 가능성"
    elif obv_trend < 0 and price_trend > 0:
        result["OBV_분석"] = "OBV 하락, 주가 상승 → 분산 가능성"
    else:
        result["OBV_분석"] = "OBV와 주가 방향 일치"

    # 일목균형표
    nine_high = df["High"].rolling(window=9).max()
    nine_low = df["Low"].rolling(window=9).min()
    df["전환선"] = (nine_high + nine_low) / 2

    twenty_six_high = df["High"].rolling(window=26).max()
    twenty_six_low = df["Low"].rolling(window=26).min()
    df["기준선"] = (twenty_six_high + twenty_six_low) / 2

    df["선행스팬1"] = ((df["전환선"] + df["기준선"]) / 2).shift(26)
    fifty_two_high = df["High"].rolling(window=52).max()
    fifty_two_low = df["Low"].rolling(window=52).min()
    df["선행스팬2"] = ((fifty_two_high + fifty_two_low) / 2).shift(26)
    df["구름하단"] = df[["선행스팬1", "선행스팬2"]].min(axis=1)
    df["전기차이"] = abs(df["전환선"] - df["기준선"])

    result["일목_최저점"] = bool((df["Close"].iloc[-1] < df["구름하단"].iloc[-1]) and (df["전기차이"].iloc[-1] < 0.1))
    result["일목_골든크로스"] = bool((df["전환선"].iloc[-1] > df["기준선"].iloc[-1]) and (df["전환선"].iloc[-2] <= df["기준선"].iloc[-2]))

    if result["일목_최저점"]:
        result["일목_해석"] = "전환선과 기준선이 평행하고 구름대 아래 위치 → 바닥 시그널 가능"
    elif result["일목_골든크로스"]:
        result["일목_해석"] = "전환선이 기준선을 상향 돌파 → 상승 추세 전환 가능"
    else:
        result["일목_해석"] = "일목균형표 기준 특이점 없음"

    return result

# ==================== 🌐 Flask API ====================

app = Flask(__name__)

@app.route("/")
def home():
    return "📈 Kiwoom Signal Analysis API is live."

@app.route("/analyze")
def analyze():
    symbol = request.args.get("symbol", "")
    if not symbol:
        return jsonify({"error": "종목코드(symbol)를 입력해주세요."}), 400
    try:
        df = get_ohlcv_kiwoom(symbol)
        result = analyze_ichimoku(df)
        return jsonify({
            "종목코드": symbol,
            "현재가": df["Close"].iloc[-1],
            "기술적_분석": result
        })
    except Exception as e:
        return jsonify({"error": f"서버 내부 오류: {str(e)}"}), 500

# ==================== 🐍 실행 ====================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
