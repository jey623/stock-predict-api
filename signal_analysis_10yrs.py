import pandas as pd
import FinanceDataReader as fdr
import ta
import numpy as np
from flask import Flask, request, jsonify

app = Flask(__name__)

krx = fdr.StockListing('KRX')

def get_code_by_name(name):
    row = krx[krx['Name'] == name]
    return row['Code'].values[0] if not row.empty else None

def get_name_by_code(code):
    row = krx[krx['Code'] == code]
    return row['Name'].values[0] if not row.empty else None

def analyze_stock(input_value):
    if input_value.isdigit():
        code = input_value
        name = get_name_by_code(code)
    else:
        name = input_value
        code = get_code_by_name(name)

    if not code:
        return {"error": "❌ 유효하지 않은 종목명 또는 코드입니다."}

    df = fdr.DataReader(code, start='2014-01-01')

    # 기술적 지표 계산
    df['CCI'] = ta.trend.CCIIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=9).cci()
    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
    adx = ta.trend.ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=17)
    df['DI+'] = adx.adx_pos()
    df['DI-'] = adx.adx_neg()
    df['ADX'] = adx.adx()

    # Envelope 하단선 및 5일 최저
    envelope_down = df['Close'].rolling(window=20).mean() * (1 - 0.12)
    df['EnvelopeDown'] = envelope_down
    df['LowestEnvelope'] = envelope_down.rolling(window=5).min()
    df['LowestClose5'] = df['Close'].rolling(window=5).min()

    # ✅ 신호 수식
    df['Signal_Triggered'] = (
        (df['CCI'] < -100) &
        (df['RSI'] < 30) &
        (df['DI-'] > 41) &
        ((df['DI-'] < df['ADX']) | (df['DI+'] < 5)) &
        (df['LowestEnvelope'] > df['LowestClose5'])
    )

    latest = df.iloc[-1]
    signal = bool(latest["Signal_Triggered"])
    current_price = float(latest["Close"])

    # 예측
    future_prices = {}
    change_rates = {}
    periods = [1, 5, 10, 20, 40, 60, 80]

    for p in periods:
        returns = []
        for i in df.index:
            future_date = i + pd.Timedelta(days=p)
            if future_date in df.index:
                buy = df.loc[i, "Close"]
                future = df.loc[future_date, "Close"]
                change = (future - buy) / buy * 100
                returns.append(change)
        if returns:
            avg_return = round(np.mean(returns), 2)
            predicted_price = round(current_price * (1 + avg_return / 100), 2)
            future_prices[f"{p}일"] = predicted_price
            change_rates[f"{p}일"] = avg_return

    # 신호 발생 날짜
    signal_dates = df[df["Signal_Triggered"]].index.strftime("%Y-%m-%d").tolist()

    return {
        "종목명": name,
        "종목코드": str(code),  # ✅ 여기 str 변환 추가
        "현재가": round(current_price, 2),
        "예측가": future_prices,
        "변화율": change_rates,
        "신호발생": signal,
        "신호발생일자": signal_dates
    }

@app.route('/')
def index():
    return '📈 Signal Analysis API is running.'

@app.route('/analyze', methods=['GET'])
def analyze():
    symbol = request.args.get('symbol', '삼성전자')
    result = analyze_stock(symbol)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
