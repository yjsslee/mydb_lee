import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta

st.set_page_config(page_title="이유진의 주식 투자 대시보드", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# ---------- 디자인 ----------
st.markdown("""
<style>
  .stApp { background: #f4f7fc; color: #172b4d; }
  [data-testid="stSidebar"] { background: linear-gradient(180deg,#172b45 0%,#203958 100%); }
  [data-testid="stSidebar"] * { color: #f3f7ff !important; }
  .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1500px; }
  .hero { font-size: 1.85rem; font-weight: 750; color: #172b4d; margin-bottom: 0.15rem; }
  .subhero { color: #7184a4; margin-bottom: 1.1rem; }
  div[data-testid="stMetric"] { background: white; border: 1px solid #e5ecf6; padding: 17px 19px; border-radius: 14px; box-shadow: 0 3px 12px #243b5310; }
  div[data-testid="stMetricLabel"] p { color: #6c7f9e !important; }
  div[data-testid="stMetricValue"] { color: #172b4d !important; }
  div[data-testid="stVerticalBlockBorderWrapper"] { background: white; border: 1px solid #e5ecf6; border-radius: 14px; padding: 12px 14px; }
  h2, h3 { color: #172b4d !important; }
  .small-note { color:#7184a4; font-size:0.82rem; }
</style>
""", unsafe_allow_html=True)

# ---------- 사이드바 ----------
st.sidebar.markdown("# 📈 이유진의")
st.sidebar.markdown("## 주식 투자 대시보드")
st.sidebar.caption("시장 · 종목 · 차트 · 투자 습관")
page = st.sidebar.radio("메뉴", ["홈", "관심종목", "시장지수", "차트 분석", "설정"])
st.sidebar.markdown("---")
st.sidebar.caption("“작은 공부가 미래의 큰 자산이 됩니다.”")

# ---------- 데이터 연결 설정 ----------
def get_secret(name):
    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""

kiwoom_key = get_secret("KIWOOM_APP_KEY")
kiwoom_secret = get_secret("KIWOOM_APP_SECRET")
krx_key = get_secret("KRX_API_KEY")
api_configured = bool(kiwoom_key and kiwoom_secret and krx_key)

# 현재는 화면/차트 동작을 먼저 확인할 수 있도록 예시 데이터를 사용합니다.
# 다음 단계에서 계정의 실제 API URL·인증·응답 형식에 맞춰 조회 함수를 연결합니다.
@st.cache_data
def demo_data():
    rng = np.random.default_rng(42)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=130)
    close = 68000 + np.cumsum(rng.normal(0, 520, len(dates)))
    close = np.maximum(close, 50000)
    df = pd.DataFrame({"날짜": dates, "종가": close})
    df["20일 이동평균"] = df["종가"].rolling(20).mean()
    df["60일 이동평균"] = df["종가"].rolling(60).mean()
    df["거래량"] = rng.integers(5000000, 18000000, len(dates))
    return df

df = demo_data()
last = float(df["종가"].iloc[-1])
prev = float(df["종가"].iloc[-2])
change = (last / prev - 1) * 100

def section_title(title, caption=None):
    st.subheader(title)
    if caption:
        st.caption(caption)

def show_price_chart(data, name="삼성전자"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["날짜"], y=data["종가"], name="종가", line=dict(color="#4776e6", width=2.5)))
    fig.add_trace(go.Scatter(x=data["날짜"], y=data["20일 이동평균"], name="20일선", line=dict(color="#25b89a", width=1.7)))
    fig.add_trace(go.Scatter(x=data["날짜"], y=data["60일 이동평균"], name="60일선", line=dict(color="#f2a541", width=1.7)))
    fig.update_layout(height=350, margin=dict(l=8,r=8,t=18,b=8), paper_bgcolor="white", plot_bgcolor="white",
        font=dict(color="#536782"), legend=dict(orientation="h",y=1.12,x=0),
        xaxis=dict(showgrid=True,gridcolor="#edf1f7",title=""), yaxis=dict(showgrid=True,gridcolor="#edf1f7",title="원"))
    st.plotly_chart(fig, use_container_width=True)

def home():
    st.markdown('<div class="hero">안녕하세요, 이유진님!</div>', unsafe_allow_html=True)
    st.markdown('<div class="subhero">오늘도 차분하게 시장과 관심종목을 확인해 보세요. ☀️</div>', unsafe_allow_html=True)
    if not api_configured:
        st.info("현재는 화면 미리보기용 예시 데이터입니다. 실제 시세를 표시하려면 설정 메뉴 안내에 따라 API 키를 Streamlit Secrets에 등록하고 조회 기능을 연결해야 합니다.")
    a,b,c = st.columns(3)
    a.metric("코스피", "API 연결 전", "KRX 연결 필요")
    b.metric("코스닥", "API 연결 전", "KRX 연결 필요")
    c.metric("삼성전자 · 예시", f"{last:,.0f}원", f"{change:+.2f}%")
    left,right = st.columns([0.9,1.6], gap="medium")
    with left:
        with st.container(border=True):
            section_title("관심종목", "종목을 선택해 차트를 확인하세요.")
            stocks = pd.DataFrame([
                ["삼성전자","005930","반도체"],
                ["SK하이닉스","000660","반도체"],
                ["한미반도체","042700","반도체 장비"],
                ["HD현대일렉트릭","267260","전력기기"],
                ["두산에너빌리티","034020","에너지"],
            ], columns=["종목명","종목코드","산업"])
            st.dataframe(stocks, hide_index=True, use_container_width=True)
    with right:
        with st.container(border=True):
            section_title("삼성전자 주가 추이", "예시 차트 · 20일선과 60일선")
            show_price_chart(df)
    x,y = st.columns([1,1], gap="medium")
    with x:
        with st.container(border=True):
            section_title("오늘의 확인 항목")
            st.markdown("- 시장 지수의 방향과 변동폭 확인\n- 관심종목 거래량과 이동평균선 확인\n- 실적·공시 등 주가 변동의 이유 확인")
    with y:
        with st.container(border=True):
            section_title("투자 원칙")
            st.markdown("- 차트 신호 하나만으로 매매를 결정하지 않기\n- 실적과 산업 흐름을 함께 살피기\n- 수익보다 위험 관리와 기록을 우선하기")

def watchlist():
    section_title("관심종목", "현재 목록은 예시입니다. 실제 시세 연결 후 최신 가격으로 바꿉니다.")
    st.dataframe(pd.DataFrame([
        ["삼성전자","005930","반도체",f"{last:,.0f}원",f"{change:+.2f}%"],
        ["SK하이닉스","000660","반도체","API 연결 전","—"],
        ["한미반도체","042700","반도체 장비","API 연결 전","—"],
        ["HD현대일렉트릭","267260","전력기기","API 연결 전","—"],
        ["두산에너빌리티","034020","에너지","API 연결 전","—"],
    ],columns=["종목명","종목코드","산업","현재가","등락률"]),hide_index=True,use_container_width=True)
    st.caption("표시된 예시 가격과 수익률은 실제 시세가 아닙니다.")

def market():
    section_title("시장지수", "KRX API 연결 전 화면입니다.")
    a,b=st.columns(2)
    a.metric("코스피","조회 대기","KRX API 연결 필요")
    b.metric("코스닥","조회 대기","KRX API 연결 필요")
    st.info("KRX API의 이용 서비스와 응답 필드에 맞춰 지수 조회를 연결할 예정입니다.")

def chart_page():
    section_title("차트 분석")
    choice = st.selectbox("종목 선택",["삼성전자","SK하이닉스","한미반도체","HD현대일렉트릭","두산에너빌리티"])
    period = st.selectbox("조회 기간",["최근 6개월","최근 3개월","최근 1개월"])
    count = {"최근 6개월":len(df),"최근 3개월":65,"최근 1개월":22}[period]
    st.caption(f"{choice} · {period} · 예시 데이터")
    show_price_chart(df.tail(count), choice)
    st.markdown("**차트 읽기**")
    st.write("20일 이동평균선은 단기 흐름, 60일 이동평균선은 중기 흐름을 살펴보는 참고 지표입니다. 단독 매매 신호로 사용하지 마세요.")

def settings():
    section_title("API 설정", "비밀키는 Python 코드나 GitHub 저장소에 직접 입력하지 마세요.")
    st.markdown("""
    ### Streamlit Community Cloud에 등록할 Secrets
    앱을 배포한 뒤 **앱 설정 → Secrets**에 아래 형식으로 등록합니다.
    """)
    st.code('KIWOOM_APP_KEY = "키움 모의투자 App Key"\nKIWOOM_APP_SECRET = "키움 모의투자 App Secret"\nKRX_API_KEY = "KRX Open API 인증키"', language="toml")
    st.warning("키와 Secret을 이 대화에 보내지 마세요. GitHub에 커밋하지 말고 Streamlit Secrets에만 저장하세요.")
    st.markdown("### 연결 상태")
    st.write("키움 App Key:", "등록됨" if kiwoom_key else "미등록")
    st.write("키움 App Secret:", "등록됨" if kiwoom_secret else "미등록")
    st.write("KRX API Key:", "등록됨" if krx_key else "미등록")
    st.caption("키 등록만으로 실제 데이터 조회가 완료되는 것은 아닙니다. 다음 단계에서 인증 토큰과 각 API 요청/응답 형식에 맞춰 연결해야 합니다.")

if page == "홈":
    home()
elif page == "관심종목":
    watchlist()
elif page == "시장지수":
    market()
elif page == "차트 분석":
    chart_page()
else:
    settings()

st.markdown("---")
st.caption("교육용 대시보드 · 예시 데이터는 실제 투자 판단에 사용하지 마세요. 자동 주문 기능은 포함되어 있지 않습니다.")
