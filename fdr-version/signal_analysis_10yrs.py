from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import ta

app = Flask(__name__)

# 종목명 → 코드 자동 변환 함수
def name_to_code(name):
    kospi = fdr.StockListing('KOSPI')
    kosdaq = fdr.StockListing('KOSDAQ')
    all_stocks = pd.concat([kospi, kosdaq])
    match = all_stocks[all_stocks['Name'] == name]
    if not match.empty:
        return match.iloc[0]['Code']
    return None

# 기술적 지표 추가 함수
def add_tech_indicators(df):
    df['ma5'] = df['Close'].rolling(window=5).mean()
    df['ma20'] = df['Close'].rolling(window=20).mean()
    df['ma60'] = df['Close'].rolling(window=60).mean()
    df['ma120'] = df['Close'].rolling(window=120).mean()
    df['disparity_5'] = df['Close'] / df['ma5'] * 100
    df['disparity_20'] = df['Close'] / df['ma20'] * 100
    df['disparity_60'] = df['Close'] / df['ma60'] * 100
    df['disparity_120'] = df['Close'] / df['ma120'] * 100
    df['rsi'] = ta.momentum.rsi(df['Close'], window=14)
    df['cci'] = ta.trend.cci(df['High'], df['Low'], df['Close'], window=20)
    df['obv'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
    return df

@app.route('/getdata', methods=['GET'])
def getdata():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({'error': 'symbol 파라미터가 필요합니다'}), 400

    # 종목명이면 코드로 변환
    if not symbol.isdigit():
        converted = name_to_code(symbol)
        if converted:
            symbol = converted
        else:
            return jsonify({'error': f'종목명을 찾을 수 없습니다: {symbol}'}), 400

    try:
        # 1년치 데이터 불러오기
        end = pd.Timestamp.today()
        start = end - pd.DateOffset(years=1)
        df = fdr.DataReader(symbol, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        df = df.dropna()
        df = add_tech_indicators(df)
        df = df.fillna(0)
        data = df.reset_index().to_dict(orient='records')
        return jsonify({
            'symbol': symbol,
            'count': len(data),
            'data': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


