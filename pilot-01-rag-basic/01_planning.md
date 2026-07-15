# 01. 기획

## 배경 및 동기


주요 업무:
- 의료 데이터를 활용한 AI/ML 기반 기능 설계 및 개발
- LLM 기반 AI Agent와 Multi-Agent 시스템 구조 설계
- RAG 검색·추론 파이프라인 구축 및 고도화
- LangChain, LangGraph, ADK 등 Agentic AI 프레임워크 기반 Tool Calling, Sub-Agent, Workflow Orchestration 개발

자격요건:
- AI/LLM 관련 연구 또는 개발 경험
- Python으로 데이터 처리, API 연동, 서비스 개발 경험
- LLM API, Prompt Engineering, RAG, Tool Calling에 대한 이해
- LangChain, LangGraph 등 AI Agent 프레임워크 활용 경험

### 파일럿 프로젝트 설정 이유
- JD 요구사항을 직접 경험으로 채우기 위한 핸즈온 파일럿
- 18년간의 임상·언더라이팅 도메인 지식을 LLM과 결합
- 기술자가 할 수 없는 부분(도메인 설계)을 직접 담당하여 차별화

---

## 목표 정의

### 최종 목표
> 의료 문서를 기반으로 보험 언더라이터의 판단을 지원하는 RAG 질의응답 시스템 구축

### 범위 설정
- 1차 파일럿: 기존 보유 SCOR 세미나 PDF 15개를 지식 베이스로 활용
- 질의 형태: 자유 텍스트 질문 입력 → 언더라이팅 형식 답변 출력
- UI: Google Colab 내 인터랙티브 위젯

---

## 기술 스택 선정 과정

### 후보 검토

| LLM API | 검토 결과 |
|---|---|
| ChatGPT (OpenAI) | 유료 — 카드 등록 필요 |
| Google Gemini | 한국 지역 제한으로 API 사용 불가 |
| **Groq (Llama 3.3 70B)** | ✅ 무료, 카드 불필요, 한국 사용 가능 |

| 임베딩 | 검토 결과 |
|---|---|
| OpenAI Embedding | 유료 |
| **jhgan/ko-sroberta-multitask** | ✅ 무료, 한국어 특화, HuggingFace 로컬 |

| 벡터 DB | 검토 결과 |
|---|---|
| Pinecone | 유료 (무료 티어 제한) |
| Chroma | 설치 복잡 |
| **FAISS** | ✅ 무료, 로컬, pip 설치 |

| UI | 검토 결과 |
|---|---|
| Streamlit + ngrok | ngrok 계정 필요 → 실패 |
| Streamlit + localtunnel | 타임아웃 오류 → 실패 |
| Streamlit + 코랩 포트 | 404 오류 → 실패 |
| **ipywidgets** | ✅ 코랩 내장, 외부 접속 불필요 |

### 최종 선정 스택
```
LLM         : Groq API (llama-3.3-70b-versatile)
임베딩      : jhgan/ko-sroberta-multitask
벡터 DB     : FAISS
오케스트레이션 : LangChain LCEL
UI          : ipywidgets
개발 환경   : Google Colab (무료)
```

---

## RAG 시스템 설계

### 질문 → 답변 플로우

```
[사용자 입력]
    "GLP-1 수용체 작용제 복용 환자의 언더라이팅 고려사항은?"
        ↓
[1단계: 키워드 필터링]
    질문에서 키워드 추출 → 관련 PDF 그룹 선택
        ↓
[2단계: 벡터 유사도 검색]
    FAISS에서 상위 k=4 청크 검색
        ↓
[3단계: 프롬프트 구성]
    검색된 청크 + 질문 → 언더라이팅 특화 프롬프트
        ↓
[4단계: LLM 답변 생성]
    Groq Llama → 구조화된 답변 출력
        ↓
[출력 형식]
    1. 핵심 요약
    2. 언더라이팅 관련 위험 요소
    3. 추가 확인 필요 항목
```

### 키워드-문서 매핑 설계

| 입력 키워드 | 검색 대상 문서 |
|---|---|
| glp, 당뇨, 비만 | GLP-1 관련 PDF |
| ckm | CKM 증후군 PDF |
| masld, 대사 | MASLD PDF |
| 심혈관 | 심혈관질환 PDF |
| 대장암 | 대장암 PDF |
| 전립선 | 전립선암 PDF |
| 알츠하이머, 치매 | AD PDF |
| ltc | LTC PDF |

### 언더라이팅 특화 프롬프트 설계 원칙
1. 역할 명시: "보험 언더라이터를 돕는 의료 정보 어시스턴트"
2. 관련성 강조: "질문과 직접 관련된 내용만 사용"
3. 구조화 출력: 핵심 요약 / 위험 요소 / 추가 확인 항목
4. 한계 명시: "관련 내용 부족 시 명시"
