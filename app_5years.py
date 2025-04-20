from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import ta

app = Flask(__name__)

# ✅ 종목명 또는 종목코드 인식 함수
def get_stock_code(query):
    stock_list = fdr.StockListing('KRX')

    if query.isdigit():  # 숫자만 입력된 경우 → 종목코드로 인식
        if query in stock_list['Code'].values:
            return query
        else:
            return None
    else:  # 문자열이면 종목명으로 처리
        try:
            code = stock_list.loc[stock_list['Name'] == query, 'Code'].values[0]
            return code
        except:
            return None

# 📊 기술적 지표 계산 함수
def calculate_indicators(df):
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA40'] = df['Close'].rolling(window=40).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()

    # RSI
    df['RSI'] = ta.momentum.RSIIndicator(df['Close']).rsi()

    # MACD & Signal
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['Signal'] = macd.macd_signal()

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df['Close'])
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_middle'] = bb.bollinger_mavg()
    df['BB_lower'] = bb.bollinger_lband()

    # OBV
    df['OBV'] = ta.volume.OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()

    # MFI
    df['MFI'] = ta.volume.MFIIndicator(df['High'], df['Low'], df['Close'], df['Volume']).money_flow_index()

    # +DI / -DI (Directional Movement Index)
    dmi = ta.trend.DirectionalMovementIndexIndicator(df['High'], df['Low'], df['Close'])
    df['+DI'] = dmi.adx_pos()
    df['-DI'] = dmi.adx_neg()

    df.dropna(inplace=True)
    return df

@app.route('/get_indicators', methods=['GET'])
def get_indicators():
    query = request.args.get('stock')
    if not query:
        return jsonify({"error": "stock 파라미터를 입력해주세요."}), 400

    code = get_stock_code(query)
    if not code:
        return jsonify({"error": f"{query}의 종목코드를 찾을 수 없습니다."}), 404

    try:
        df = fdr.DataReader(code, start='2020-01-01')  # 5년치 기준
        df = calculate_indicators(df)
        latest = df.iloc[-1]

        # 종목명 찾기
        stock_list = fdr.StockListing('KRX')
        name_row = stock_list[stock_list['Code'] == code]
        stock_name = name_row['Name'].values[0] if not name_row.empty else query

        result = {
            "종목명": stock_name,
            "종목코드": code,
            "날짜": str(latest.name.date()),
            "현재가": int(latest["Close"]),
            "MA20": round(latest["MA20"], 2),
            "MA40": round(latest["MA40"], 2),
            "MA60": round(latest["MA60"], 2),
            "RSI": round(latest["RSI"], 2),
            "MACD": round(latest["MACD"], 2),
            "신호선": round(latest["Signal"], 2),
            "볼린저상단": round(latest["BB_upper"], 2),
            "볼린저중단": round(latest["BB_middle"], 2),
            "볼린저하단": round(latest["BB_lower"], 2),
            "OBV": int(latest["OBV"]),
            "MFI": round(latest["MFI"], 2),
            "+DI": round(latest["+DI"], 2),
            "-DI": round(latest["-DI"], 2)
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)


