# 03. 로드맵 — Pilot 03 · 04 설계

## Pilot 03 — 외부 데이터 자동 수집

### 목표
> PubMed에서 새 논문을 자동 탐지하고 검수 대기열을 생성한다.
> **자동 반영이 아니라 사람이 검수 후 승인**하는 구조.

### 핵심 원칙
```
자동 수행 (시스템)          사람 수행 (지수씨)
─────────────────          ──────────────────
변경 감지                   근거 수준 판단
원문 다운로드               지식 통합
메타데이터 추출             보험 영향 해석
기존 버전과 비교            최종 승인
변경 요약 초안 생성
검수 대기열 생성
```

### 시스템 구조

```
[PubMed E-utilities API]
  검색식: "diabetes"[MeSH] AND "GLP-1"[Title]
  주기: 매일 오전 6시
        ↓
[신규 PMID 감지]
  기존 저장 PMID와 비교
  새로운 것만 처리
        ↓
[메타데이터 추출]
  제목 / 저자 / 출판일 / 초록 / DOI
        ↓
[LLM 요약 초안 생성]
  언더라이팅 관련성 점수
  영향 가능 섹션 제안
        ↓
[검수 대기 파일 생성]
  /review_queue/UPD-20260715-001.md
        ↓
[사람 승인]
        ↓
[ChromaDB 업데이트]
  변경된 청크만 재임베딩
```

### PubMed 수집 코드 설계

```python
import requests
from datetime import date, timedelta

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

def search_new_pubmed(query: str, days_back: int = 1) -> list:
    """신규 PubMed 논문 검색"""
    today = date.today()
    from_date = (today - timedelta(days=days_back)).strftime("%Y/%m/%d")

    search_url = f"{PUBMED_BASE}/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": f"{query} AND {from_date}[Date - Publication]:3000[Date - Publication]",
        "retmode": "json",
        "retmax": 50
    }
    response = requests.get(search_url, params=params)
    pmids = response.json()["esearchresult"]["idlist"]
    return pmids

def fetch_pubmed_details(pmids: list) -> list:
    """논문 상세 정보 가져오기"""
    fetch_url = f"{PUBMED_BASE}/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml"
    }
    response = requests.get(fetch_url, params=params)
    # XML 파싱 후 반환
    return parse_pubmed_xml(response.text)

def detect_new_papers(query: str, existing_pmids: set) -> list:
    """기존 PMID와 비교하여 신규만 반환"""
    current_pmids = set(search_new_pubmed(query))
    new_pmids = current_pmids - existing_pmids
    return list(new_pmids)
```

### 검수 대기 파일 형식

```markdown
---
update_id: UPD-20260715-001
source: PubMed
pmid: 39876543
status: pending_review
detected_at: 2026-07-15
relevance_score: 0.87
affected_sections:
  - treatment
  - complications
---

## 논문 정보
- 제목: Cardiovascular outcomes of GLP-1 receptor agonists in T2DM
- 저자: Kim et al.
- 출판일: 2026-07-10
- DOI: 10.1234/diabetes.2026.001

## LLM 요약 초안
GLP-1 수용체 작용제가 제2형 당뇨병 환자의 심혈관 사건을 27% 감소시킨다는 
대규모 RCT 결과. SGLT2 억제제와의 병용 효과도 확인됨.

## 언더라이팅 관련성
- 관련 섹션: treatment, complications
- 영향 가능 위험 인자: 심혈관 합병증
- 보험 영향: 심혈관 위험 등급 재평가 필요 가능성

## 검수 항목
- [ ] 원문 확인
- [ ] 기존 지식과 비교
- [ ] 근거 수준 판단
- [ ] 보험 해석 수정 여부
- [ ] ChromaDB 업데이트 승인
```

### GitHub Actions 자동화

```yaml
# .github/workflows/update_knowledge.yml
name: Medical Knowledge Update
on:
  schedule:
    - cron: "0 6 * * *"   # 매일 오전 6시 UTC
  workflow_dispatch:        # 수동 실행 가능

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python pipelines/check_pubmed.py
      - run: python pipelines/build_review_queue.py
      - name: Commit review queue
        run: |
          git config user.email "auto@pilot.com"
          git config user.name "Knowledge Bot"
          git add review_queue/
          git commit -m "auto: 신규 논문 검수 대기열 생성 $(date)"
          git push
```

### 버전 관리 상태값

```
new           → 신규 탐지, 미검토
pending_review → 검수 대기 중
active        → 승인 완료, 현재 사용 중
superseded    → 더 최신 버전으로 대체됨
archived      → 보관 (삭제 안 함)
withdrawn     → 오류·철회로 사용 불가
```

---

## Pilot 04 — 언더라이팅 Rule Engine 연결

### 목표
> 임상 근거 검색 결과에 언더라이팅 판단 계층을 연결한다.
> "Stage IB EGFR 양성 환자는?" → 임상 근거 + 언더라이팅 판단 통합 출력

### 지식 계층 구조

```
Source (원문)
  SRC-KDA-2023
       ↓
Evidence (근거)
  EVD-HbA1c-001: "HbA1c 9% 초과 시 합병증 위험 증가"
       ↓
Knowledge (지식)
  KNO-DM-SEVERITY: "HbA1c 기반 조절 등급 분류"
       ↓
Underwriting Application (언더라이팅 적용)
  APP-UW-DM-001: "HbA1c 9% 초과 → 추가보험료 또는 부담보 검토"
```

### 언더라이팅 Rule 설계

```python
UNDERWRITING_RULES = {
    "diabetes": {
        "HbA1c_control": {
            "good": {           # HbA1c < 7%
                "risk_level": "standard",
                "additional_check": ["유병기간", "합병증 여부"],
                "insurance_impact": "표준체 가능"
            },
            "moderate": {       # HbA1c 7~9%
                "risk_level": "substandard",
                "additional_check": [
                    "HbA1c 최근 추이",
                    "약물 단계",
                    "합병증 동반 여부"
                ],
                "insurance_impact": "추가보험료 또는 조건부 승인"
            },
            "poor": {           # HbA1c > 9%
                "risk_level": "high",
                "additional_check": [
                    "인슐린 사용 여부",
                    "심혈관 합병증",
                    "신기능 (eGFR)",
                    "안저검사 결과"
                ],
                "insurance_impact": "거절 또는 합병증 부담보 조건"
            }
        },
        "treatment_stage": {
            "oral_single": {"risk_level": "low"},
            "oral_multiple": {"risk_level": "moderate"},
            "insulin": {"risk_level": "high"}
        },
        "complications": {
            "none": {"risk_level": "low"},
            "microvascular": {"risk_level": "moderate"},
            "macrovascular": {"risk_level": "high"},
            "both": {"risk_level": "decline_review"}
        }
    }
}
```

### 통합 출력 형식

```
질문: HbA1c 8.5%, metformin + GLP-1 복용 중인 제2형 당뇨 환자

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 임상 근거
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HbA1c 8.5%는 조절 불량 범위(>8%)에 해당하며
심혈관 및 미세혈관 합병증 위험이 증가한다.
[KDA_2023 p.45 | 근거수준: A]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 언더라이팅 판단
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
위험 등급: Substandard (추가보험료 검토)
치료 단계: 경구 2제 이상 → 중등도 위험

📌 추가 확인 필요 항목:
1. HbA1c 최근 6개월 추이
2. 합병증 동반 여부 (망막/신장/신경)
3. 심혈관질환 과거력
4. 인슐린 전환 가능성

💊 보험 영향:
- 사망보험: 추가보험료 또는 당뇨 합병증 부담보
- 실손보험: 당뇨 관련 질환 부담보 가능

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 참고 출처
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[KDA_2023 p.45 | 근거수준: A]
[KDA_2023 p.78 | 근거수준: B]
```

---

## 파일럿 시리즈 전체 연결도

```
Pilot 01: RAG 기본 파이프라인
  ↓ 한계: 단순 청크, 문서 혼재, 출처 없음

Pilot 02: 지식 구조화
  ↓ 추가: 메타데이터 스키마, ChromaDB, 출처 표시
  ↓ 한계: 수동 업데이트, 외부 데이터 없음

Pilot 03: 자동 수집 파이프라인
  ↓ 추가: PubMed 연동, 검수 대기열, 버전 관리
  ↓ 한계: 언더라이팅 판단 없음

Pilot 04: 언더라이팅 Rule Engine
  ↓ 추가: 임상 근거 + 보험 판단 통합
  ↓ 완성: Clinical Evidence Intelligence Platform v1.0
```
