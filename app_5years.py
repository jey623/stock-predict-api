from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import ta

app = Flask(__name__)

# 종목명 ↔ 종목코드 매핑 딕셔너리 생성 (캐시)
stock_dict = fdr.StockListing('KRX')[['Code', 'Name']].set_index('Name')['Code'].to_dict()
code_dict = {v: k for k, v in stock_dict.items()}

def get_stock_code(stock):
    if stock.isdigit():
        return stock, code_dict.get(stock, "Unknown")
    else:
        return stock_dict.get(stock, "Unknown"), stock

@app.route('/get_indicators', methods=['GET'])
def get_indicators():
    stock = request.args.get('stock')
    if not stock:
        return jsonify({'error': 'Missing stock name or code'}), 400

    code, name = get_stock_code(stock)
    if code == "Unknown":
        return jsonify({'error': 'Invalid stock name or code'}), 400

    try:
        df = fdr.DataReader(code, start='2020-01-01')
        df = df.dropna()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA40'] = df['Close'].rolling(window=40).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['RSI'] = ta.momentum.RSIIndicator(df['Close']).rsi()
        macd = ta.trend.MACD(df['Close'])
        df['MACD'] = macd.macd()
        df['Signal'] = macd.macd_signal()
        df.dropna(inplace=True)
        latest = df.iloc[-1]

        return jsonify({
            '종목명': name,
            '종목코드': code,
            '날짜': latest.name.strftime('%Y-%m-%d'),
            '현재가': int(latest['Close']),
            'MA20': round(latest['MA20'], 2),
            'MA40': round(latest['MA40'], 2),
            'MA60': round(latest['MA60'], 2),
            'RSI': round(latest['RSI'], 2),
            'MACD': round(latest['MACD'], 2),
            '신호선': round(latest['Signal'], 2)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)

