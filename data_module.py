import pandas as pd
import json
from datetime import datetime
from pytz import timezone
from pykrx import stock
import numpy as np
import streamlit as st

# 시간대 설정
KST = timezone('Asia/Seoul')

# config.json 로드 - 캐싱을 통해 반복적인 파일 읽기 방지
@st.cache_data
def load_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

try:
    CONFIG = load_config()
    PORTFOLIO_CONFIG = CONFIG['portfolios']
except Exception as e:
    st.error(f"설정 파일을 로드하는 중 오류가 발생했습니다: {e}")
    PORTFOLIO_CONFIG = {}

@st.cache_data(ttl=3600)
def get_etf_price(ticker: str, start_date: str = '20241209', end_date: str = None) -> pd.DataFrame:
    """
    ETF 가격 데이터 조회 (캐싱 적용)
    """
    if end_date is None:
        end_date = datetime.now(KST).strftime('%Y%m%d')
    
    try:
        df = stock.get_market_ohlcv(start_date, end_date, ticker)
        return df
    except Exception as e:
        print(f"[ERROR] {ticker} 조회 실패: {str(e)}")
        return pd.DataFrame()


def calculate_mdd(prices: pd.Series) -> float:
    """
    최대 낙폭(MDD) 계산
    """
    if len(prices) < 2:
        return 0
    
    cummax = prices.expanding().max()
    drawdown = (prices - cummax) / cummax * 100
    return float(drawdown.min())


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """
    샤프 비율 계산 (연율화)
    """
    if len(returns) == 0:
        return 0
    
    # 일간 수익률을 연간으로 환산 (영업일 252일 기준)
    annual_return = returns.mean() * 252
    annual_std = returns.std() * np.sqrt(252)
    
    if annual_std == 0:
        return 0
    
    sharpe = (annual_return - risk_free_rate) / annual_std
    return float(sharpe)


def get_portfolio_performance(portfolio_name: str) -> dict:
    """
    포트폴리오 전체 성과 계산 (2024년 12월 9일부터)
    """
    if portfolio_name not in PORTFOLIO_CONFIG:
        return {}
    
    config = PORTFOLIO_CONFIG[portfolio_name]
    etfs = config['etfs']
    
    start_date = '20241209'
    end_date = datetime.now(KST).strftime('%Y%m%d')
    
    # 데이터 수집 및 병합
    price_df = pd.DataFrame()
    
    for etf_name, etf_info in etfs.items():
        ticker = etf_info['ticker']
        weight = etf_info['weight']
        
        if weight <= 0:
            continue
            
        df = get_etf_price(ticker, start_date, end_date)
        
        if not df.empty and '종가' in df.columns:
            # 첫 번째 데이터면 인덱스 설정, 아니면 조인
            if price_df.empty:
                price_df[etf_name] = df['종가']
            else:
                price_df = price_df.join(df['종가'].rename(etf_name), how='outer')
    
    if price_df.empty:
        return {}
    
    # 결측치 처리 (앞의 데이터로 채움)
    price_df = price_df.ffill().dropna()
    
    if price_df.empty:
        return {}
    
    # 포트폴리오 가중치 적용 가격 지수 계산
    # (각 자산의 시작가를 100으로 정규화한 뒤 가중치 적용)
    normalized_prices = price_df / price_df.iloc[0] * 100
    portfolio_index = pd.Series(0.0, index=price_df.index)
    
    for etf_name in price_df.columns:
        weight = etfs[etf_name]['weight']
        portfolio_index += normalized_prices[etf_name] * weight
    
    # 지표 계산
    daily_returns = portfolio_index.pct_change().dropna()
    
    total_return = (portfolio_index.iloc[-1] / portfolio_index.iloc[0] - 1) * 100
    mdd = calculate_mdd(portfolio_index)
    sharpe = calculate_sharpe_ratio(daily_returns)
    annual_return = daily_returns.mean() * 252 * 100  # 연환산 수익률(%)

    return {
        'total_return': total_return,
        'annual_return': annual_return,  # 추가
        'mdd': mdd,
        'sharpe_ratio': sharpe,
        'target_sharpe': config.get('target_sharpe', 0),
        'prices': portfolio_index,
        'returns': daily_returns,
        'last_updated': price_df.index[-1].strftime('%Y-%m-%d') if not price_df.empty else None
    }