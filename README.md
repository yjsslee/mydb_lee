# 이유진의 주식 투자 대시보드

Streamlit 기반 주식 대시보드의 기본 시작 버전입니다.

## 현재 기능
- 홈 화면과 관심종목 목록
- 예시 주가 차트 및 20일·60일 이동평균선
- Streamlit Secrets 키 등록 여부 표시

## 중요
현재 차트는 화면 확인용 예시 데이터입니다. 실제 주가나 시장 지수가 아닙니다. KRX 지수와 키움증권 시세 API는 다음 단계에서 각각 연결하고 테스트합니다.

## 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Secrets
```toml
KIWOOM_APP_KEY = "발급받은_키움_모의투자_APP_KEY"
KIWOOM_APP_SECRET = "발급받은_키움_모의투자_APP_SECRET"
KRX_API_KEY = "발급받은_KRX_API_KEY"
```

API 키와 Secret을 GitHub 코드에 직접 입력하지 마세요.
