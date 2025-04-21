# app_5years.py (수정본)
from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import ta

app = Flask(__name__)

# 종목명/코드 자동 인식
def get_stock_code(name_or_code):
    stock_list = fdr.StockListing('KRX')
    match = stock_list[(stock_list['Name'] == name_or_code) | (stock_list['Code'] == name_or_code)]
    if not match.empty:
        return match.iloc[0]['Code'], match.iloc[0]['Name']
    return None, None

@app.route('/get_indicators', methods=['GET'])
def get_indicators():
    stock = request.args.get('stock')
    if not stock:
        return jsonify({'error': 'Missing stock parameter'}), 400

    code, name = get_stock_code(stock)
    if not code:
        return jsonify({'error': 'Invalid stock name or code'}), 400

    try:
        df = fdr.DataReader(code, start='2020-01-01')
        df = df.dropna()

        # 기술적 지표
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA40'] = df['Close'].rolling(40).mean()
        df['MA60'] = df['Close'].rolling(60).mean()
        df['RSI'] = ta.momentum.RSIIndicator(df['Close']).rsi()
        macd = ta.trend.MACD(df['Close'])
        df['MACD'] = macd.macd()
        df['Signal'] = macd.macd_signal()
        bb = ta.volatility.BollingerBands(df['Close'])
        df['BB_High'] = bb.bollinger_hband()
        df['BB_Low'] = bb.bollinger_lband()
        df['TSF'] = ta.trend.EMAIndicator(df['Close'], window=14).ema_indicator()
        adx = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'])
        df['ADX'] = adx.adx()
        df['+DI'] = adx.adx_pos()
        df['-DI'] = adx.adx_neg()
        df['Envelope_Upper'] = df['MA20'] * 1.03
        df['Envelope_Lower'] = df['MA20'] * 0.97

        latest = df.iloc[-1]

        return jsonify({
            '종목명': name,
            '종목코드': code,
            '날짜': latest.name.strftime('%Y-%m-%d'),
            '현재가': round(latest['Close']),
            'MA20': round(latest['MA20'], 2),
            'MA40': round(latest['MA40'], 2),
            'MA60': round(latest['MA60'], 2),
            'RSI': round(latest['RSI'], 2),
            'MACD': round(latest['MACD'], 2),
            '신호선': round(latest['Signal'], 2),
            'BB_High': round(latest['BB_High'], 2),
            'BB_Low': round(latest['BB_Low'], 2),
            'TSF': round(latest['TSF'], 2),
            'ADX': round(latest['ADX'], 2),
            '+DI': round(latest['+DI'], 2),
            '-DI': round(latest['-DI'], 2),
            'Envelope_Upper': round(latest['Envelope_Upper'], 2),
            'Envelope_Lower': round(latest['Envelope_Lower'], 2)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

