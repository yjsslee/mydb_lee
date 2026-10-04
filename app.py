import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="이유진의 주식 투자 대시보드", page_icon="📈", layout="wide")
st.markdown("""
<style>
.stApp { background:#f4f7fc; }
.block-container { max-width:1400px; padding-top:2rem; }
[data-testid="stSidebar"] { background:#203752; }
[data-testid="stSidebar"] * { color:#f7f9fc; }
div[data-testid="stMetric"] { background:white; border:1px solid #e4ebf5; border-radius:14px; padding:16px; }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("📈 이유진의")
st.sidebar.subheader("주식 투자 대시보드")
page = st.sidebar.radio("메뉴", ["홈", "차트 보기", "API 설정"])
st.title("이유진의 주식 투자 대시보드")
st.caption("처음부터 다시 시작하는 기본 버전")

def has_secret(name):
    try:
        return bool(str(st.secrets.get(name, "")).strip())
    except Exception:
        return False

@st.cache_data
def demo_prices():
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=130)
    rng = np.random.default_rng(7)
    close = 70000 + np.cumsum(rng.normal(0, 450, len(dates)))
    data = pd.DataFrame({"날짜": dates, "종가": close})
    data["20일 이동평균"] = data["종가"].rolling(20).mean()
    data["60일 이동평균"] = data["종가"].rolling(60).mean()
    return data

def draw_chart(data):
    fig = go.Figure()
    for col in ["종가", "20일 이동평균", "60일 이동평균"]:
        fig.add_trace(go.Scatter(x=data["날짜"], y=data[col], mode="lines", name=col))
    fig.update_layout(height=430, margin=dict(l=10,r=10,t=30,b=10),
                      paper_bgcolor="white", plot_bgcolor="white",
                      hovermode="x unified", legend=dict(orientation="h", y=1.12, x=0),
                      xaxis=dict(title="", showgrid=True, gridcolor="#edf1f7"),
                      yaxis=dict(title="가격(원)", showgrid=True, gridcolor="#edf1f7"))
    st.plotly_chart(fig, use_container_width=True)

data = demo_prices()
if page == "홈":
    a,b,c = st.columns(3)
    a.metric("키움 App Key", "등록됨" if has_secret("KIWOOM_APP_KEY") else "미등록")
    b.metric("키움 App Secret", "등록됨" if has_secret("KIWOOM_APP_SECRET") else "미등록")
    c.metric("KRX API Key", "등록됨" if has_secret("KRX_API_KEY") else "미등록")
    st.info("차트는 화면 확인용 예시 데이터입니다. 실제 주가가 아닙니다.")
    left,right = st.columns([1,2])
    with left:
        st.subheader("관심종목")
        st.dataframe(pd.DataFrame([
            ["삼성전자","005930"],["SK하이닉스","000660"],["한미반도체","042700"],
            ["HD현대일렉트릭","267260"],["두산에너빌리티","034020"]
        ], columns=["종목명","종목코드"]), hide_index=True, use_container_width=True)
    with right:
        st.subheader("예시 주가 차트")
        draw_chart(data)
elif page == "차트 보기":
    period = st.selectbox("기간 선택", ["최근 1개월","최근 3개월","최근 6개월"])
    n = {"최근 1개월":22,"최근 3개월":65,"최근 6개월":130}[period]
    st.warning("아래는 예시 데이터이며 실제 시장 가격이 아닙니다.")
    draw_chart(data.tail(n))
    st.dataframe(data.tail(10).round(2), hide_index=True, use_container_width=True)
else:
    st.subheader("API 설정")
    st.code('KIWOOM_APP_KEY = "발급받은_키움_모의투자_APP_KEY"\nKIWOOM_APP_SECRET = "발급받은_키움_모의투자_APP_SECRET"\nKRX_API_KEY = "발급받은_KRX_API_KEY"', language="toml")
    st.write("키움 App Key:", "등록됨" if has_secret("KIWOOM_APP_KEY") else "미등록")
    st.write("키움 App Secret:", "등록됨" if has_secret("KIWOOM_APP_SECRET") else "미등록")
    st.write("KRX API Key:", "등록됨" if has_secret("KRX_API_KEY") else "미등록")
    st.warning("키 등록 상태와 실제 API 연결 성공은 다릅니다. 다음 단계에서 API를 하나씩 연결합니다.")

st.divider()
st.caption("기본 버전 · 차트는 예시 데이터입니다. 투자 판단에 사용하지 마세요.")
