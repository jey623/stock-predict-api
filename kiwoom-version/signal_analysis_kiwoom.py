from flask import Flask, request, jsonify
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import pandas as pd
import ta

app = Flask(__name__)

@app.route('/full_analysis', methods=['GET'])
def get_stock_technical_data():
    symbol = request.args.get('symbol')
    if not symbol:
        return "symbol 파라미터는 필수입니다.", 400

    try:
        # 최근 2년치 데이터 조회
        end_date = datetime.today()
        start_date = end_date - timedelta(days=2*365)

        df = fdr.DataReader(symbol, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        df.reset_index(inplace=True)

        # 기술적 지표 계산
        df['RSI'] = ta.momentum.RSIIndicator(close=df['Close']).rsi()
        df['CCI'] = ta.trend.cci(high=df['High'], low=df['Low'], close=df['Close'])
        df['OBV'] = ta.volume.OnBalanceVolumeIndicator(close=df['Close'], volume=df['Volume']).on_balance_volume()

        # 결과 구성 (가장 최근 값 기준)
        technicals = {
            "RSI": round(df['RSI'].iloc[-1], 2),
            "CCI": round(df['CCI'].iloc[-1], 2),
            "OBV": int(df['OBV'].iloc[-1])
        }

        return jsonify({
            "기술지표": technicals,
            "주가데이터": df.tail(100).to_dict(orient='records')  # 최근 100일 데이터
        })

    except Exception as e:
        return f"분석 중 오류 발생: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)

