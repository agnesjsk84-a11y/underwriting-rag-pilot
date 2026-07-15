# RWE Data Validator

HIRA 「약제성과평가를 위한 실제 근거(RWE) 생성 가이드라인」을 참고해 만든 CSV 품질 검증 예제입니다. 프로젝트의 정식 기준은 [`docs/rwe-data-ingestion-standardization-validation-guideline.md`](../docs/rwe-data-ingestion-standardization-validation-guideline.md)를 따릅니다.

## 지원 검증

- 필수 컬럼과 필수값
- 문자열, 정수, 실수, 날짜 자료형
- 숫자 최소·최대 범위
- 허용 코드 목록
- 단일 또는 복합키 중복
- 두 날짜 컬럼의 시간 순서
- 규칙별 `error`/`warning` 심각도
- JSON 및 Markdown 검증 근거 리포트

## 실행

Python 3.9 이상에서 외부 패키지 없이 실행됩니다.

```bash
python3 rwe-validator/src/rwe_validator.py \
  --input rwe-validator/examples/patients.csv \
  --rules rwe-validator/config/validation-rules.json \
  --output-json rwe-validator/reports/validation-report.json \
  --output-md rwe-validator/reports/validation-report.md
```

검증 오류가 없으면 종료 코드 `0`, 하나 이상의 `error` 규칙이 실패하면 `1`, 입력·설정 오류는 `2`를 반환합니다. `warning`만 존재할 때는 `0`입니다.

## 테스트

```bash
python3 -m unittest discover -s rwe-validator/tests -v
```

## 규칙 설정

[`config/validation-rules.json`](config/validation-rules.json)에서 프로젝트별 임계값을 관리합니다.

```json
{
  "name": "age",
  "type": "integer",
  "required": true,
  "min": 0,
  "max": 120,
  "severity": "error"
}
```

운영 데이터에 적용할 때는 다음을 함께 버전 관리합니다.

- 데이터 사전과 코드 체계 버전
- 소스-타깃 매핑서
- 규칙 변경 사유와 승인자
- 데이터 스냅샷 ID 또는 해시
- 검증 도구·설정 버전과 실행 결과

> 이 코드는 포트폴리오와 운영 설계용 참조 구현입니다. 규제기관 승인, 임상적 타당성 평가 또는 개인정보 적법성 검토를 대체하지 않습니다.
