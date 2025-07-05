from flask import Flask, request, jsonify
import FinanceDataReader as fdr
import pandas as pd
import ta

app = Flask(__name__)
krx = fdr.StockListing("KRX")

def _code2name(code):
    return krx.loc[krx["Code"] == code, "Name"].squeeze()

def _name2code(name):
    return krx.loc[krx["Name"] == name, "Code"].squeeze()

def get_stock_data_with_indicators(code):
    try:
        df = fdr.DataReader(code, start="2014-01-01").dropna().copy()
        df.reset_index(inplace=True)

        df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
        df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"], window=20).cci()
        df["OBV"] = ta.volume.OnBalanceVolumeIndicator(df["Close"], df["Volume"]).on_balance_volume()
        df["MA5"] = df["Close"].rolling(window=5).mean()
        df["MA20"] = df["Close"].rolling(window=20).mean()
        df["MA60"] = df["Close"].rolling(window=60).mean()
        df["MA120"] = df["Close"].rolling(window=120).mean()

        df_filtered = df.dropna().copy()
        return {
            "종목명": _code2name(code),
            "종목코드": code,
            "주가데이터": df_filtered.to_dict(orient="records")
        }
    except:
        return None

@app.route("/full_analysis")
def full_analysis():
    symbol = request.args.get("symbol")
    code = symbol if symbol.isdigit() else _name2code(symbol)
    if not code:
        return jsonify({"error": "유효한 종목명 또는 코드가 아닙니다."}), 404
    result = get_stock_data_with_indicators(code)
    return jsonify(result or {"message": "분석에 실패했습니다."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


