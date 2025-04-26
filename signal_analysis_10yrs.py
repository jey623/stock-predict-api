# signal_analysis_10yrs.py
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from ta.momentum import RSIIndicator
from ta.trend    import CCIIndicator, ADXIndicator
from flask       import Flask, request, jsonify

app = Flask(__name__)

# ── KRX 종목명 ↔ 종목코드 매핑 ────────────────────────────────
krx = fdr.StockListing('KRX')

def get_code_by_name(name: str) -> str | None:
    row = krx[krx['Name'] == name]
    return row['Code'].values[0] if not row.empty else None

def get_name_by_code(code: str) -> str | None:
    row = krx[krx['Code'] == code]
    return row['Name'].values[0] if not row.empty else None

# ── 기술적 지표 계산 ────────────────────────────────────────
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df['CCI'] = CCIIndicator(high=df['High'], low=df['Low'],
                             close=df['Close'], window=9).cci()
    df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()

    adx = ADXIndicator(high=df['High'], low=df['Low'],
                       close=df['Close'], window=17)
    df['DI+'] = adx.adx_pos()
    df['DI-'] = adx.adx_neg()
    df['ADX'] = adx.adx()

    # Envelope-(20, 12 %) ↓ 및 5일 최저값
    env_down = df['Close'].rolling(window=20).mean() * (1 - 0.12)
    df['EnvDown']  = env_down
    df['LowEnv5']  = env_down.rolling(window=5).min()
    df['LowC5']    = df['Close'].rolling(window=5).min()
    return df

# ── 신호 탐지 ───────────────────────────────────────────────
def detect_signals(df: pd.DataFrame, hi: int = 41, lo: int = 5):
    signal = (
        (df['CCI'] < -100) &
        (df['RSI'] < 30)   &
        (df['DI-'] > hi)   &
        ((df['DI-'] < df['ADX']) | (df['DI+'] < lo)) &
        (df['LowEnv5'] > df['LowC5'])
    )
    df['Signal'] = signal
    dates  = df[signal].index.strftime('%Y-%m-%d').tolist()
    latest = bool(signal.iloc[-1]) if len(signal) else False
    return latest, dates

# ── 메인 분석 함수 ──────────────────────────────────────────
def analyze_stock(query: str, hi: int, lo: int):
    # 종목코드/이름 자동 인식
    if query.isdigit():
        code = query
        name = get_name_by_code(code) or query
    else:
        name = query
        code = get_code_by_name(name) or query

    # 10년치 데이터
    df = fdr.DataReader(code, start='2014-01-01')
    df = add_indicators(df)
    is_signal_now, signal_dates = detect_signals(df, hi, lo)

    current_price = float(df['Close'].iloc[-1])

    # 단순 예측(예시: 고정 배수)
    factors = {1:1.002, 5:1.01, 10:1.02, 20:1.04, 40:1.08, 60:1.12, 80:1.16}
    pred, diff = {}, {}
    for d, f in factors.items():
        price = round(current_price * f, 2)
        pred[f'{d}일']  = price
        diff[f'{d}일']  = round((price - current_price) / current_price * 100, 2)

    return {
        '종목명'     : name,
        '종목코드'   : code,
        '현재가'     : current_price,
        '예측가'     : pred,
        '변화율'     : diff,
        '신호발생'   : is_signal_now,
        '신호발생일자': signal_dates
    }

# ── Flask 엔드포인트 ───────────────────────────────────────
@app.route('/')
def home():
    return '📈 Signal Analysis API is running.'

@app.route('/analyze', methods=['GET'])
def analyze():
    symbol = request.args.get('symbol', '삼성전자')
    hi     = request.args.get('hi', 41, type=int)
    lo     = request.args.get('lo', 5,  type=int)

    try:
        result = analyze_stock(symbol, hi, lo)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

