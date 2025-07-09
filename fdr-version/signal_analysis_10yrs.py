from flask import Flask, request, jsonify
import FinanceDataReader as fdr
from prophet import Prophet
import pandas as pd
import datetime
import os

app = Flask(__name__)

def resolve_symbol(symbol_or_name):
    if symbol_or_name.isdigit():
        return symbol_or_name, symbol_or_name
    try:
        stock_list = fdr.StockListing('KRX')
        matched = stock_list[stock_list['Name'] == symbol_or_name]
        if not matched.empty:
            code = matched.iloc[0]['Code']
            name = matched.iloc[0]['Name']
            return code, name
    except Exception:
        pass
    return None, None

@app.route('/predict', methods=['GET'])
def predict():
    symbol_input = request.args.get('symbol')
    period = int(request.args.get('period', 5))
    period = max(1, min(period, 10))
    days = 10

    if not symbol_input:
        return jsonify({'error': 'symbol 파라미터가 필요합니다'}), 400

    resolved_code, resolved_name = resolve_symbol(symbol_input)
    if not resolved_code:
        return jsonify({'error': f'"{symbol_input}"에 해당하는 종목코드를 찾을 수 없습니다.'}), 400

    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=365 * period)

    try:
        df = fdr.DataReader(resolved_code, start, end)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    if df.empty:
        return jsonify({'error': '데이터가 없습니다'}), 404

    # Prophet 데이터 준비
    data = df.reset_index()[['Date', 'Close']].rename(columns={'Date': 'ds', 'Close': 'y'})

    # Prophet 모델 생성 및 학습
    model = Prophet(daily_seasonality=True, yearly_seasonality=True)
    model.fit(data)

    # 10거래일 예측 (평일만)
    future = model.make_future_dataframe(periods=days, freq='B')
    forecast = model.predict(future)
    preds = forecast[['ds', 'yhat']].tail(days)

    preds = [
        {'날짜': row['ds'].strftime('%Y-%m-%d'), '예측종가': round(float(row['yhat']), 2)}
        for _, row in preds.iterrows()
    ]

    latest_close = float(df['Close'].iloc[-1])

    return jsonify({
        '종목명': resolved_name,
        '종목코드': resolved_code,
        '현재가': round(latest_close, 2),
        '예측종가_10일': preds
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))

