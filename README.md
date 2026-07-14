# 🏥 Medical Underwriting AI — 파일럿 시리즈

> 보험 언더라이팅과 의료 AI의 교차점을 직접 설계·구현하는 파일럿 프로젝트 시리즈

## 시리즈 개요

18년간의 임상·언더라이팅 도메인 지식을 바탕으로, LLM·RAG·Agent 기술을 보험 실무에 적용하는 과정을 단계별로 기록한다. 각 파일럿은 이전 파일럿의 한계에서 출발하며, 기획 → 실행 → 오류 → 개선 → 인사이트의 구조로 문서화된다.

## 파일럿 목록

| # | 주제 | 핵심 기술 | 상태 |
|---|---|---|---|
| 01 | RAG를 활용한 지식 플랫폼 구축 | LangChain · FAISS · Groq API | ✅ 완료 |
| 02 | 지식 구조화 방안 설계 | 메타데이터 설계 · 동적 라우팅 | 🔜 예정 |

## 파일럿 간 연결고리

```
[Pilot 01] RAG 기본 파이프라인 구축
    ↓ 한계 발견: 단순 청크만으로는 정확도 낮음
    ↓ 인사이트: 지식 구조화가 선결 조건
[Pilot 02] 지식 구조화 방안 설계
    ↓ 메타데이터 태깅 · 버전 관리 · 맥락 데이터화
    ↓ ...
```

## 공통 기술 스택

```
언어      : Python 3.12
개발 환경 : Google Colab (무료)
LLM       : Groq API (Llama 3.3 70B)
임베딩    : jhgan/ko-sroberta-multitask
벡터 DB   : FAISS
프레임워크 : LangChain LCEL
```

## 디렉토리 구조

```
underwriting-rag-pilot/
├── README.md                        # 전체 시리즈 소개 (현재 파일)
├── pilot-01-rag-basic/              # Pilot 01
│   ├── README.md
│   ├── 01_planning.md
│   ├── 02_execution.md
│   ├── 03_errors_and_fixes.md
│   ├── 04_improvements.md
│   └── 05_final_output.md
└── pilot-02-knowledge-structure/    # Pilot 02 (예정)
    └── README.md
```
