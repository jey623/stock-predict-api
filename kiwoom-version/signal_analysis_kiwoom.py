import os
import requests
import pandas as pd
import ta
from flask import Flask, request, jsonify, Response
from datetime import datetime

app = Flask(__name__)

# ✅ AppKey, AppSecret 환경변수 불러오기
def load_keys():
    app_key = os.environ.get("APP_KEY", "").strip()
    app_secret = os.environ.get("APP_SECRET", "").strip()
    if not app_key or not app_secret:
        raise Exception("❌ 환경변수 APP_KEY 또는 APP_SECRET이 설정되지 않았습니다.")
    return app_key, app_secret

APP_KEY, APP_SECRET = load_keys()

# ✅ 토큰 발급 함수 (au10001)
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

# ✅ 주가 데이터 요청 함수 (ka10081)
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
    return r.json().get("output2", [])

# ✅ 기술적 분석 함수 (기존 유지)
def analyze_technical_indicators(df):
    result = {}

    df['Close'] = pd.to_numeric(df['stck_clpr'], errors='coerce')
    df['High'] = pd.to_numeric(df['stck_hgpr'], errors='coerce')
    df['Low'] = pd.to_numeric(df['stck_lwpr'], errors='coerce')
    df['Volume'] = pd.to_numeric(df['acml_vol'], errors='coerce')

    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()

    result['지지선'] = round(df['Close'].rolling(20).min().iloc[-1], 2)
    result['저항선'] = round(df['Close'].rolling(20).max().iloc[-1], 2)

    golden = (df['MA20'] > df['MA60']) & (df['MA20'].shift() <= df['MA60'].shift())
    dead = (df['MA20'] < df['MA60']) & (df['MA20'].shift() >= df['MA60'].shift())
    result['골든크로스'] = bool(golden.iloc[-1])
    result['데드크로스'] = bool(dead.iloc[-1])

    disparity_20 = (df['Close'] / df['MA20']) * 100
    disparity_60 = (df['Close'] / df['MA60']) * 100
    result['이격도_20일'] = classify_disparity(disparity_20.iloc[-1])
    result['이격도_60일'] = classify_disparity(disparity_60.iloc[-1])

    obv_indicator = ta.volume.OnBalanceVolumeIndicator(close=df['Close'], volume=df['Volume'])
    obv = obv_indicator.on_balance_volume()
    obv_trend = obv.rolling(5).mean().iloc[-1] - obv.rolling(5).mean().iloc[-2]
    price_trend = df['Close'].iloc[-1] - df['Close'].iloc[-2]

    if obv_trend > 0 and price_trend < 0:
        result['OBV_분석'] = "OBV 유지, 주가 하락 → 매집 가능성"
    elif obv_trend < 0 and price_trend > 0:
        result['OBV_분석'] = "OBV 하락, 주가 상승 → 분산 가능성"
    else:
        result['OBV_분석'] = "OBV와 주가 방향 일치"

    # ✅ 일목균형표 계산
    nine_high = df['High'].rolling(window=9).max()
    nine_low = df['Low'].rolling(window=9).min()
    df['전환선'] = (nine_high + nine_low) / 2

    twenty_six_high = df['High'].rolling(window=26).max()
    twenty_six_low = df['Low'].rolling(window=26).min()
    df['기준선'] = (twenty_six_high + twenty_six_low) / 2

    df['선행스팬1'] = ((df['전환선'] + df['기준선']) / 2).shift(26)
    fifty_two_high = df['High'].rolling(window=52).max()
    fifty_two_low = df['Low'].rolling(window=52).min()
    df['선행스팬2'] = ((fifty_two_high + fifty_two_low) / 2).shift(26)
    df['구름하단'] = df[['선행스팬1', '선행스팬2']].min(axis=1)
    df['전기차이'] = abs(df['전환선'] - df['기준선'])

    result['일목_최저점'] = bool((df['Close'].iloc[-1] < df['구름하단'].iloc[-1]) and (df['전기차이'].iloc[-1] < 0.1))
    result['일목_골든크로스'] = bool((df['전환선'].iloc[-1] > df['기준선'].iloc[-1]) and (df['전환선'].iloc[-2] <= df['기준선'].iloc[-2]))

    if result['일목_최저점']:
        result['일목_해석'] = "전환선과 기준선이 평행하고 구름대 아래 위치 → 바닥 시그널 가능"
    elif result['일목_골든크로스']:
        result['일목_해석'] = "전환선이 기준선을 상향 돌파 → 상승 추세 전환 가능"
    else:
        result['일목_해석'] = "일목균형표 기준 특이점 없음"

    return result

# ✅ 이격도 판단 함수
def classify_disparity(val):
    if val < 92:
        return f"과매도({val:.1f}%)"
    elif val > 102:
        return f"과매수({val:.1f}%)"
    else:
        return f"중립({val:.1f}%)"

# ✅ API 라우팅
@app.route("/")
def home():
    return Response("📈 Signal Analysis API (Kiwoom Ver) is running.", content_type="text/plain; charset=utf-8")

@app.route("/analyze")
def analyze():
    code = request.args.get("symbol", "")
    base_date = request.args.get("date", datetime.today().strftime("%Y%m%d"))
    if not code:
        return jsonify({"error": "❗ symbol 파라미터가 필요합니다."}), 400

    try:
        token = get_token()
        raw_data = request_chart_data(token, code, base_date)
        if not raw_data:
            return jsonify({"error": "❌ 데이터 수신 실패 또는 데이터 없음."}), 404
        df = pd.DataFrame(raw_data).iloc[::-1].reset_index(drop=True)
        result = analyze_technical_indicators(df)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"서버 내부 오류: {e}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
