import pandas as pd
import json
from datetime import datetime
from pytz import timezone
from pykrx import stock
import numpy as np

KST = timezone('Asia/Seoul')

# config.json에서 중립형 포트폴리오 ETF 정보 불러오기
def load_neutral_etfs(config_path='config.json'):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    neutral_etfs = config['portfolios']['중립적 (Neutral)']['etfs']
    return neutral_etfs

# ETF별 가격 데이터 조회
def get_etf_price(ticker, start_date='20241209', end_date=None):
    if end_date is None:
        end_date = datetime.now(KST).strftime('%Y%m%d')
    try:
        df = stock.get_market_ohlcv(start_date, end_date, ticker)
        return df['종가']
    except Exception as e:
        print(f"[ERROR] {ticker} 조회 실패: {str(e)}")
        return pd.Series(dtype=float)

# 중립형 포트폴리오 ETF별 가격 데이터프레임 생성
def get_neutral_portfolio_prices():
    etfs = load_neutral_etfs()
    price_df = pd.DataFrame()
    for etf_name, etf_info in etfs.items():
        ticker = etf_info['ticker']
        prices = get_etf_price(ticker)
        if not prices.empty:
            price_df[etf_name] = prices
    price_df = price_df.ffill().dropna()
    return price_df

# 상관관계 행렬 계산 함수
def calculate_correlation_matrix(price_df):
    returns_df = price_df.pct_change().dropna()
    return returns_df.corr()

if __name__ == "__main__":
    price_df = get_neutral_portfolio_prices()
    if price_df.empty:
        print("데이터가 없습니다.")
    else:
        corr_matrix = calculate_correlation_matrix(price_df)
        print("중립형 포트폴리오 상품별 수익률 상관관계 행렬:")
        print(corr_matrix)
