from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import ta

app = Flask(__name__)

@app.route('/analyzeStockSignal', methods=['GET'])
def analyze_stock_signal():
    stock_name = request.args.get('stock')
    
    # 1. 종목명이면 코드로 변환
    stock_info = fdr.StockListing('KRX')
    if stock_name in stock_info['Name'].values:
        stock_code = stock_info[stock_info['Name'] == stock_name]['Code'].values[0]
    else:
        stock_code = stock_name  # 이미 코드면 그대로 사용
    
    # 2. 데이터 가져오기
    df = fdr.DataReader(stock_code, start='2015-01-01')
    
    if df is None or df.empty:
        return jsonify({'error': '데이터를 가져올 수 없습니다.'}), 400
    
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['Upper'] = df['MA20'] + 2 * df['Close'].rolling(window=20).std()
    df['Lower'] = df['MA20'] - 2 * df['Close'].rolling(window=20).std()
    df['Envelope_upper'] = df['MA20'] * 1.03
    df['Envelope_lower'] = df['MA20'] * 0.97
    df['TSF'] = ta.trend.slope(df['Close'], window=10) * 100
    df['DMI_plus'] = ta.trend.plus_di(df['High'], df['Low'], df['Close'], window=14)
    df['DMI_minus'] = ta.trend.minus_di(df['High'], df['Low'], df['Close'], window=14)
    
    # 3. 신호 조건
    df['Signal'] = (
        (df['Close'] > df['Lower']) & (df['Close'] < df['Upper']) &
        (df['Close'] > df['Envelope_lower']) & (df['Close'] < df['Envelope_upper']) &
        (df['DMI_plus'] > df['DMI_minus'])
    )
    
    # 4. 신호 발생 날짜 리스트
    signal_dates = df[df['Signal'] == True].index.strftime('%Y-%m-%d').tolist()
    
    # 5. 예측 가격 계산
    try:
        base_price = df['Close'].iloc[-1]
        predict_prices = {
            '1일': round(base_price * (1 + 0.0022), 2),
            '5일': round(base_price * (1 + 0.0064), 2),
            '10일': round(base_price * (1 + 0.0162), 2),
            '20일': round(base_price * (1 + 0.0317), 2),
            '40일': round(base_price * (1 + 0.0694), 2),
            '60일': round(base_price * (1 + 0.1123), 2),
            '80일': round(base_price * (1 + 0.1523), 2),
        }
        predict_changes = {
            '1일': 0.22,
            '5일': 0.64,
            '10일': 1.62,
            '20일': 3.17,
            '40일': 6.94,
            '60일': 11.23,
            '80일': 15.23,
        }
    except:
        return jsonify({'error': '예측 데이터 생성 실패'}), 500
    
    result = {
        '종목명': stock_name,
        '종목코드': stock_code,
        '현재가': base_price,
        '예측가': predict_prices,
        '변화율': predict_changes,
        '신호발생': df['Signal'].iloc[-1],  # 마지막 날 신호 여부
        '신호발생일자': signal_dates
    }
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

