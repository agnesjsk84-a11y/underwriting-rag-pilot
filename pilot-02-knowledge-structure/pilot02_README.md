# Pilot 02 — 지식 구조화 기반 RAG 플랫폼

## Pilot 01과의 차이

| 항목 | Pilot 01 | Pilot 02 |
|---|---|---|
| 청크 방식 | 단순 분할 | 섹션 기반 분할 |
| 벡터 DB | FAISS | ChromaDB |
| 메타데이터 | 없음 | disease / section / guideline / version / page |
| 검색 방식 | 키워드 필터링 | 메타데이터 필터링 |
| 출처 표시 | 없음 | 가이드라인명 + 페이지 + 근거수준 |
| 버전 관리 | 없음 | content_hash + status |

## 목표

> PDF 한 개를 올리면, 메타데이터와 함께 출처가 표시된 답변이 나오는 RAG

## 문서 구성

| 파일 | 내용 |
|---|---|
| `01_planning.md` | 기획 — 스키마 설계, 기술 스택 선정 |
| `02_execution.md` | 실행 — Step별 코드와 구현 |
| `03_roadmap_pilot03_04.md` | Pilot 03·04 상세 설계 |

## 상태

🔜 구현 예정
