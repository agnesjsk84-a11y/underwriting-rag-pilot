# 🏥 언더라이팅 RAG Assistant — 파일럿 프로젝트

> 보험 언더라이터를 위한 의료 문서 기반 RAG(Retrieval-Augmented Generation) 질의응답 시스템

## 프로젝트 개요

| 항목 | 내용 |
|---|---|
| **목적** | 의료 문서를 벡터 DB로 구축하고 LLM으로 언더라이팅 관련 질의응답 제공 |
| **배경** | 카카오헬스케어 JD 기반 — RAG, LLM Agent, 의료 AI 실무 역량 파일럿 |
| **기간** | 2026년 7월 |
| **개발 환경** | Google Colab (무료) |
| **최종 스택** | Groq API + LangChain + FAISS + ipywidgets |

## 기술 스택

```
LLM         : Llama 3.3 70B (Groq API — 무료)
임베딩      : jhgan/ko-sroberta-multitask (한국어 특화)
벡터 DB     : FAISS (로컬)
오케스트레이션 : LangChain LCEL
UI          : ipywidgets (Google Colab 내장)
문서 로더   : PyPDFLoader
```

## 지식 베이스 (RAG 소스 문서)

| 파일명 | 주제 |
|---|---|
| GLP-1 치료제의 기대와 현실 | GLP-1 수용체 작용제 임상 및 언더라이팅 |
| CKM 증후군과 위험분류 | CKM 스테이징 및 위험 분류 |
| MASLD와 대사질환 | 대사 관련 간질환 |
| 심혈관질환 치료 최신동향 | 심혈관 위험 인자 |
| 대장암의 치료 | 대장암 치료 동향 |
| 전립선암 치료 동향 | 전립선암 최신 치료 |
| AD 2.0 생물학적 정의 및 치료 혁신 | 알츠하이머 질병수정치료제 |
| LTC | 장기간호 위험 |

총 **15개 PDF**, **217페이지**, **277청크** 벡터화 완료

## 시스템 구조

```
[사용자 질문 입력]
        ↓
[키워드 기반 문서 필터링]
  예: "GLP-1" → GLP-1 관련 PDF만 선택
        ↓
[FAISS 유사도 검색 (k=4)]
        ↓
[LangChain LCEL RAG 체인]
  - 문서 포맷팅
  - 프롬프트 구성
  - Groq LLM 호출
        ↓
[언더라이팅 형식 답변 출력]
  1. 핵심 요약
  2. 언더라이팅 관련 위험 요소
  3. 추가 확인 필요 항목
```

## 디렉토리 구조

```
rag-pilot-docs/
├── README.md                     # 프로젝트 전체 개요 (현재 파일)
├── docs/
│   ├── 01_planning.md            # 기획
│   ├── 02_execution.md           # 실행 과정
│   ├── 03_errors_and_fixes.md    # 오류 및 수정 내역
│   ├── 04_improvements.md        # 개선 내역
│   └── 05_final_output.md        # 최종 산출물 및 회고
└── notebooks/
    └── underwriting_rag.ipynb    # 최종 코랩 노트북
```

## 핵심 성과

- ✅ 무료 스택만으로 RAG 파이프라인 완성
- ✅ 한국어 특화 임베딩 적용
- ✅ 문서 혼재 문제 → 키워드 필터링으로 해결
- ✅ 코랩 내 인터랙티브 UI 구현

## 다음 단계 (TODO)

- [ ] 당뇨병 진료지침 PDF 추가
- [ ] 언더라이팅 기준 텍스트 직접 작성 및 추가
- [ ] Streamlit Cloud 배포
- [ ] 당뇨병 특화 Agent (HbA1c, 약물, 유병기간 입력 → 위험도 분류)
