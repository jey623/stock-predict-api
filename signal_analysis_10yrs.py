# ──────────────────────────────────────────────────────────────
#  signal_analysis_10yrs.py
# ──────────────────────────────────────────────────────────────
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from ta.momentum import RSIIndicator
from ta.trend    import CCIIndicator, ADXIndicator
from flask import Flask, request, jsonify

app = Flask(__name__)

# ── (1) 보조 지표 계산 ─────────────────────────────────────────
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df["CCI"] = CCIIndicator(high=df["High"], low=df["Low"],
                             close=df["Close"], window=9).cci()
    df["RSI"] = RSIIndicator(close=df["Close"], window=14).rsi()

    adx = ADXIndicator(high=df["High"], low=df["Low"],
                       close=df["Close"], window=17)
    df["DI+"] = adx.adx_pos()
    df["DI-"] = adx.adx_neg()
    df["ADX"] = adx.adx()

    env_dn = df["Close"].rolling(window=20).mean() * (1 - 0.12)
    df["EnvelopeDown"]  = env_dn
    df["LowestEnvelope"] = env_dn.rolling(window=5).min()
    df["LowestC"]        = df["Close"].rolling(window=5).min()
    return df


# ── (2) 신호 탐지 ─────────────────────────────────────────────
def attach_signal_column(df: pd.DataFrame,
                         high_top: float = 30,   # ← 완화된 값
                         low_bottom: float = 7   # ← 완화된 값
                         ) -> tuple[pd.DataFrame, bool, list[str], dict]:
    conds = {
        "cci":      df["CCI"] < -100,
        "rsi":      df["RSI"] < 30,
        "di_minus": df["DI-"] > high_top,
        "adx_mix":  (df["DI-"] < df["ADX"]) | (df["DI+"] < low_bottom),
        "env":      df["LowestEnvelope"] > df["LowestC"]
    }

    df["Signal"] = True
    for c in conds.values():
        df["Signal"] &= c

    # 디버그용 카운트
    debug_counts = {k: int(v.sum()) for k, v in conds.items()}

    signal_dates = df[df["Signal"]].index.strftime("%Y-%m-%d").tolist()
    latest_signal = bool(df["Signal"].iloc[-1])
    return df, latest_signal, signal_dates, debug_counts


# ── (3) API 엔드포인트 ───────────────────────────────────────
@app.route("/analyze", methods=["GET"])
def analyze():
    symbol = request.args.get("symbol", "").strip()
    if not symbol:
        return jsonify({"error": "쿼리 파라미터 symbol 이 필요합니다."}), 400

    try:
        # 10년치(2520 거래일) 데이터
        df = fdr.DataReader(symbol)[-2520:].copy()
        df = add_indicators(df)

        df, signal_now, signal_dates, dbg = attach_signal_column(df)

        current_price = float(df["Close"].iloc[-1])

        horizon = [1, 5, 10, 20, 40, 60, 80]
        predicted_prices, predicted_changes = {}, {}
        for d in horizon:
            future_price = round(current_price * (1 + 0.002 * d), 2)  # dummy model
            predicted_prices[f"{d}일"]  = future_price
            predicted_changes[f"{d}일"] = round((future_price - current_price)
                                                / current_price * 100, 2)

        result = {
            "종목명": symbol,
            "종목코드": symbol,   # 필요하면 코드 매핑 함수 넣으셔도 됩니다
            "현재가": current_price,
            "예측가": predicted_prices,
            "변화율": predicted_changes,
            "신호발생": signal_now,
            "신호발생일자": signal_dates,
            "디버그_조건건수": dbg     # ← 필요 없으면 삭제/주석
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def index():
    return "📈 Signal Analysis API is running."


if __name__ == "__main__":
    # Render 기준 포트는 10000, 로컬 테스트는 5000 등으로 지정
    app.run(host="0.0.0.0", port=10000, debug=True)

