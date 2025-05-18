# ==================== signal_analysis_kiwoom.py ====================
import os
import json
import requests
from datetime import datetime
import pandas as pd
import ta
from flask import Flask, request, jsonify

# ==================== API KEY LOAD ====================
def load_keys():
    appkey = os.getenv("APP_KEY", "").strip()
    appsecret = os.getenv("APP_SECRET", "").strip()
    if not appkey or not appsecret:
        raise Exception("\u274c \ud658\uacbd\ubcc0\uc218 APP_KEY \ub610\ub294 APP_SECRET\uc774 \uc124\uc815\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.")
    return appkey, appsecret

# ==================== GET ACCESS TOKEN ====================
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
        raise Exception(f"\u274c \ud1a0\ud070 \ubc1c\uae09 \uc2e4\ud328: {response.status_code} {response.text}")
    return response.json()["access_token"]

# ==================== GET OHLCV FROM KIWOOOM ====================
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
        raise Exception(f"\u274c \uc77c\ubd09 \uc870\ud68c \uc2e4\ud328: {response.status_code} {response.text}")

    items = response.json().get("output2", [])
    if not items:
        raise Exception("\u274c \ub370\uc774\ud130\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.")

    df = pd.DataFrame(items)
    df["\ub0a0\uc9dc"] = pd.to_datetime(df["stck_bsop_date"])
    df.set_index("\ub0a0\uc9dc", inplace=True)
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

# ==================== TECHNICAL ANALYSIS ====================
def analyze_ichimoku(df):
    result = {}
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()
    result["\uc9c0\uc9c0\uc120"] = round(df["Close"].rolling(20).min().iloc[-1], 2)
    result["\uc800\ud76c\uc120"] = round(df["Close"].rolling(20).max().iloc[-1], 2)

    golden = (df["MA20"] > df["MA60"]) & (df["MA20"].shift() <= df["MA60"].shift())
    dead = (df["MA20"] < df["MA60"]) & (df["MA20"].shift() >= df["MA60"].shift())
    result["\uace8\ub4dc\ud06c\ub85c\uc2a4"] = bool(golden.iloc[-1])
    result["\ub370\ub4dc\ud06c\ub85c\uc2a4"] = bool(dead.iloc[-1])

    d20 = (df["Close"] / df["MA20"] * 100).iloc[-1]
    d60 = (df["Close"] / df["MA60"] * 100).iloc[-1]

    def classify_disparity(val):
        if val < 92:
            return f"\uac00\ub9e4\ub3c4({val:.1f}%)"
        elif val > 102:
            return f"\uac00\ub9e4\uc218({val:.1f}%)"
        else:
            return f"\uc911\ub9bd({val:.1f}%)"

    result["\uc774\uaca9\ub3c4_20\uc77c"] = classify_disparity(d20)
    result["\uc774\uaca9\ub3c4_60\uc77c"] = classify_disparity(d60)

    obv = ta.volume.OnBalanceVolumeIndicator(df["Close"], df["Volume"]).on_balance_volume()
    obv_trend = obv.rolling(5).mean().iloc[-1] - obv.rolling(5).mean().iloc[-2]
    price_trend = df["Close"].iloc[-1] - df["Close"].iloc[-2]

    if obv_trend > 0 and price_trend < 0:
        result["OBV_\ubd84\uc11d"] = "OBV \uc720\uc9c0, \uc8fc\uac00 \ud558\ub791 \u2192 \ub9e4\uc9d1 \uac00\ub2a5\uc131"
    elif obv_trend < 0 and price_trend > 0:
        result["OBV_\ubd84\uc11d"] = "OBV \ud558\ub791, \uc8fc\uac00 \uc0c1\uc2b9 \u2192 \ubd84\uc0b0 \uac00\ub2a5\uc131"
    else:
        result["OBV_\ubd84\uc11d"] = "OBV\uc640 \uc8fc\uac00 \ubc29\ud5a5 \uc77c\uce58"

    # Ichimoku
    df["\uc804\ud658\uc120"] = (df["High"].rolling(9).max() + df["Low"].rolling(9).min()) / 2
    df["\uae30\uc900\uc120"] = (df["High"].rolling(26).max() + df["Low"].rolling(26).min()) / 2
    df["\uc120\ud68d\uc2a4\ud3101"] = ((df["\uc804\ud658\uc120"] + df["\uae30\uc900\uc120"]) / 2).shift(26)
    df["\uc120\ud68d\uc2a4\ud3102"] = ((df["High"].rolling(52).max() + df["Low"].rolling(52).min()) / 2).shift(26)
    df["\uad6c\ub984\ud558\ub2e8"] = df[["\uc120\ud68d\uc2a4\ud3101", "\uc120\ud68d\uc2a4\ud3102"]].min(axis=1)
    df["\uc804\uae30\ucc28\uc774"] = abs(df["\uc804\ud658\uc120"] - df["\uae30\uc900\uc120"])

    result["\uc77c\ubaa9_\ucd5c\uc800\uc810"] = bool((df["Close"].iloc[-1] < df["\uad6c\ub984\ud558\ub2e8"].iloc[-1]) and (df["\uc804\uae30\ucc28\uc774"].iloc[-1] < 0.1))
    result["\uc77c\ubaa9_\uace8\ub4dc\ud06c\ub85c\uc2a4"] = bool((df["\uc804\ud658\uc120"].iloc[-1] > df["\uae30\uc900\uc120"].iloc[-1]) and (df["\uc804\ud658\uc120"].iloc[-2] <= df["\uae30\uc900\uc120"].iloc[-2]))

    if result["\uc77c\ubaa9_\ucd5c\uc800\uc810"]:
        result["\uc77c\ubaa9_\ud574\uc11d"] = "\uc804\ud658\uc120\uacfc \uae30\uc900\uc120\uc774 \ud3c9\ud569\ud558\uace0 \uad6c\ub984\ub300 \uc544\ub798 \uc704\uce58 \u2192 \ubcbd\ub2e4 \uc2dc\uadf8\ub110 \uac00\ub2a5"
    elif result["\uc77c\ubaa9_\uace8\ub4dc\ud06c\ub85c\uc2a4"]:
        result["\uc77c\ubaa9_\ud574\uc11d"] = "\uc804\ud658\uc120\uc774 \uae30\uc900\uc120\uc744 \uc0c1\ud5a5 \ub3cc\ud30c \u2192 \uc0c1\uc2b9 \ucd94\uc138 \uc804\ud658 \uac00\ub2a5"
    else:
        result["\uc77c\ubaa9_\ud574\uc11d"] = "\uc77c\ubaa9\uad00\uc5ed \ud2b9\uc774\uc810 \uc5c6\uc74c"

    return result

# ==================== FLASK APP ====================

app = Flask(__name__)

@app.route("/")
def home():
    return "\ud83d\udcc8 Kiwoom Signal Analysis API is live."

@app.route("/analyze")
def analyze():
    symbol = request.args.get("symbol", "")
    if not symbol:
        return jsonify({"error": "\uc885\ub8cc\ucf54\ub4dc(symbol)\ub97c \uc785\ub825\ud574\uc8fc\uc138\uc694."}), 400
    try:
        df = get_ohlcv_kiwoom(symbol)
        result = analyze_ichimoku(df)
        return jsonify({
            "\uc885\ub8cc\ucf54\ub4dc": symbol,
            "\ud604\uc7ac\uac00": df["Close"].iloc[-1],
            "\uae30\uc220\uc801_\ubd84\uc11d": result
        })
    except Exception as e:
        return jsonify({"error": f"\uc11c\ubc84 \ub0b4\ubd80 \uc624\ub958: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

