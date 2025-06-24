import pandas as pd

def analyze_signal(df):
    result = {}

    # 이동평균선 계산
    ma5 = df["Close"].rolling(window=5).mean()
    ma20 = df["Close"].rolling(window=20).mean()

    # OBV 계산
    obv = [0]
    for i in range(1, len(df)):
        if df["Close"][i] > df["Close"][i - 1]:
            obv.append(obv[-1] + df["Volume"][i])
        elif df["Close"][i] < df["Close"][i - 1]:
            obv.append(obv[-1] - df["Volume"][i])
        else:
            obv.append(obv[-1])
    df["OBV"] = obv

    # OBV 트렌드
    obv_trend = df["OBV"].iloc[-1] - df["OBV"].iloc[-5]
    price_trend = df["Close"].iloc[-1] - df["Close"].iloc[-5]

    score = 0
    if obv_trend > 0 and price_trend < 0:
        result['OBV_분석'] = "OBV 유지, 주가 하락 → 매집 가능성"
        score += 1
    elif obv_trend > 0:
        result['OBV_분석'] = "OBV 상승 → 세력 매집 중일 가능성"
        score += 1
    else:
        result['OBV_분석'] = "OBV 감소 → 세력 이탈 가능성"

    # 이평선 분석
    if ma5.iloc[-1] > ma20.iloc[-1] and ma5.iloc[-1] > ma5.iloc[-3] and ma20.iloc[-1] > ma20.iloc[-3]:
        result["이평선분석"] = "5일선 > 20일선, 둘 다 상승"
        score += 1
    else:
        result["이평선분석"] = "이평선 약세 또는 하락 전환"

    # CCI 계산
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    cci = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std())
    cci_value = round(cci.iloc[-1], 2)
    result["CCI"] = cci_value
    if 50 < cci_value < 150:
        score += 1

    # 봉 형태 판단
    candle = df.iloc[-1]
    body = abs(candle["Close"] - candle["Open"])
    avg_range = (df["High"] - df["Low"]).mean()
    is_bull_short = (candle["Close"] > candle["Open"]) and (body < avg_range * 0.5)
    is_bear = candle["Close"] < candle["Open"]
    if is_bull_short or is_bear:
        result["캔들조건"] = "음봉 또는 짧은 양봉"
        score += 1
    else:
        result["캔들조건"] = "비적합"

    result['기술점수'] = f"{score} / 4"

    # 1~5일 수익률 예측
    future_returns = {}
    returns_list = []
    for day in range(1, 6):
        future_price = df["Close"].shift(-day)
        valid = ~future_price.isnull()
        returns = ((future_price[valid] - df["Close"][valid]) / df["Close"][valid]) * 100
        avg_return = round(returns.mean(), 2)
        future_returns[f"{day}일"] = avg_return
        returns_list.append(avg_return)

    result["단기예측"] = future_returns

    # 예측 방향성
    if returns_list == sorted(returns_list):
        result['예측추세'] = "우상향"
    elif returns_list == sorted(returns_list, reverse=True):
        result['예측추세'] = "우하향"
    else:
        result['예측추세'] = "불규칙"

    # 진입 추천 판단
    if score >= 3 and future_returns['3일'] > 2.0:
        result['진입추천'] = '강하게 추천 🔥'
    elif score >= 2 and future_returns['3일'] > 1.0:
        result['진입추천'] = '가능'
    else:
        result['진입추천'] = '보류 또는 관망'

    return result

