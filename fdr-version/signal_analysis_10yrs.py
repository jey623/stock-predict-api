from flask import Flask, request, jsonify
import pandas as pd
import FinanceDataReader as fdr
import ta
from xgboost import XGBRegressor
import datetime
import os

app = Flask(__name__)

def resolve_symbol(symbol_or_name):
    """종목명 또는 종목코드를 종목코드로 변환"""
    if symbol_or_name.isdigit():
        return symbol_or_name, symbol_or_name  # 코드 그대로 사용
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

def compute_technical_indicators(df):
    df = df.copy()
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
    df['CCI'] = ta.trend.CCIIndicator(df['High'], df['Low'], df['Close'], window=20).cci()
    df['OBV'] = ta.volume.OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()
    df['Disparity'] = df['Close'] / df['Close'].rolling(5).mean() * 100
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    df['MA120'] = df['Close'].rolling(120).mean()
    return df.dropna()

def predict_future(df_ti, days=5):
    df = df_ti.copy()
    df['Target'] = df['Close'].shift(-days)
    df = df.dropna()
    features = ['RSI','CCI','OBV','Disparity','MA5','MA20','MA60','MA120']
    X, y = df[features], df['Target']
    model = XGBRegressor(n_estimators=100, random_state=42, verbosity=0)
    model.fit(X, y)
    last_feat = df.iloc[-1:][features].copy()
    preds = []
    for _ in range(days):
        p = model.predict(last_feat)[0]
        preds.append(p)
        last_feat.iloc[0, 0] = p  # RSI에 임시 대입 (모형 입력 유지용)
    return preds

@app.route('/predict', methods=['GET'])
def predict():
    symbol_input = request.args.get('symbol')
    period = int(request.args.get('period', 5))
    period = max(1, min(period, 10))

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

    df_ti = compute_technical_indicators(df)
    preds = predict_future(df_ti, days=5)
    latest_indicators = df_ti.iloc[-1][['RSI','CCI','OBV','Disparity','MA5','MA20','MA60','MA120']].to_dict()
    latest_close = df['Close'].iloc[-1]

    # 예측 날짜
    dates = []
    last_date = df.index[-1]
    cnt = 1
    while len(dates) < 5:
        next_day = last_date + datetime.timedelta(days=cnt)
        if next_day.weekday() < 5:
            dates.append(next_day.strftime('%Y-%m-%d'))
        cnt += 1

    return jsonify({
        '종목명': resolved_name,
        '종목코드': resolved_code,
        '기간_년': period,
        '현재가': round(float(latest_close), 2),
        '최신지표': {k: round(float(v), 4) for k, v in latest_indicators.items()},
        '예측종가_5일': [
            {'날짜': d, '예측종가': round(float(p), 2)}
            for d, p in zip(dates, preds)
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))


