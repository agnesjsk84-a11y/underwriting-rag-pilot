# 01. 기획 — 지식 구조화 기반 RAG 플랫폼

## Pilot 01에서 출발한 이유

Pilot 01을 통해 단순 청크 기반 RAG의 한계를 직접 경험했다.

| Pilot 01 한계 | Pilot 02 해결 방향 |
|---|---|
| 단순 청크 분할 → 문서 혼재 | 메타데이터 태깅 → 정교한 필터링 |
| 파일명 키워드 필터링 → 규칙 기반 한계 | 스키마 기반 구조화 → 확장 가능 |
| 출처 없는 답변 | 근거 + 페이지 + 버전 함께 출력 |
| 버전 혼재 | 문서 버전 관리 체계 설계 |
| 맥락 없는 검색 | disease / stage / drug 등 컨텍스트 태깅 |

---

## 목표

> **PDF 한 개를 올리면, 메타데이터와 함께 출처가 표시된 답변이 나오는 RAG**

- 질환: 당뇨병 (단일 질환으로 시작)
- 문서: 대한당뇨병학회 진료지침 2023
- 핵심: 구조화된 지식 스키마 + ChromaDB 메타데이터 필터링

---

## 지식 스키마 설계

### 질환 문서 구조 (Disease Schema)

Wikipedia/Medscape의 정보 구조를 참고하여 의료 지식의 표준 목차를 설계한다.
단, 콘텐츠를 복사하는 것이 아니라 **구조만 차용**한다.

```
diabetes/
├── 01_definition.md         # 정의 · 분류
├── 02_epidemiology.md       # 역학 · 유병률
├── 03_risk_factors.md       # 위험요인
├── 04_diagnosis.md          # 진단 기준 · HbA1c
├── 05_severity.md           # 중증도 · 조절 등급
├── 06_treatment.md          # 치료 단계 · 약물
├── 07_complications.md      # 합병증
├── 08_prognosis.md          # 예후
└── 09_underwriting.md       # 언더라이팅 연결
```

### 메타데이터 스키마 설계

각 청크에 다음 메타데이터를 사전에 태깅한다.

```yaml
# 기본 메타데이터
disease: diabetes
disease_type: type2
section: treatment          # definition / diagnosis / treatment / complications 등
subsection: GLP-1           # 세부 주제

# 근거 메타데이터
guideline: KDA_2023         # 출처 가이드라인
version: 2023               # 버전
source: 대한당뇨병학회
source_type: guideline      # guideline / paper / policy / textbook
page: 45                    # 원문 페이지
evidence_level: A           # 근거 수준 (A/B/C)

# 임상 메타데이터
population: type2_diabetes  # 대상 환자군
intervention: GLP-1         # 중재 (약물/검사/시술)
outcome: HbA1c_reduction    # 결과 지표
country: KR                 # 적용 국가

# 버전 관리
knowledge_id: KNO-DM-006
content_hash: ""            # 내용 해시 (변경 감지용)
last_reviewed: 2026-07-15
status: active              # active / superseded / archived
```

### 언더라이팅 연결 계층

임상 지식과 보험 판단을 별도 계층으로 분리한다.

```yaml
# 언더라이팅 메타데이터
underwriting_relevant: true
risk_factor: HbA1c_uncontrolled
risk_level: high            # low / moderate / high / decline
additional_check:
  - HbA1c 수치 확인
  - 합병증 동반 여부
  - 인슐린 사용 여부
insurance_impact:
  - 사망보험: 추가보험료 또는 부담보
  - 실손보험: 당뇨 합병증 부담보 가능
```

---

## 기술 스택 변경

| 항목 | Pilot 01 | Pilot 02 | 변경 이유 |
|---|---|---|---|
| 벡터 DB | FAISS | ChromaDB | 메타데이터 필터링 지원 |
| 청크 방식 | 단순 분할 | 섹션 기반 분할 | 문서 흐름 유지 |
| 임베딩 | jhgan/ko-sroberta | 동일 | 유지 |
| LLM | Groq Llama | 동일 | 유지 |
| 출처 표시 | 없음 | 근거 + 페이지 표시 | 신뢰도 향상 |

### ChromaDB를 선택한 이유

```
FAISS
- 장점: 빠름, 설치 간단
- 단점: 메타데이터 필터링 불가
        → disease="diabetes" AND section="treatment" 검색 불가

ChromaDB
- 장점: 메타데이터 필터링 지원
        → where={"disease": "diabetes", "section": "treatment"}
- 단점: FAISS보다 약간 느림 (파일럿 수준에서는 무관)
```

---

## 시스템 구조

```
[PDF 업로드]
        ↓
[섹션 기반 청크 분할]
  definition / diagnosis / treatment / complications
        ↓
[메타데이터 태깅]
  disease / section / guideline / version / page / evidence_level
        ↓
[ChromaDB 저장]
  벡터 + 메타데이터 함께 저장
        ↓
[질문 입력]
  "HbA1c 8% 이상 제2형 당뇨 환자 언더라이팅 고려사항은?"
        ↓
[메타데이터 필터링]
  disease=diabetes, section=treatment OR complications
        ↓
[유사도 검색 (k=4)]
        ↓
[LLM 답변 생성]
        ↓
[출력]
  1. 핵심 요약
  2. 언더라이팅 위험 요소
  3. 추가 확인 항목
  4. 근거 출처 (가이드라인명 + 페이지)
```

---

## MVP 범위 (2주 목표)

### 포함
- 당뇨병 진료지침 PDF 1개 구조화
- 메타데이터 스키마 설계 및 태깅
- ChromaDB 저장 및 메타데이터 필터링 검색
- 출처(가이드라인 + 페이지) 함께 출력
- ipywidgets UI (Pilot 01과 동일)

### 제외 (Version 2 이후)
- PubMed 자동 수집
- 다른 질환 추가
- 자동 업데이트 파이프라인
- 보험 Rule Engine

---

## Pilot 03 · 04 예고

### Pilot 03 — 외부 데이터 자동 수집
```
PubMed E-utilities API
        ↓
당뇨병 + GLP-1 검색식 자동 실행
        ↓
신규 논문 탐지 → 메타데이터 추출
        ↓
검수 대기 파일 생성
        ↓
사람 승인 → ChromaDB 업데이트
```

### Pilot 04 — 언더라이팅 Rule Engine 연결
```
임상 근거 검색 결과
        ↓
언더라이팅 판단 계층 연결
  위험 등급 / 추가 확인 항목 / 보험금 영향
        ↓
근거 + 언더라이팅 판단 통합 출력
```
