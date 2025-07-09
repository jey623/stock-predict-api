from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
from prophet import Prophet
import datetime

app = Flask(__name__)

def get_code(symbol):
    # 숫자로만 되어 있으면 그대로(코드), 아니면 한글→코드 매핑
    if symbol.isdigit():
        return symbol
    try:
        stock_list = fdr.StockListing('KRX')
        code = stock_list.loc[stock_list['Name'] == symbol, 'Code']
        if len(code) == 0:
            return None
        return code.values[0]
    except Exception as e:
        return None

@app.route('/')
def index():
    return "OK"

@app.route('/predict', methods=['GET'])
def predict():
    symbol = request.args.get('symbol')
    period = int(request.args.get('period', 10))
    code = get_code(symbol)

    if code is None:
        return jsonify({'error': '종목 코드를 찾을 수 없습니다.'}), 400

    # 10년치 데이터 가져오기
    end = datetime.datetime.today()
    start = end - pd.DateOffset(years=10)
    df = fdr.DataReader(code, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))

    if df is None or len(df) < 100:
        return jsonify({'error': '종목 데이터를 불러오지 못했습니다.'}), 404

    # Prophet 입력 포맷 변환
    df = df.reset_index()
    df = df[['Date', 'Close']].rename(columns={'Date': 'ds', 'Close': 'y'})

    # 최신 실제 종가, 종목명
    latest_price = float(df['y'].iloc[-1])
    stock_name = code
    try:
        stock_list = fdr.StockListing('KRX')
        name_row = stock_list.loc[stock_list['Code'] == code, 'Name']
        if len(name_row) > 0:
            stock_name = name_row.values[0]
    except:
        pass

    # Prophet 예측
    model = Prophet(daily_seasonality=True)
    model.fit(df)

    future = model.make_future_dataframe(periods=period)
    forecast = model.predict(future)

    pred = []
    for i in range(-period, 0):
        row = forecast.iloc[i]
        pred.append({
            "날짜": str(row['ds'].date()),
            "예측종가": round(float(row['yhat']), 2)
        })

    result = {
        "예측종가_10일": pred,
        "종목명": stock_name,
        "종목코드": code,
        "최신일자_실제종가": latest_price
    }
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)


