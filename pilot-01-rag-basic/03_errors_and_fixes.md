# 03. 오류 및 수정 내역

## 오류 1 — LangChain Import 경로 변경

### 오류 메시지
```
ModuleNotFoundError: No module named 'langchain.document_loaders'
ModuleNotFoundError: No module named 'langchain.text_splitter'
ModuleNotFoundError: No module named 'langchain.chains'
```

### 원인
LangChain이 패키지 구조를 대폭 변경함
- 구버전: `langchain.document_loaders`, `langchain.chains` 등 통합 패키지
- 신버전: 기능별 분리 패키지로 이전

추가로 `langchain-community`도 deprecated 경고 발생:
```
DeprecationWarning: `langchain-community` is being sunset
```

### 수정 내역

| 구버전 (오류) | 신버전 (정상) |
|---|---|
| `from langchain.document_loaders import PyPDFLoader` | `from langchain_community.document_loaders import PyPDFLoader` |
| `from langchain.text_splitter import RecursiveCharacterTextSplitter` | `from langchain_text_splitters import RecursiveCharacterTextSplitter` |
| `from langchain.vectorstores import FAISS` | `from langchain_community.vectorstores import FAISS` |
| `from langchain.embeddings import HuggingFaceEmbeddings` | `from langchain_huggingface import HuggingFaceEmbeddings` |
| `from langchain.chains import RetrievalQA` | LCEL 방식으로 전환 |
| `from langchain.prompts import PromptTemplate` | `from langchain_core.prompts import PromptTemplate` |

### 핵심 교훈
> LangChain은 빠르게 업데이트되므로 항상 공식 문서의 최신 import 경로 확인 필요
> `RetrievalQA` 같은 구버전 체인 대신 LCEL(LangChain Expression Language) 방식 사용 권장

---

## 오류 2 — pip 의존성 충돌 경고

### 오류 메시지
```
ERROR: pip's dependency resolver does not currently take into account all the packages 
that are installed. google-colab 1.0.0 requires requests==2.32.4, 
but you have requests 2.34.2 which is incompatible.
```

### 원인
코랩 기본 패키지(`google-colab`)와 설치된 패키지(`requests`) 버전 충돌

### 처리 방법
**무시하고 진행** — 이 경고는 실행에 영향 없음
코랩 자체 패키지 충돌이며 실제 코드 실행에는 문제 없음

---

## 오류 3 — 런타임 재시작 시 파일 및 변수 초기화

### 현상
런타임 재시작 후:
1. 업로드한 PDF 파일 사라짐 (`/content/` 초기화)
2. API 키 환경변수 초기화 → `AuthenticationError: Invalid API Key`
3. 모든 변수 초기화 (vectorstore, llm, chunks 등)

### 오류 메시지
```
ValueError: File path /content/2023 당뇨병 진료지침_전문_240620.pdf is not a valid file or url
AuthenticationError: Error code: 401 - {'error': {'message': 'Invalid API Key'}}
```

### 수정 방법
1. **PDF는 구글 드라이브에 저장** → 런타임 재시작해도 유지
2. **노트북 맨 위에 API 키 설정 셀 고정** → 재시작 시 항상 먼저 실행
3. **셀 실행 순서 체크리스트 작성**

### 올바른 노트북 셀 순서
```
셀 1: 라이브러리 설치 (pip install)
셀 2: API 키 설정 ← 재시작 후 반드시 먼저 실행
셀 3: 구글 드라이브 마운트
셀 4: PDF 로드 + 벡터 DB 구축
셀 5: RAG 체인 구성
셀 6: UI 실행
```

---

## 오류 4 — Streamlit 외부 접속 실패 (3가지 시도)

### 시도 1: ngrok
```
PyngrokNgrokError: authentication failed — ngrok requires an account
ERR_NGROK_4018
```
**원인**: ngrok이 무료 사용 시 계정 인증 필수로 정책 변경

### 시도 2: localtunnel
```
TimeoutExpired: Command '['lt', '--port', '8501']' timed out after 10 seconds
```
**원인**: 코랩 네트워크 환경에서 localtunnel 연결 불안정

### 시도 3: 코랩 내장 포트 포워딩
```
HTTP ERROR 404
```
**원인**: 코랩 세션 끊김 시 포트 주소 변경됨, 재접속 불안정

### 최종 해결: ipywidgets
외부 접속 자체를 포기하고 **코랩 내에서 직접 실행**하는 방식으로 전환
- `ipywidgets`: 코랩 기본 내장 라이브러리
- 별도 서버 불필요
- 안정적으로 코랩 셀 내에서 UI 렌더링

---

## 오류 5 — RAG 문서 혼재 (핵심 품질 문제)

### 현상
"GLP-1 수용체 작용제" 질문에 **알츠하이머(AD)** 문서 내용이 답변에 포함됨

```
질문: GLP-1 수용체 작용제 복용 환자의 언더라이팅 시 주요 고려사항은?

오답 답변 예시:
"ARIA-E 및 ARIA-H 중증도에 따라 투약 중단 여부가 결정된다"
→ 이는 레카네맙(알츠하이머 치료제) 내용
```

### 원인 진단
```python
# 실제 검색된 청크 확인
docs = retriever.invoke(query)
for doc in docs:
    print(doc.metadata.get('source'))
```

**결과**:
```
청크 1: 13_[최종] GLP-1 치료제의 기대와 현실.pdf  ← 정상
청크 2: 15_AD 2.0 생물학적 정의 및 치료 혁신.pdf  ← 오류
청크 3: 15_AD 2.0 생물학적 정의 및 치료 혁신.pdf  ← 오류
청크 4: 15_AD 2.0 생물학적 정의 및 치료 혁신.pdf  ← 오류
청크 5: 15_AD 2.0 생물학적 정의 및 치료 혁신.pdf  ← 오류
```

**근본 원인**: FAISS 벡터 유사도 검색이 GLP-1 문서보다 AD 문서를 더 관련있다고 판단
→ 문서 볼륨 차이 (AD 문서가 더 크고 청크 수 많음) + 임베딩 공간에서의 벡터 유사도 문제

### 수정 시도 1: 프롬프트 개선 → 효과 미미
```python
# 프롬프트에 추가
"질문과 직접 관련없는 내용은 무시하고 답변하세요."
"참고 문서 관련성 (상/중/하) 평가 추가"
```
→ 여전히 AD 내용 혼재. LLM이 제공된 컨텍스트를 무시하지 못함

### 수정 시도 2: 검색 개수 증가 (k=3→5) → 효과 없음
더 많은 청크를 가져와도 AD 문서 비율이 높아 오히려 악화

### 최종 해결: 키워드 기반 문서 필터링 ✅
```python
TOPIC_MAP = {
    "glp": "GLP-1",
    "당뇨": "GLP-1",
    "ckm": "CKM",
    ...
}

def get_filtered_retriever(query):
    # 질문 키워드로 관련 문서 그룹 선택
    # 해당 그룹의 청크만으로 별도 FAISS 인덱스 생성
    # 그 안에서만 유사도 검색
```

**결과**: GLP-1 질문 시 GLP-1 문서만 검색 → AD 내용 완전 제거 ✅

### 핵심 교훈
> RAG에서 검색 정확도는 프롬프트보다 **검색 단계(Retrieval)** 에서 결정된다.
> 문서 종류가 다양할 때는 메타데이터 필터링이 필수.
> "Garbage in, Garbage out" — LLM이 좋아도 잘못된 컨텍스트가 들어오면 답변이 틀린다.
