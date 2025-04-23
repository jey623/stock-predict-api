from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import xgboost as xgb
from ta import add_all_ta_features
import traceback

app = Flask(__name__)

# 종목명 → 종목코드 매핑 (필요 시 확장 가능)
name_to_code = {
    "삼성전자": "005930",
    "카카오": "035720",
    "NAVER": "035420",
    "LG전자": "066570",
    "SK하이닉스": "000660",
    # 추가 가능
}

# 사용되는 기술적 지표 feature 리스트 (입력 피처 선정)
feature_cols = [
    'volume',
    'open',
    'high',
    'low',
    'close',
    'trend_macd', 'trend_macd_signal',
    'momentum_rsi', 'trend_adx', 'trend_adx_pos', 'trend_adx_neg',
    'volatility_bbm', 'volatility_bbh', 'volatility_bbl',
    'trend_visual_indicator',
]

@app.route("/predict")
def predict():
    try:
        stock_input = request.args.get("stock")
        stock_code = name_to_code.get(stock_input, stock_input)  # 한글 입력 시 코드로 변환

        print(f"✅ [1] 입력된 종목코드: {stock_code}")

        # 5년치 주가 데이터 수집
        df = fdr.DataReader(stock_code)
        df = df[-(252 * 5):]  # 5년치 (영업일 기준 252일 * 5)
        print(f"✅ [2] 데이터 수집 완료. 총 행 수: {len(df)}")

        # 기술적 지표 계산
        df = add_all_ta_features(
            df, open="Open", high="High", low="Low", close="Close", volume="Volume", fillna=True
        )

        df.columns = df.columns.str.lower()
        df.rename(columns={'close': 'close'}, inplace=True)
        df.dropna(inplace=True)
        print(f"✅ [3] 기술적 지표 적용 및 결측 제거 완료. 사용 행 수: {len(df)}")

        # 예측용 데이터 구성
        X = []
        for i in range(len(df) - 1):
            try:
                X.append(df[feature_cols].iloc[i].values)
            except Exception as e:
                print("⚠️ 행 스킵 -", i, e)
                continue
        X = np.array(X)

        # 마지막 입력값 예측
        model = xgb.XGBRegressor()
        model.fit(X[:-1], df['close'].iloc[1:len(X)])
        prediction = model.predict(X[-1].reshape(1, -1))[0]

        current_price = df['close'].iloc[-1]
        print(f"✅ [4] 현재가: {current_price}, 예측가: {prediction}")

        return jsonify({
            "종목코드": stock_code,
            "현재가": round(current_price, 2),
            "예측가": round(float(prediction), 2),
            "예상수익률(%)": round(((prediction - current_price) / current_price) * 100, 2)
        })

    except Exception as e:
        print("❌ 예외 발생:", e)
        traceback.print_exc()
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)

