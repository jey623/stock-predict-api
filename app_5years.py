from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
import ta

app = Flask(__name__)

# 종목명-코드 매핑
stock_list = fdr.StockListing('KRX')
code_name_map = dict(zip(stock_list['Code'], stock_list['Name']))
name_code_map = dict(zip(stock_list['Name'], stock_list['Code']))

@app.route('/get_indicators', methods=['GET'])
def get_indicators():
    stock_input = request.args.get('stock')
    if not stock_input:
        return jsonify({'error': 'Missing stock name or code'}), 400

    # 종목명 또는 종목코드 처리
    if stock_input in code_name_map:
        stock_name = code_name_map[stock_input]
        code = stock_input
    elif stock_input in name_code_map:
        code = name_code_map[stock_input]
        stock_name = stock_input
    else:
        return jsonify({'error': '종목명을 정확히 입력해주세요'}), 400

    # 5년치 일봉 데이터 수집
    try:
        df = fdr.DataReader(code, start='2020-01-01')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    df = df.dropna()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA40'] = df['Close'].rolling(window=40).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
    macd = ta.trend.MACD(close=df['Close'])
    df['MACD'] = macd.macd()
    df['신호선'] = macd.macd_signal()

    latest = df.iloc[-1]
    result = {
        '종목명': stock_name,
        '종목코드': code,
        '날짜': latest.name.strftime('%Y-%m-%d'),
        '현재가': int(latest['Close']),
        'MA20': round(latest['MA20'], 2),
        'MA40': round(latest['MA40'], 2),
        'MA60': round(latest['MA60'], 2),
        'RSI': round(latest['RSI'], 2),
        'MACD': round(latest['MACD'], 2),
        '신호선': round(latest['신호선'], 2)
    }
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

