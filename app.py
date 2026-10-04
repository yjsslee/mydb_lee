import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import date, timedelta

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
page = st.sidebar.radio("메뉴", ["홈", "차트 보기", "시장지수", "API 설정"])
st.title("이유진의 주식 투자 대시보드")

def secret(name):
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""

KIWOOM_KEY = secret("KIWOOM_APP_KEY")
KIWOOM_SECRET = secret("KIWOOM_APP_SECRET")
KRX_KEY = secret("KRX_API_KEY")

def parse_num(v):
    if v is None: return None
    try:
        return abs(float(str(v).strip().replace(",", "").replace("+", "")))
    except (TypeError, ValueError):
        return None

@st.cache_data(ttl=300, show_spinner=False)
def kiwoom_token(appkey, appsecret):
    r = requests.post(
        "https://mockapi.kiwoom.com/oauth2/token",
        json={"grant_type":"client_credentials","appkey":appkey,"secretkey":appsecret},
        headers={"Content-Type":"application/json;charset=UTF-8"},
        timeout=20,
    )
    if not r.ok:
        raise RuntimeError(f"키움 토큰 발급 실패(HTTP {r.status_code}): {r.text[:200]}")
    data = r.json()
    if data.get("return_code", 0) not in (0, "0", None):
        raise RuntimeError(f"키움 토큰 발급 실패: {data.get('return_msg', data)}")
    token = data.get("token") or data.get("access_token")
    if not token: raise RuntimeError(f"토큰 응답에서 token을 찾지 못했습니다: {list(data.keys())}")
    return token

def kiwoom_post(tr_code, body):
    if not KIWOOM_KEY or not KIWOOM_SECRET:
        raise RuntimeError("KIWOOM_APP_KEY 또는 KIWOOM_APP_SECRET이 Secrets에 없습니다.")
    token = kiwoom_token(KIWOOM_KEY, KIWOOM_SECRET)
    r = requests.post(
        "https://mockapi.kiwoom.com/api/dostk/" + ("stkinfo" if tr_code == "ka10001" else "chart"),
        json=body,
        headers={
            "Content-Type":"application/json;charset=UTF-8",
            "authorization":f"Bearer {token}",
            "api-id":tr_code,
        },
        timeout=20,
    )
    if not r.ok:
        raise RuntimeError(f"키움 {tr_code} 조회 실패(HTTP {r.status_code}): {r.text[:240]}")
    data = r.json()
    if data.get("return_code", 0) not in (0, "0", None):
        raise RuntimeError(f"키움 {tr_code} 오류: {data.get('return_msg', data)}")
    return data

@st.cache_data(ttl=60, show_spinner=False)
def get_quote(stock_code):
    data = kiwoom_post("ka10001", {"stk_cd":stock_code})
    price = parse_num(data.get("cur_prc"))
    if price is None:
        raise RuntimeError(f"현재가 필드(cur_prc)가 응답에 없습니다. 응답 필드: {', '.join(data.keys())}")
    pct = None
    try: pct = float(str(data.get("flu_rt","")).replace("%","").replace("+",""))
    except (TypeError, ValueError): pass
    return {"price":price,"pct":pct,"name":data.get("stk_nm",stock_code)}

@st.cache_data(ttl=300, show_spinner=False)
def get_daily_chart(stock_code, days=190):
    data = kiwoom_post("ka10081", {
        "stk_cd":stock_code,
        "base_dt":date.today().strftime("%Y%m%d"),
        "upd_stkpc_tp":"1",
    })
    rows = None
    for k,v in data.items():
        if isinstance(v,list) and v and isinstance(v[0],dict):
            rows = v
            break
    if not rows:
        raise RuntimeError(f"일봉 응답에서 데이터 목록을 찾지 못했습니다. 응답 필드: {', '.join(data.keys())}")
    frame = pd.DataFrame(rows)
    date_col = next((x for x in ["dt","date","日期","stk_dt","trd_dt"] if x in frame.columns), None)
    close_col = next((x for x in ["cur_prc","close","cls_prc","close_pric"] if x in frame.columns), None)
    if date_col is None or close_col is None:
        raise RuntimeError(f"일봉 응답의 날짜/종가 필드를 찾지 못했습니다. 응답 필드: {', '.join(frame.columns)}")
    frame["날짜"] = pd.to_datetime(frame[date_col].astype(str), format="%Y%m%d", errors="coerce")
    frame["종가"] = pd.to_numeric(frame[close_col].astype(str).str.replace(",","").str.replace("+",""), errors="coerce").abs()
    frame = frame.dropna(subset=["날짜","종가"]).sort_values("날짜").tail(days)
    if frame.empty: raise RuntimeError("키움 일봉 데이터가 비어 있습니다.")
    frame["20일 이동평균"] = frame["종가"].rolling(20).mean()
    frame["60일 이동평균"] = frame["종가"].rolling(60).mean()
    return frame[["날짜","종가","20일 이동평균","60일 이동평균"]]

@st.cache_data(ttl=3600, show_spinner=False)
def get_krx_index(api_id, label):
    if not KRX_KEY: raise RuntimeError("KRX_API_KEY가 Secrets에 없습니다.")
    url = f"https://data-dbg.krx.co.kr/svc/apis/idx/{api_id}"
    notes = []
    # 일별 데이터라 주말/공휴일을 고려해 최근 15일을 탐색합니다.
    for offset in range(15):
        d = date.today() - timedelta(days=offset)
        r = requests.get(url, params={"basDd":d.strftime("%Y%m%d")},
                         headers={"AUTH_KEY":KRX_KEY,"Accept":"application/json"}, timeout=20)
        if r.status_code in (401,403):
            raise RuntimeError(f"KRX 인증 거부(HTTP {r.status_code}). 인증키 발급 및 해당 API 활용 신청/승인을 확인하세요.")
        if not r.ok:
            notes.append(f"HTTP {r.status_code}: {r.text[:100]}")
            continue
        try: payload = r.json()
        except ValueError:
            notes.append("JSON이 아닌 응답: " + r.text[:100])
            continue
        rows = payload if isinstance(payload,list) else None
        if isinstance(payload,dict):
            for key in ("OutBlock_1","output","data","items","result"):
                if isinstance(payload.get(key),list):
                    rows = payload[key]
                    break
            if not rows:
                msg = payload.get("respMsg") or payload.get("return_msg") or payload.get("message")
                code = payload.get("respCode") or payload.get("return_code") or payload.get("code")
                if msg or code: notes.append(f"응답코드={code}, 메시지={msg}")
                else: notes.append("응답 필드=" + ", ".join(payload.keys()))
                continue
        if not rows: continue
        # KRX 지수 API는 IDX_NM, CLSPRC_IDX, BAS_DD 필드를 제공합니다.
        match = next((x for x in rows if label in str(x.get("IDX_NM",""))), None)
        if match is None:
            # 응답 목록에 대표 지수 외 여러 지수가 있으면 KOSPI/KOSDAQ 명칭을 우선 선택합니다.
            match = next((x for x in rows if label.upper() in str(x.get("IDX_NM","")).upper()), rows[0])
        value = parse_num(match.get("CLSPRC_IDX"))
        if value is not None:
            return {"value":value,"date":match.get("BAS_DD",d.strftime("%Y%m%d"))}
        notes.append("종가 필드 없음. 응답 필드=" + ", ".join(match.keys()))
    raise RuntimeError("KRX 데이터를 찾지 못했습니다. 마지막 응답: " + (notes[-1] if notes else "최근 15일 자료 없음") + ". KRX 사이트에서 지수 API 활용 승인을 확인하세요.")

@st.cache_data
def demo_prices():
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=130)
    rng = np.random.default_rng(7)
    close = 70000 + np.cumsum(rng.normal(0,450,len(dates)))
    df = pd.DataFrame({"날짜":dates,"종가":close})
    df["20일 이동평균"] = df["종가"].rolling(20).mean()
    df["60일 이동평균"] = df["종가"].rolling(60).mean()
    return df

def draw_chart(df):
    fig = go.Figure()
    for col in ["종가","20일 이동평균","60일 이동평균"]:
        fig.add_trace(go.Scatter(x=df["날짜"],y=df[col],mode="lines",name=col))
    fig.update_layout(height=430,margin=dict(l=10,r=10,t=25,b=10),paper_bgcolor="white",
        plot_bgcolor="white",hovermode="x unified",legend=dict(orientation="h",y=1.12,x=0),
        xaxis=dict(title="",showgrid=True,gridcolor="#edf1f7"),
        yaxis=dict(title="가격(원)",showgrid=True,gridcolor="#edf1f7"))
    st.plotly_chart(fig,use_container_width=True)

def index_metric(api_id, label):
    try:
        result = get_krx_index(api_id,label)
        st.metric(label, f"{result['value']:,.2f}", f"{result['date']} 기준")
        return None
    except Exception as e:
        st.metric(label,"조회 실패","오류 상세 아래 확인")
        return str(e)

if page == "홈":
    a,b,c = st.columns(3)
    with a:
        e1 = index_metric("kospi_dd_trd","코스피")
    with b:
        e2 = index_metric("kosdaq_dd_trd","코스닥")
    with c:
        try:
            q = get_quote("005930")
            st.metric("삼성전자 · 키움 모의 API",f"{q['price']:,.0f}원",f"{q['pct']:+.2f}%" if q["pct"] is not None else "키움 현재가")
            e3 = None
        except Exception as e:
            st.metric("삼성전자 · 키움 모의 API","조회 실패")
            e3 = str(e)
    for title, err in [("코스피",e1),("코스닥",e2),("삼성전자",e3)]:
        if err:
            with st.expander(f"{title} API 오류",expanded=(title=="삼성전자")): st.error(err)
    left,right=st.columns([1,2])
    with left:
        st.subheader("관심종목")
        st.dataframe(pd.DataFrame([["삼성전자","005930"],["SK하이닉스","000660"],["한미반도체","042700"],["HD현대일렉트릭","267260"],["두산에너빌리티","034020"]],columns=["종목명","종목코드"]),hide_index=True,use_container_width=True)
    with right:
        st.subheader("삼성전자 주가 추이")
        try:
            chart = get_daily_chart("005930",190)
            st.caption("키움증권 API 실제 일봉 데이터")
        except Exception as e:
            st.warning("실제 일봉 조회에 실패해 예시 차트를 표시합니다. 아래 오류를 확인하세요.")
            with st.expander("일봉 API 오류"): st.error(str(e))
            chart = demo_prices()
            st.caption("예시 데이터 · 실제 주가가 아닙니다.")
        draw_chart(chart)

elif page == "차트 보기":
    stocks = {"삼성전자":"005930","SK하이닉스":"000660","한미반도체":"042700","HD현대일렉트릭":"267260","두산에너빌리티":"034020"}
    name = st.selectbox("종목 선택",list(stocks.keys()))
    period = st.selectbox("조회 기간",["최근 1개월","최근 3개월","최근 6개월"])
    try:
        chart = get_daily_chart(stocks[name],190)
        n = {"최근 1개월":22,"최근 3개월":65,"최근 6개월":130}[period]
        st.caption(f"{name} · 키움증권 실제 일봉 데이터 · {period}")
        draw_chart(chart.tail(n))
        st.dataframe(chart.tail(10).round(2),hide_index=True,use_container_width=True)
    except Exception as e:
        st.error(f"{name} 일봉 조회에 실패했습니다: {e}")
        st.info("현재는 실제 데이터 조회에 성공한 경우에만 실제 차트를 표시합니다. 홈 화면의 삼성전자 예시 차트와 혼동하지 마세요.")

elif page == "시장지수":
    st.subheader("KRX 시장지수")
    a,b=st.columns(2)
    with a:
        e1=index_metric("kospi_dd_trd","코스피")
        if e1: st.error(e1)
    with b:
        e2=index_metric("kosdaq_dd_trd","코스닥")
        if e2: st.error(e2)
    st.caption("KRX 지수 API는 일별 데이터이며, 당일 장중 실시간 지수와 다를 수 있습니다.")

else:
    st.subheader("API 설정")
    st.write("아래 이름을 Streamlit Cloud → 앱 Settings → Secrets에 등록합니다.")
    st.code('KIWOOM_APP_KEY = "발급받은_키움_모의투자_APP_KEY"\nKIWOOM_APP_SECRET = "발급받은_키움_모의투자_APP_SECRET"\nKRX_API_KEY = "발급받은_KRX_API_KEY"',language="toml")
    for label,key in [("키움 App Key","KIWOOM_APP_KEY"),("키움 App Secret","KIWOOM_APP_SECRET"),("KRX API Key","KRX_API_KEY")]:
        st.write(label + ":", "등록됨" if secret(key) else "미등록")
    st.warning("키 등록 여부와 API 호출 성공은 다릅니다. 홈과 시장지수 메뉴에 표시되는 오류 상세를 확인하세요.")
    st.caption("키와 Secret을 GitHub에 직접 저장하지 마세요.")

st.divider()
st.caption("투자 교육용 앱 · API 오류 시 원문 일부를 표시합니다. 실제 거래 주문 기능은 없습니다.")
