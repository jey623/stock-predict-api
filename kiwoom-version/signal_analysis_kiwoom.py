import datetime

def analyze_full_stock(code):
    try:
        # ✅ 오늘 날짜 기준으로 2년 전부터의 데이터만 가져오기
        end_date = datetime.datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.datetime.today() - datetime.timedelta(days=365*2)).strftime('%Y-%m-%d')
        
        df = fdr.DataReader(code, start=start_date, end=end_date).dropna().copy()
        df.reset_index(inplace=True)

        # 기술 지표 계산 (생략 없이 그대로 유지)
        df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
        df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"], window=20).cci()
        df["OBV"] = ta.volume.OnBalanceVolumeIndicator(df["Close"], df["Volume"]).on_balance_volume()
        df["MA5"] = df["Close"].rolling(window=5).mean()
        df["MA20"] = df["Close"].rolling(window=20).mean()
        df["MA60"] = df["Close"].rolling(window=60).mean()
        df["MA120"] = df["Close"].rolling(window=120).mean()

        cur = float(df["Close"].iloc[-1])
        ma_array = sorted([
            ("MA5", df["MA5"].iloc[-1]),
            ("MA20", df["MA20"].iloc[-1]),
            ("MA60", df["MA60"].iloc[-1]),
            ("MA120", df["MA120"].iloc[-1])
        ], key=lambda x: -x[1])
        ma_order = " > ".join([x[0] for x in ma_array])

        return {
            "종목명": _code2name(code),
            "종목코드": code,
            "현재가": cur,
            "기술지표": {
                "RSI": {"값": round(df["RSI"].iloc[-1], 2), "해석": "과매수 경계" if df["RSI"].iloc[-1] > 70 else "정상"},
                "CCI": {"값": round(df["CCI"].iloc[-1], 2), "해석": "단기 급등 흐름" if df["CCI"].iloc[-1] > 100 else "중립"},
                "OBV 변화": int(df["OBV"].iloc[-1] - df["OBV"].iloc[-2]),
                "이동평균 배열": f"{ma_order}",
                "현재가 vs 60일선": "상단" if cur > df["MA60"].iloc[-1] else "하단",
                "현재가 vs 120일선": "상단" if cur > df["MA120"].iloc[-1] else "하단"
            },
            "요약": "상승 흐름 지속 중. RSI 과열 주의." if df["RSI"].iloc[-1] > 70 else "단기 안정 흐름."
        }

    except Exception as e:
        return {"error": str(e)}

