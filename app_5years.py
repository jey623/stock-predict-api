from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
from ta.trend import MACD
from ta.momentum import RSIIndicator

app = Flask(__name__)

# 종목명-종목코드 매핑 테이블 로드
stock_table = fdr.StockListing('KRX')
code_name_map = dict(zip(stock_table['Name'], stock_table['Code']))
name_code_map = dict(zip(stock_table['Code'], stock_table['Name']))

@app.route('/get_indicators', methods=['GET'])
def get_indicators():
    stock_input = request.args.get('stock')

    if not stock_input:
        return jsonify({'error': 'stock 파라미터가 필요합니다'}), 400

    # 종목명 또는 코드로 인식
    if stock_input in code_name_map:
        stock_name = code_name_map[stock_input]
        code = stock_input
    elif stock_input in name_code_map:
        stock_name = stock_input
        code = name_code_map[stock_input]
    else:
        return jsonify({'error': '종목명을 정확히 입력해주세요'}), 400

    try:
        df = fdr.DataReader(code, start='2020-01-01')  # 5년치 데이터
        df.dropna(inplace=True)

        # 기술적 지표 계산
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA40'] = df['Close'].rolling(window=40).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        rsi = RSIIndicator(close=df['Close'], window=14)
        df['RSI'] = rsi.rsi()
        macd = MACD(close=df['Close'])
        df['MACD'] = macd.macd()
        df['Signal'] = macd.macd_signal()

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
            '신호선': round(latest['Signal'], 2)
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Render에서 외부 접속 가능하도록 설정
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)

