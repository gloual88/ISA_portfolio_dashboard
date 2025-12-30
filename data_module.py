import pandas as pd
import json
from datetime import datetime
from pytz import timezone
from pykrx import stock
import numpy as np

# 시간대 설정
KST = timezone('Asia/Seoul')

# config.json 로드
with open('config.json', 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)

PORTFOLIO_CONFIG = CONFIG['portfolios']


def get_etf_price(ticker: str, start_date: str = '20241209', end_date: str = None) -> pd.DataFrame:
    """
    ETF 가격 데이터 조회
    
    Args:
        ticker: ETF 티커
        start_date: 시작 날짜 (YYYYMMDD)
        end_date: 종료 날짜 (YYYYMMDD)
    
    Returns:
        pd.DataFrame: 가격 데이터
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
    
    Args:
        prices: 가격 시계열
    
    Returns:
        float: MDD (%)
    """
    if len(prices) < 2:
        return 0
    
    cummax = prices.expanding().max()
    drawdown = (prices - cummax) / cummax * 100
    return drawdown.min()


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """
    샤프 비율 계산
    
    Args:
        returns: 일일 수익률
        risk_free_rate: 무위험 이율 (연율)
    
    Returns:
        float: 샤프 비율
    """
    if len(returns) == 0:
        return 0
    
    annual_return = returns.mean() * 252
    annual_std = returns.std() * np.sqrt(252)
    
    if annual_std == 0:
        return 0
    
    sharpe = (annual_return - risk_free_rate) / annual_std
    return sharpe


def get_portfolio_performance(portfolio_name: str) -> dict:
    """
    포트폴리오 전체 성과 계산 (12월 9일부터)
    
    Args:
        portfolio_name: 포트폴리오 이름
    
    Returns:
        dict: 포트폴리오 성과 지표
    """
    if portfolio_name not in PORTFOLIO_CONFIG:
        return {}
    
    config = PORTFOLIO_CONFIG[portfolio_name]
    etfs = config['etfs']
    
    # 포트폴리오 출발시점: 12월 9일 (2024-12-09)
    start_date = '20241209'
    end_date = datetime.now(KST).strftime('%Y%m%d')
    
    # 모든 ETF의 가격 데이터 조회
    all_prices = {}
    for etf_name, etf_info in etfs.items():
        ticker = etf_info['ticker']
        weight = etf_info['weight']
        
        # 비중이 0이면 스킵
        if weight == 0:
            continue
        
        prices = get_etf_price(ticker, start_date, end_date)
        
        if not prices.empty and '종가' in prices.columns:
            all_prices[etf_name] = prices['종가']
    
    if not all_prices:
        return {}
    
    # 모든 데이터를 공통 인덱스로 정렬
    common_index = all_prices[list(all_prices.keys())[0]].index
    for key in all_prices:
        all_prices[key] = all_prices[key].reindex(common_index, method='ffill')
    
    # 포트폴리오 가격 계산 (가중치 적용)
    portfolio_prices = pd.Series(0.0, index=common_index)
    for etf_name, prices in all_prices.items():
        weight = etfs[etf_name]['weight']
        if weight > 0:
            portfolio_prices += prices * weight
    
    # 성과 지표 계산
    if len(portfolio_prices) < 2:
        return {}
    
    daily_returns = portfolio_prices.pct_change().dropna()
    
    if portfolio_prices.iloc[0] > 0:
        annual_return = (portfolio_prices.iloc[-1] - portfolio_prices.iloc[0]) / portfolio_prices.iloc[0] * 100
    else:
        annual_return = 0
    
    mdd = calculate_mdd(portfolio_prices)
    sharpe = calculate_sharpe_ratio(daily_returns)
    
    return {
        'annual_return': annual_return,
        'mdd': mdd,
        'sharpe_ratio': sharpe,
        'target_sharpe': config['target_sharpe'],
        'prices': portfolio_prices,
        'returns': daily_returns
    }