import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from ta.momentum import RSIIndicator
from ta.trend import CCIIndicator, ADXIndicator
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/analyzeStockSignal', methods=['GET'])
def analyze_stock_signal():
    stock = request.args.get('stock')

    df = fdr.DataReader(stock, start='2015-01-01')
    df = df.dropna()

    # 기술적 지표 계산
    df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
    df['CCI'] = CCIIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=9).cci()
    adx = ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=17)
    df['DI+'] = adx.adx_pos()
    df['DI-'] = adx.adx_neg()
    df['ADX'] = adx.adx()

    # Envelope 기준선
    ma20 = df['Close'].rolling(window=20).mean()
    envelope_down = ma20 * (1 - 0.12)
    df['EnvelopeLow'] = envelope_down
    df['Lowest_Env'] = envelope_down.rolling(window=5).min()
    df['Lowest_C'] = df['Close'].rolling(window=5).min()

    # 사용자 신호 수식
    df['Signal'] = (
        (df['CCI'] < -100) &
        (df['RSI'] < 30) &
        (df['DI-'] > 41) &
        ((df['DI-'] < df['ADX']) | (df['DI+'] < 5)) &
        (df['Lowest_Env'] > df['Lowest_C'])
    )

    # 예측가 및 변화율 계산
    current_price = df['Close'].iloc[-1]
    predict_factors = {
        "1일": 1.0022, "5일": 1.0064, "10일": 1.0162,
        "20일": 1.0317, "40일": 1.0694, "60일": 1.1123, "80일": 1.1523
    }

    predicted_prices = {
        day: round(current_price * factor, 1) for day, factor in predict_factors.items()
    }

    predicted_changes = {
        day: round((price - current_price) / current_price * 100, 2)
        for day, price in predicted_prices.items()
    }

    # 신호발생일자 추출
    df['Date'] = df.index
    signal_dates = df[df['Signal']]['Date'].dt.strftime('%Y-%m-%d').tolist()
    is_signal_now = bool(df['Signal'].iloc[-1])

    return jsonify({
        "종목명": stock,
        "종목코드": df.columns.name or "",
        "현재가": round(current_price, 1),
        "신호발생": is_signal_now,
        "신호발생일자": signal_dates,
        "예측가": predicted_prices,
        "변화율": predicted_changes
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

