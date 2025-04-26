# -*- coding: utf-8 -*-
import pandas as pd, numpy as np, FinanceDataReader as fdr
from ta.momentum import RSIIndicator
from ta.trend    import CCIIndicator, ADXIndicator
from flask       import Flask, request, jsonify

app = Flask(__name__)

# ──────────────────── 1) KRX 종목 테이블 한 번만 로드
krx = fdr.StockListing('KRX')[['Code', 'Name']]

def get_code_by_name(name: str) -> str | None:
    hit = krx.loc[krx['Name'] == name, 'Code']
    return hit.iloc[0] if not hit.empty else None

# ──────────────────── 2) 핵심 로직
def analyze_stock(symbol: str):
    # 이름이면 코드로 변환
    code = symbol if symbol.isdigit() else get_code_by_name(symbol)
    if code is None:
        return {"error": f"❌ '{symbol}'(은)는 KRX에서 찾을 수 없습니다."}

    # 10 년치 일봉
    df = fdr.DataReader(code, start='2014-01-01').copy()

    # ── 기술적 지표
    df['CCI'] = CCIIndicator(df['High'], df['Low'], df['Close'], 9).cci()
    df['RSI'] = RSIIndicator(df['Close'], 14).rsi()
    adx        = ADXIndicator(df['High'], df['Low'], df['Close'], 17)
    df['DI+']  = adx.adx_pos();  df['DI-'] = adx.adx_neg();  df['ADX'] = adx.adx()

    ma20           = df['Close'].rolling(20).mean()
    df['EnvDn']    = ma20 * (1 - 0.12)
    df['LowEnv5']  = df['EnvDn'].rolling(5).min()
    df['LowC5']    = df['Close'].rolling(5).min()

    # ── 신호 조건
    hi, lo = 30, 7                                    # 기본값
    df['Signal'] = (
        (df['CCI'] < -100) &
        (df['RSI'] < 30)  &
        (df['DI-'] > hi) &
        ((df['DI-'] < df['ADX']) | (df['DI+'] < lo)) &
        (df['LowEnv5'] > df['LowC5'])
    )

    # ── 결과 구성
    latest = df.iloc[-1]
    periods = [1,5,10,20,40,60,80]
    pred    = {f"{p}일": round(latest['Close']*(1+0.002*p),2) for p in periods}
    change  = {k: round((v-latest['Close'])/latest['Close']*100,2) for k,v in pred.items()}

    return {
        "종목명": krx.loc[krx['Code']==code,'Name'].iat[0],
        "종목코드": code,
        "현재가": round(float(latest['Close']),2),
        "예측가": pred,
        "변화율": change,
        "신호발생": bool(latest['Signal']),
        "신호발생일자": df[df['Signal']].index.strftime('%Y-%m-%d').tolist()
    }

# ──────────────────── 3) Flask 엔드포인트
@app.route('/')
def home(): return '📈 Signal-Analysis API is running.'

@app.route('/analyze')
def api_analyze():
    symbol = request.args.get('symbol', '').strip()
    if not symbol:
        return jsonify({"error": "symbol 파라미터가 필요합니다."}), 400
    return jsonify(analyze_stock(symbol))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

