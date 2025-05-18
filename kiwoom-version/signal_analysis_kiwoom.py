from datetime import datetime, timedelta
import os, time, requests
import pandas as pd
import ta
from flask import Flask, request, jsonify

app = Flask(__name__)

# 🔐 환경변수에서 키 불러오기
def load_keys():
    app_key = os.getenv("APP_KEY")
    app_secret = os.getenv("APP_SECRET")
    if not app_key or not app_secret:
        raise Exception("❌ 환경변수 APP_KEY 또는 APP_SECRET이 설정되지 않았습니다.")
    return app_key, app_secret

APP_KEY, APP_SECRET = load_keys()
ACCESS_TOKEN = None

# 🔁 토큰 발급
def get_access_token():
    global ACCESS_TOKEN
    if ACCESS_TOKEN:
        return ACCESS_TOKEN
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    headers = {"Content-Type": "application/json"}
    data = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    res = requests.post(url, headers=headers, json=data)
    if res.status_code == 200:
        ACCESS_TOKEN = res.json().get("access_token")
        return ACCESS_TOKEN
    raise Exception(f"❌ 토큰 발급 실패: {res.status_code} {res.text}")

# 📊 일봉 데이터 조회
def get_ohlcv_kiwoom(code, start_date="20140101"):
    token = get_access_token()
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010100",
        "custtype": "P"
    }

    df_all = pd.DataFrame()
    current_date = datetime.now().strftime('%Y%m%d')

    for _ in range(100):
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": code,
            "fid_input_date_1": start_date,
            "fid_input_date_2": current_date,
            "fid_org_adj_prc": "0"
        }
        res = requests.get(url, headers=headers, params=params)
        if res.status_code != 200: break
        output = res.json().get("output", [])
        if not output: break

        df = pd.DataFrame(output)
        df = df.rename(columns={
            "stck_bsop_date": "Date",
            "stck_clpr": "Close",
            "stck_hgpr": "High",
            "stck_lwpr": "Low",
            "acml_vol": "Volume"
        })
        df["Date"] = pd.to_datetime(df["Date"])
        df = df[["Date", "High", "Low", "Close", "Volume"]].apply(pd.to_numeric, errors="coerce")
        df_all = pd.concat([df_all, df])
        current_date = (df["Date"].min() - timedelta(days=1)).strftime('%Y%m%d')
        time.sleep(1)

    df_all.dropna(inplace=True)
    df_all.set_index("Date", inplace=True)
    return df_all.sort_index()

# 📘 전자책 + 일목균형표 분석
def analyze_e_book_signals(df):
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

    def label(val):
        if val < 92: return f"과매도({val:.1f}%)"
        elif val > 102: return f"과매수({val:.1f}%)"
        return f"중립({val:.1f}%)"

    result["이격도_20일"] = label(d20)
    result["이격도_60일"] = label(d60)

    obv = ta.volume.OnBalanceVolumeIndicator(df["Close"], df["Volume"]).on_balance_volume()
    obv_trend = obv.rolling(5).mean().iloc[-1] - obv.rolling(5).mean().iloc[-2]
    price_trend = df["Close"].iloc[-1] - df["Close"].iloc[-2]

    if obv_trend > 0 and price_trend < 0:
        result["OBV_분석"] = "OBV 유지, 주가 하락 → 매집 가능성"
    elif obv_trend < 0 and price_trend > 0:
        result["OBV_분석"] = "OBV 하락, 주가 상승 → 분산 가능성"
    else:
        result["OBV_분석"] = "OBV와 주가 방향 일치"

    df["전환선"] = (df["High"].rolling(9).max() + df["Low"].rolling(9).min()) / 2
    df["기준선"] = (df["High"].rolling(26).max() + df["Low"].rolling(26).min()) / 2
    df["선행스팬1"] = ((df["전환선"] + df["기준선"]) / 2).shift(26)
    df["선행스팬2"] = ((df["High"].rolling(52).max() + df["Low"].rolling(52).min()) / 2).shift(26)
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

# 🔍 종목 분석
def analyze_stock(symbol):
    df = get_ohlcv_kiwoom(symbol)
    if df.empty:
        return {"error": "❌ 데이터 없음 또는 종목코드 오류"}

    cur = df["Close"].iloc[-1]
    future, change = {}, {}
    for d in [1, 5, 10, 20, 40, 60, 80]:
        pred = round(cur * (1 + 0.002 * d), 2)
        future[f"{d}일"] = pred
        change[f"{d}일"] = round((pred - cur) / cur * 100, 2)

    return {
        "종목코드": symbol,
        "현재가": float(cur),
        "예측가": future,
        "변화율": change,
        "기술적_분석": analyze_e_book_signals(df)
    }

# 🌐 라우터
@app.route("/")
def index():
    return "📈 Kiwoom REST API + Ichimoku Analysis API is running."

@app.route("/analyze")
def api_analyze():
    symbol = request.args.get("symbol", "")
    if not symbol:
        return jsonify({"error": "symbol 파라미터가 필요합니다"}), 400
    return jsonify(analyze_stock(symbol))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)



