from flask import Flask, request, jsonify
import pandas as pd
import FinanceDataReader as fdr
import ta
from xgboost import XGBRegressor
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

def predict_future(df_ti, latest_close, days=10):
    df = df_ti.copy()
    df['Target'] = (df['Close'].shift(-days) - df['Close']) / df['Close']
    df = df.dropna()
    features = ['RSI','CCI','OBV','Disparity','MA5','MA20','MA60','MA120']
    X, y = df[features], df['Target']
    model = XGBRegressor(n_estimators=100, random_state=42, verbosity=0)
    model.fit(X, y)
    last_feat = df.iloc[-1:][features].copy()
    preds = []
    for _ in range(days):
        rate = model.predict(last_feat)[0]
        if pd.isna(rate) or abs(rate) > 0.5:
            rate = 0
        latest_close *= (1 + rate)
        preds.append(latest_close)
        last_feat.iloc[0, 0] = rate  # RSI에 임시 대입
    return preds

def calculate_mdd(df):
    cummax = df['Close'].cummax()
    drawdown = (df['Close'] - cummax) / cummax
    mdd = drawdown.min()
    return round(float(mdd) * 100, 2)

def calculate_cagr(df):
    start_value = df['Close'].iloc[0]
    end_value = df['Close'].iloc[-1]
    years = (df.index[-1] - df.index[0]).days / 365.0
    if years == 0:
        return 0.0
    cagr = ((end_value / start_value) ** (1 / years)) - 1
    return round(float(cagr) * 100, 2)

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

    df_ti = compute_technical_indicators(df)
    latest_close = df['Close'].iloc[-1]
    preds = predict_future(df_ti, latest_close=latest_close, days=days)
    latest_indicators = df_ti.iloc[-1][['RSI','CCI','OBV','Disparity','MA5','MA20','MA60','MA120']].to_dict()

    mdd = calculate_mdd(df)
    cagr = calculate_cagr(df)

    dates = []
    last_date = df.index[-1]
    cnt = 1
    while len(dates) < days:
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
        '예측종가_10일': [
            {'날짜': d, '예측종가': round(float(p), 2)}
            for d, p in zip(dates, preds)
        ],
        'MDD': f'{mdd} %',
        'CAGR': f'{cagr} %'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))


