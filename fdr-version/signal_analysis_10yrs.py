import FinanceDataReader as fdr
import pandas as pd
import ta
from datetime import datetime, timedelta

# 사용자 입력: 종목코드 여러 개
codes_input = input("3년치 주가 데이터를 받을 종목코드를 콤마로 구분해 입력하세요(예: 005930,035720): ")
codes = [code.strip() for code in codes_input.split(',') if code.strip()]

# 3년치 기간 설정 (1095일)
today = datetime.today().strftime('%Y-%m-%d')
start_date = (datetime.today() - timedelta(days=1095)).strftime('%Y-%m-%d')

# 상장종목 리스트(종목명 매칭용)
try:
    info = fdr.StockListing('KRX')
except Exception:
    info = None

for code in codes:
    try:
        df = fdr.DataReader(code, start_date, today)
        if df.empty:
            print(f"{code}: 데이터가 없습니다.")
            continue

        # 등락률(Change)
        df['Change'] = df['Close'].pct_change().fillna(0)

        # 이동평균선
        df['MA5'] = ta.trend.sma_indicator(df['Close'], window=5)
        df['MA20'] = ta.trend.sma_indicator(df['Close'], window=20)
        df['MA60'] = ta.trend.sma_indicator(df['Close'], window=60)
        df['MA120'] = ta.trend.sma_indicator(df['Close'], window=120)

        # 이격도(Disparity)
        df['Disparity5'] = (df['Close'] / df['MA5']) * 100
        df['Disparity20'] = (df['Close'] / df['MA20']) * 100
        df['Disparity60'] = (df['Close'] / df['MA60']) * 100
        df['Disparity120'] = (df['Close'] / df['MA120']) * 100

        # RSI, MACD, OBV, CCI
        df['RSI14'] = ta.momentum.rsi(df['Close'], window=14)
        df['MACD'] = ta.trend.macd(df['Close'])
        df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
        df['CCI20'] = ta.trend.cci(df['High'], df['Low'], df['Close'], window=20)

        # 일목균형표
        high9 = df['High'].rolling(window=9).max()
        low9 = df['Low'].rolling(window=9).min()
        df['Ichimoku_Conversion'] = (high9 + low9) / 2

        high26 = df['High'].rolling(window=26).max()
        low26 = df['Low'].rolling(window=26).min()
        df['Ichimoku_Base'] = (high26 + low26) / 2

        df['Ichimoku_LeadingSpan1'] = ((df['Ichimoku_Conversion'] + df['Ichimoku_Base']) / 2).shift(26)
        high52 = df['High'].rolling(window=52).max()
        low52 = df['Low'].rolling(window=52).min()
        df['Ichimoku_LeadingSpan2'] = ((high52 + low52) / 2).shift(26)

        df['Ichimoku_Lagging'] = df['Close'].shift(-26)

        # 종목명
        name = code
        if info is not None:
            try:
                name = info[info['Code'] == code]['Name'].values[0]
            except Exception:
                pass

        # 저장할 컬럼 순서 정의
        save_cols = [
            'Open', 'High', 'Low', 'Close', 'Volume', 'Change',
            'MA5', 'MA20', 'MA60', 'MA120',
            'Disparity5', 'Disparity20', 'Disparity60', 'Disparity120',
            'RSI14', 'MACD', 'OBV', 'CCI20',
            'Ichimoku_Conversion', 'Ichimoku_Base',
            'Ichimoku_LeadingSpan1', 'Ichimoku_LeadingSpan2', 'Ichimoku_Lagging'
        ]
        # Date 컬럼 처리
        if 'Date' not in df.columns:
            df = df.reset_index()
        filename = f"{name}_{code}_3년치_기술적분석.csv"
        df[['Date'] + save_cols].to_csv(filename, encoding='cp949', index=False)
        print(f"{name}({code}) 3년치 데이터가 '{filename}' 파일로 저장되었습니다. (기술적지표 포함)")
    except Exception as e:
        print(f"{code}: 데이터 저장 실패 - {e}")



