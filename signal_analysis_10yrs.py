# signal_analysis_10yrs.py
from datetime import timedelta
import numpy as np
import pandas as pd
import FinanceDataReader as fdr
from ta.momentum import RSIIndicator
from ta.trend    import CCIIndicator, ADXIndicator
from flask import Flask, request, jsonify

app = Flask(__name__)

# ────────────────────────────────
# ① 종목명 ↔ 종목코드 매핑 함수
# ────────────────────────────────
_krx = fdr.StockListing('KRX')        # KRX 전체 상장리스트 캐싱

def name_to_code(name: str) -> str | None:
    row = _krx[_krx['Name'] == name]
    return None if row.empty else str(row['Code'].iloc[0])

def code_to_name(code: str) -> str | None:
    row = _krx[_krx['Code'] == code]
    return None if row.empty else str(row['Name'].iloc[0])

# ────────────────────────────────
# ② 핵심 분석 로직
# ────────────────────────────────
def analyze_stock(symbol: str) -> dict:
    # ▸ 심볼 식별
    if symbol.isdigit():
        code  = symbol
        name  = code_to_name(code) or symbol
    else:
        name  = symbol
        code  = name_to_code(name)
    if not code:
        return {"error": "❌ 유효하지 않은 종목명 또는 코드입니다."}

    # ▸ 데이터 수집 (10 년치, FDR → NAVER 우선)
    try:
        df = fdr.DataReader(code, start='2014-01-01')   # ex) 086520
    except Exception:                                    # FDR 예외 시 Yahoo-KRX fallback
        df = fdr.DataReader(code, exchange='KRX', start='2014-01-01')
    if df.empty:
        return {"error": "❌ 가격 데이터를 찾을 수 없습니다."}

    # ── 기술적 지표 ───────────────────────────────────────────
    df['CCI'] = CCIIndicator(df['High'], df['Low'], df['Close'], window=9).cci()
    df['RSI'] = RSIIndicator(df['Close'], window=14).rsi()

    adx_obj   = ADXIndicator(df['High'], df['Low'], df['Close'], window=17)
    df['DI+'] = adx_obj.adx_pos()
    df['DI-'] = adx_obj.adx_neg()
    df['ADX'] = adx_obj.adx()

    # Envelope 하단선 = MA20 * (1-0.12)
    df['MA20']          = df['Close'].rolling(20).mean()
    df['EnvelopeDown']  = df['MA20'] * 0.88
    df['LowestEnv5']    = df['EnvelopeDown'].rolling(5).min()
    df['LowestClose5']  = df['Close'].rolling(5).min()

    # ── 신호 수식 ────────────────────────────────────────────
    HIGH_TOP   = 41
    LOW_BOTTOM = 5
    df['Signal'] = (
        (df['CCI'] < -100) &
        (df['RSI'] < 30) &
        (df['DI-'] > HIGH_TOP) &
        ((df['DI-'] < df['ADX']) | (df['DI+'] < LOW_BOTTOM)) &
        (df['LowestEnv5'] > df['LowestClose5'])
    )

    # ── 신호발생일자 & 현재 신호 ─────────────────────────────
    signal_dates = df.loc[df['Signal']].index.strftime('%Y-%m-%d').tolist()
    signal_now   = bool(df['Signal'].iloc[-1])

    # ── 간단 예측(평균 수익률 기반) ───────────────────────────
    current_price = float(df['Close'].iloc[-1])
    horizons      = [1, 5, 10, 20, 40, 60, 80]
    pred_prices, changes = {}, {}

    for h in horizons:
        future = df['Close'].shift(-h)                       # h일 뒤의 종가
        pct    = ((future / df['Close']) - 1) * 100          # 변화율 %
        mean_r = pct.mean(skipna=True)
        if not np.isnan(mean_r):
            pred_prices[f"{h}일"] = round(current_price * (1 + mean_r / 100), 2)
            changes[f"{h}일"]     = round(mean_r, 2)

    # ── 최종 JSON 출력 ───────────────────────────────────────
    return {
        "종목명"      : name,
        "종목코드"    : code,
        "현재가"      : round(current_price, 2),
        "예측가"      : pred_prices,
        "변화율"      : changes,
        "신호발생"    : signal_now,
        "신호발생일자": signal_dates
    }

# ────────────────────────────────
# ③ Flask 엔드포인트
# ────────────────────────────────
@app.route('/')
def root():
    return '📈 Signal Analysis API is running.'

@app.route('/analyze', methods=['GET'])
def analyze():
    symbol = request.args.get('symbol', '').strip()
    if not symbol:
        return jsonify({"error": "symbol 파라미터가 필요합니다."}), 400
    result = analyze_stock(symbol)
    status = 200 if 'error' not in result else 400
    return jsonify(result), status

# ────────────────────────────────
if __name__ == '__main__':
    # Render 같은 환경에선 gunicorn으로 실행되므로
    # 로컬 테스트할 때만 직접 띄우면 됩니다.
    app.run(host='0.0.0.0', port=10000, debug=True)

