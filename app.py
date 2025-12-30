import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from data_module import get_portfolio_performance, PORTFOLIO_CONFIG

# 페이지 설정
st.set_page_config(page_title="ISA Portfolio Dashboard", layout="wide")
st.title("📊 ISA 포트폴리오 대시보드")

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    portfolio = st.selectbox(
        "포트폴리오 선택",
        list(PORTFOLIO_CONFIG.keys())
    )
    
    st.markdown("---")
    st.info(f"🎯 목표 샤프 비율: {PORTFOLIO_CONFIG[portfolio]['target_sharpe']}")
    st.info(f"📝 {PORTFOLIO_CONFIG[portfolio].get('description', '포트폴리오 설명 없음')}")

# 포트폴리오 성과 조회
perf = get_portfolio_performance(portfolio)

if perf:
    # 메트릭 표시
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📈 연간 수익률",
            f"{perf['annual_return']:.2f}%"
        )
    
    with col2:
        st.metric(
            "📊 샤프 비율",
            f"{perf['sharpe_ratio']:.2f}",
            delta=f"목표: {perf['target_sharpe']}"
        )
    
    with col3:
        st.metric(
            "📉 최대 낙폭 (MDD)",
            f"{perf['mdd']:.2f}%"
        )
    
    with col4:
        achievement = (perf['sharpe_ratio'] / perf['target_sharpe']) * 100
        st.metric(
            "🎯 목표 달성도",
            f"{achievement:.1f}%"
        )
    
    # 차트
    st.markdown("---")
    st.subheader("📈 누적 수익률")
    
    fig = go.Figure()
    prices = perf['prices']
    normalized = (prices / prices.iloc[0] - 1) * 100
    
    fig.add_trace(go.Scatter(
        x=normalized.index,
        y=normalized.values,
        mode='lines',
        name='누적 수익률',
        line=dict(width=2, color='#1f77b4'),
        fill='tozeroy'
    ))
    
    fig.update_layout(
        hovermode='x unified',
        height=400,
        xaxis_title="날짜",
        yaxis_title="누적 수익률 (%)",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 포트폴리오 구성
    st.markdown("---")
    st.subheader("🎲 포트폴리오 구성")
    
    etf_data = []
    for etf_name, etf_info in PORTFOLIO_CONFIG[portfolio]['etfs'].items():
        weight = etf_info['weight']
        if weight > 0:
            etf_data.append({
                'ETF': etf_name,
                '비중': f"{weight*100:.1f}%",
                '설명': etf_info.get('description', '상품 설명 없음')
            })
    
    if etf_data:
        df = pd.DataFrame(etf_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 포트폴리오 설명
        st.markdown("---")
        st.info(f"📌 **포트폴리오 설명**: {PORTFOLIO_CONFIG[portfolio].get('description', '')}")
    else:
        st.info("포트폴리오 데이터 없음")
    
    # 성과 통계
    st.markdown("---")
    st.subheader("📊 성과 통계")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "데이터 기간",
            f"{len(perf['prices'])}일"
        )
    
    with col2:
        daily_return = perf['returns'].mean() * 100
        st.metric(
            "평균 일일 수익률",
            f"{daily_return:.4f}%"
        )
    
    with col3:
        daily_volatility = perf['returns'].std() * 100
        st.metric(
            "일일 변동성",
            f"{daily_volatility:.4f}%"
        )

else:
    st.error("❌ 데이터를 불러올 수 없습니다. KRX 데이터 서비스를 확인하세요.")
    st.info("💡 새로고침을 시도해주세요.")