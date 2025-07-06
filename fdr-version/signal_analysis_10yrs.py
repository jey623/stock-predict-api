from datetime import datetime
import pandas as pd, FinanceDataReader as fdr, ta
import xgboost as xgb
from flask import Flask, request, jsonify

app = Flask(__name__)
krx = fdr.StockListing("KRX")

def _name2code(name): return krx.loc[krx["Name"] == name, "Code"].squeeze()
def _code2name(code): return krx.loc[krx["Code"] == code, "Name"].squeeze()

def create_features(df):
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    df['Disparity20'] = (df['Close'] / df['MA20']) * 100
    df['Disparity60'] = (df['Close'] / df['MA60']) * 100
    df['Disparity120'] = (df['Close'] / df['MA120']) * 100

    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
    df['CCI'] = ta.trend.CCIIndicator(df['High'], df['Low'], df['Close'], window=20).cci()
    obv = ta.volume.OnBalanceVolumeIndicator(close=df['Close'], volume=df['Volume']).on_balance_volume()
    df['OBV'] = obv

    # 추가 지표
    stoch = ta.momentum.StochasticOscillator(df['High'], df['Low'], df['Close'], window=14)
    df['Stoch_K'] = stoch.stoch()
    df['Stoch_D'] = stoch.stoch_signal()

    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff()

    df['ATR'] = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range()
    df['Momentum'] = ta.momentum.MomentumIndicator(df['Close'], window=10).momentum()
    df['Volume_Change'] = df['Volume'].pct_change() * 100

    df = df.dropna()
    return df

def train_model(df, day):
    df = create_features(df)
    df[f'Target_{day}'] = (df['Close'].shift(-day) - df['Close']) / df['Close'] * 100
    df = df.dropna()

    feature_cols = [
        'MA5', 'MA20', 'MA60', 'MA120',
        'Disparity20', 'Disparity60', 'Disparity120',
        'RSI', 'CCI', 'OBV',
        'Stoch_K', 'Stoch_D',
        'MACD', 'MACD_Signal', 'MACD_Hist',
        'ATR', 'Momentum', 'Volume_Change'
    ]
    X = df[feature_cols]
    y = df[f'Target_{day}']

    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, max_depth=3)
    model.fit(X, y)
    return model, df

def predict_next(df, models):
    df = create_features(df)
    latest = df.iloc[-1:]
    feature_cols = [
        'MA5', 'MA20', 'MA60', 'MA120',
        'Disparity20', 'Disparity60', 'Disparity120',
        'RSI', 'CCI', 'OBV',
        'Stoch_K', 'Stoch_D',
        'MACD', 'MACD_Signal', 'MACD_Hist',
        'ATR', 'Momentum', 'Volume_Change'
    ]
    X_latest = latest[feature_cols]
    current_price = latest['Close'].values[0]

    predictions = {}
    for day in range(1, 6):
        pred_return = models[day].predict(X_latest)[0]
        pred_price = round(current_price * (1 + pred_return / 100), 2)
        predictions[f"{day}일후"] = {
            "수익률": round(pred_return, 2),
            "예상종가": pred_price
        }

    return predictions, current_price

@app.route("/forecast")
def forecast():
    symbol = request.args.get("symbol", "")
    if not symbol:
        return jsonify({"error": "Need symbol"}), 400

    code = symbol if symbol.isdigit() else _name2code(symbol)
    name = _code2name(code) if symbol.isdigit() else symbol
    if not code or pd.isna(code):
        return jsonify({"error": "Invalid symbol"}), 400

    df = fdr.DataReader(code, start="2014-01-01")
    models = {}
    for day in range(1, 6):
        model, _ = train_model(df.copy(), day)
        models[day] = model

    predictions, cur_price = predict_next(df, models)

    return jsonify({
        "종목명": name,
        "종목코드": code,
        "현재가": round(cur_price, 2),
        "예측": predictions
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10010)

