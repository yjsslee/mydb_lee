import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import date, timedelta

st.set_page_config(page_title="이유진의 주식 투자 대시보드", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

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

st.sidebar.markdown("# 📈 이유진의")
st.sidebar.markdown("## 주식 투자 대시보드")
st.sidebar.caption("시장 · 종목 · 차트 · 투자 습관")
page = st.sidebar.radio("메뉴", ["홈", "관심종목", "시장지수", "차트 분석", "설정"])
st.sidebar.markdown("---")
st.sidebar.caption("“작은 공부가 미래의 큰 자산이 됩니다.”")

def get_secret(name):
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""

kiwoom_key = get_secret("KIWOOM_APP_KEY")
kiwoom_secret = get_secret("KIWOOM_APP_SECRET")
krx_key = get_secret("KRX_API_KEY")

def clean_number(value):
    """API에서 숫자 문자열에 포함된 쉼표/부호를 안전하게 숫자로 변환합니다."""
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("+", "")
    if not text or text in ("-", "None", "null"):
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None

@st.cache_data(ttl=300, show_spinner=False)
def get_kiwoom_token(app_key, app_secret):
    """키움 REST API 접근 토큰 발급. 키움 모의투자 서버를 사용합니다."""
    url = "https://mockapi.kiwoom.com/oauth2/token"
    response = requests.post(
        url,
        json={"grant_type": "client_credentials", "appkey": app_key, "secretkey": app_secret},
        headers={"Content-Type": "application/json;charset=UTF-8"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    token = data.get("token") or data.get("access_token")
    if not token:
        raise RuntimeError(data.get("return_msg") or data.get("error_description") or "토큰 응답에서 token을 찾지 못했습니다.")
    return token

@st.cache_data(ttl=60, show_spinner=False)
def get_kiwoom_quote(app_key, app_secret, stock_code):
    token = get_kiwoom_token(app_key, app_secret)
    response = requests.post(
        "https://mockapi.kiwoom.com/api/dostk/stkinfo",
        json={"stk_cd": stock_code},
        headers={
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {token}",
            "api-id": "ka10001",
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("return_code", 0) not in (0, "0", None):
        raise RuntimeError(data.get("return_msg", "키움 API가 오류를 반환했습니다."))
    price = clean_number(data.get("cur_prc"))
    if price is None:
        raise RuntimeError(data.get("return_msg") or "현재가(cur_prc)를 응답에서 찾지 못했습니다.")
    return {
        "price": abs(price),
        "change": clean_number(data.get("pred_pre")),
        "change_pct": clean_number(data.get("flu_rt")),
        "name": data.get("stk_nm", stock_code),
        "raw_date": date.today().isoformat(),
    }

def krx_latest_index(api_key, api_id, keyword):
    """KRX Open API에서 최근 제공된 지수 일별 시세를 조회합니다."""
    if not api_key:
        raise RuntimeError("KRX_API_KEY가 Streamlit Secrets에 등록되지 않았습니다.")
    url = f"https://data-dbg.krx.co.kr/svc/apis/idx/{api_id}"
    last_error = None
    # 주말·공휴일·장 마감 전에는 당일 자료가 없을 수 있으므로 최근 10일을 확인합니다.
    for offset in range(10):
        target = date.today() - timedelta(days=offset)
        try:
            response = requests.get(
                url,
                params={"basDd": target.strftime("%Y%m%d")},
                headers={"AUTH_KEY": api_key},
                timeout=15,
            )
            if response.status_code == 401 or response.status_code == 403:
                raise RuntimeError("KRX 인증에 실패했습니다. 인증키와 API 서비스 활용 승인을 확인하세요.")
            response.raise_for_status()
            payload = response.json()
            rows = None
            if isinstance(payload, list):
                rows = payload
            elif isinstance(payload, dict):
                for key in ("OutBlock_1", "output", "data", "items"):
                    if isinstance(payload.get(key), list):
                        rows = payload[key]
                        break
            if not rows:
                continue
            matches = [r for r in rows if keyword.lower() in str(r.get("IDX_NM", "")).lower()]
            row = matches[0] if matches else rows[0]
            value = clean_number(row.get("CLSPRC_IDX"))
            if value is not None:
                return {
                    "value": value,
                    "date": row.get("BAS_DD", target.strftime("%Y%m%d")),
                    "name": row.get("IDX_NM", keyword),
                    "change_pct": clean_number(row.get("FLUC_RT")),
                }
        except Exception as exc:
            last_error = exc
            if isinstance(exc, RuntimeError) and "인증에 실패" in str(exc):
                raise
    if last_error:
        raise RuntimeError(f"KRX 지수 조회 실패: {last_error}")
    raise RuntimeError("최근 10일 자료에서 지수를 찾지 못했습니다. KRX API 서비스 신청·승인과 키를 확인하세요.")

@st.cache_data(ttl=900, show_spinner=False)
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

def section_title(title, caption=None):
    st.subheader(title)
    if caption:
        st.caption(caption)

def show_price_chart(data):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["날짜"], y=data["종가"], name="종가", line=dict(color="#4776e6", width=2.5)))
    fig.add_trace(go.Scatter(x=data["날짜"], y=data["20일 이동평균"], name="20일선", line=dict(color="#25b89a", width=1.7)))
    fig.add_trace(go.Scatter(x=data["날짜"], y=data["60일 이동평균"], name="60일선", line=dict(color="#f2a541", width=1.7)))
    fig.update_layout(height=350, margin=dict(l=8,r=8,t=18,b=8), paper_bgcolor="white", plot_bgcolor="white",
        font=dict(color="#536782"), legend=dict(orientation="h",y=1.12,x=0),
        xaxis=dict(showgrid=True,gridcolor="#edf1f7",title=""), yaxis=dict(showgrid=True,gridcolor="#edf1f7",title="원"))
    st.plotly_chart(fig, use_container_width=True)

def fetch_index_safely(api_id, keyword):
    if not krx_key:
        return None, "KRX_API_KEY가 등록되지 않았습니다."
    try:
        return krx_latest_index(krx_key, api_id, keyword), None
    except Exception as exc:
        return None, str(exc)

def fetch_samsung_safely():
    if not (kiwoom_key and kiwoom_secret):
        return None, "키움 App Key 또는 App Secret이 등록되지 않았습니다."
    try:
        return get_kiwoom_quote(kiwoom_key, kiwoom_secret, "005930"), None
    except Exception as exc:
        return None, str(exc)

def home():
    st.markdown('<div class="hero">안녕하세요, 이유진님!</div>', unsafe_allow_html=True)
    st.markdown('<div class="subhero">오늘도 차분하게 시장과 관심종목을 확인해 보세요. ☀️</div>', unsafe_allow_html=True)
    with st.spinner("API 연결 상태와 최신 데이터를 확인하고 있습니다..."):
        kospi, kospi_error = fetch_index_safely("kospi_dd_trd", "코스피")
        kosdaq, kosdaq_error = fetch_index_safely("kosdaq_dd_trd", "코스닥")
        samsung, samsung_error = fetch_samsung_safely()
    a,b,c = st.columns(3)
    a.metric("코스피", f"{kospi['value']:,.2f}" if kospi else "조회 실패",
             f"{kospi['date']} 기준" if kospi else "KRX 응답 확인 필요")
    b.metric("코스닥", f"{kosdaq['value']:,.2f}" if kosdaq else "조회 실패",
             f"{kosdaq['date']} 기준" if kosdaq else "KRX 응답 확인 필요")
    c.metric("삼성전자 · 키움 모의 API", f"{samsung['price']:,.0f}원" if samsung else "조회 실패",
             f"{samsung['change_pct']:+.2f}%" if samsung and samsung.get("change_pct") is not None else "키움 응답 확인 필요")
    errors = []
    if kospi_error: errors.append("코스피: " + kospi_error)
    if kosdaq_error: errors.append("코스닥: " + kosdaq_error)
    if samsung_error: errors.append("삼성전자: " + samsung_error)
    if errors:
        with st.expander("API 연결 오류 확인", expanded=True):
            for error in errors:
                st.warning(error)
            st.caption("인증키를 저장한 것만으로는 API 사용 승인이 보장되지 않습니다. 아래 설정 메뉴에서 키 상태를 확인하고, 키움 모의투자 키인지 확인하세요.")
    left,right = st.columns([0.9,1.6], gap="medium")
    with left:
        with st.container(border=True):
            section_title("관심종목", "현재가 조회 연결은 삼성전자부터 확인합니다.")
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
            section_title("삼성전자 주가 추이", "아래 차트는 아직 예시 데이터입니다. 실시간 현재가와는 별개입니다.")
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
    section_title("관심종목", "실제 현재가 연결 테스트는 삼성전자에 적용되어 있습니다.")
    with st.spinner("삼성전자 시세 조회 중..."):
        samsung, error = fetch_samsung_safely()
    price = f"{samsung['price']:,.0f}원" if samsung else "조회 실패"
    change = f"{samsung['change_pct']:+.2f}%" if samsung and samsung.get("change_pct") is not None else "—"
    st.dataframe(pd.DataFrame([
        ["삼성전자","005930","반도체",price,change],
        ["SK하이닉스","000660","반도체","추가 연결 필요","—"],
        ["한미반도체","042700","반도체 장비","추가 연결 필요","—"],
        ["HD현대일렉트릭","267260","전력기기","추가 연결 필요","—"],
        ["두산에너빌리티","034020","에너지","추가 연결 필요","—"],
    ],columns=["종목명","종목코드","산업","현재가","등락률"]),hide_index=True,use_container_width=True)
    if error: st.error(error)
    st.caption("삼성전자 이외의 종목은 아직 실시간 시세 연결 전입니다.")

def market():
    section_title("시장지수", "KRX Open API의 최근 제공 일별 시세")
    with st.spinner("KRX 지수를 조회하고 있습니다..."):
        kospi, e1 = fetch_index_safely("kospi_dd_trd", "코스피")
        kosdaq, e2 = fetch_index_safely("kosdaq_dd_trd", "코스닥")
    a,b=st.columns(2)
    a.metric("코스피", f"{kospi['value']:,.2f}" if kospi else "조회 실패", f"{kospi['date']} 기준" if kospi else "오류 상세 아래 확인")
    b.metric("코스닥", f"{kosdaq['value']:,.2f}" if kosdaq else "조회 실패", f"{kosdaq['date']} 기준" if kosdaq else "오류 상세 아래 확인")
    if e1: st.error("코스피: " + e1)
    if e2: st.error("코스닥: " + e2)
    st.caption("KRX Open API는 서비스 승인 상태와 제공 시점에 따라 당일 데이터가 아직 없을 수 있습니다.")

def chart_page():
    section_title("차트 분석")
    choice = st.selectbox("종목 선택",["삼성전자","SK하이닉스","한미반도체","HD현대일렉트릭","두산에너빌리티"])
    period = st.selectbox("조회 기간",["최근 6개월","최근 3개월","최근 1개월"])
    count = {"최근 6개월":len(df),"최근 3개월":65,"최근 1개월":22}[period]
    st.caption(f"{choice} · {period} · 예시 데이터(실제 과거 시세 연결 전)")
    show_price_chart(df.tail(count))
    st.markdown("**차트 읽기**")
    st.write("20일 이동평균선은 단기 흐름, 60일 이동평균선은 중기 흐름을 살펴보는 참고 지표입니다. 단독 매매 신호로 사용하지 마세요.")

def settings():
    section_title("API 설정", "API 키는 코드나 GitHub가 아닌 Streamlit Secrets에만 저장합니다.")
    st.markdown("### Streamlit Community Cloud Secrets 형식")
    st.code('KIWOOM_APP_KEY = "키움 모의투자 App Key"\nKIWOOM_APP_SECRET = "키움 모의투자 App Secret"\nKRX_API_KEY = "KRX Open API 인증키"', language="toml")
    st.warning("실제 키와 Secret을 채팅이나 GitHub에 올리지 마세요.")
    st.markdown("### 키 등록 상태")
    st.write("키움 App Key:", "등록됨" if kiwoom_key else "미등록")
    st.write("키움 App Secret:", "등록됨" if kiwoom_secret else "미등록")
    st.write("KRX API Key:", "등록됨" if krx_key else "미등록")
    st.markdown("### 현재 연결 범위")
    st.write("- 키움증권 모의투자: 삼성전자 현재가 조회 시도")
    st.write("- KRX Open API: 코스피·코스닥 최근 제공 일별 지수 조회 시도")
    st.write("- 주가 과거 차트 및 나머지 관심종목: 아직 예시 데이터/미연결")
    st.caption("실패하면 홈 또는 시장지수 메뉴의 'API 연결 오류 확인'에 원인이 표시됩니다.")

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
st.caption("교육용 대시보드 · 예시 차트는 실제 투자 판단에 사용하지 마세요. 자동 주문 기능은 포함되어 있지 않습니다.")
