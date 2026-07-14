# 04. 개선 내역

## 개선 1 — LangChain 구버전 → LCEL 최신 방식 전환

### 변경 전 (구버전 RetrievalQA)
```python
from langchain.chains import RetrievalQA

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(),
    chain_type_kwargs={"prompt": PROMPT},
    return_source_documents=True
)
result = qa_chain.invoke({"query": query})
```

### 변경 후 (LCEL 방식)
```python
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt_template
    | llm
    | StrOutputParser()
)
result = rag_chain.invoke(query)
```

### 개선 효과
- 최신 LangChain 방식으로 deprecated 경고 제거
- 파이프라인 구조가 시각적으로 명확
- 각 컴포넌트 교체가 용이 (모듈화)

---

## 개선 2 — 프롬프트 언더라이팅 특화

### 변경 전 (일반적)
```
아래 문서를 참고하여 질문에 답하세요.
```

### 변경 후 (언더라이팅 특화)
```
당신은 보험 언더라이터를 돕는 의료 정보 어시스턴트입니다.
아래 참고 문서를 바탕으로 질문과 직접 관련된 내용만 답변하세요.
질문과 관련없는 내용은 완전히 무시하세요.
참고 문서에 질문과 관련된 내용이 부족하면 "관련 문서에서 충분한 정보를 찾지 못했습니다"라고 명시하세요.

답변 형식:
1. 핵심 요약 (3줄 이내, 질문과 직접 관련된 내용만)
2. 언더라이팅 관련 위험 요소 (질문 주제에 한정)
3. 추가 확인 필요 항목
```

### 개선 효과
- 언더라이터 관점의 구조화된 출력
- 관련 없는 내용 무시 지시
- 정보 부족 시 명시적 표현

---

## 개선 3 — 단순 벡터 검색 → 키워드 필터링 + 벡터 검색

### 변경 전
```python
# 전체 문서에서 유사도 검색
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
```

### 변경 후
```python
# 1단계: 키워드로 관련 문서 그룹 선택
# 2단계: 해당 그룹 내에서만 유사도 검색
TOPIC_MAP = {
    "glp": "GLP-1",
    "당뇨": "GLP-1",
    "비만": "GLP-1",
    "ckm": "CKM",
    "심혈관": "심혈관",
    "masld": "MASLD",
    "대사": "MASLD",
    "대장암": "대장암",
    "전립선": "전립선",
    "알츠하이머": "AD",
    "치매": "AD",
    "ltc": "LTC",
}

def get_filtered_retriever(query):
    query_lower = query.lower()
    for keyword, topic in TOPIC_MAP.items():
        if keyword in query_lower:
            filtered_docs = [
                doc for doc in chunks
                if topic.lower() in doc.metadata.get('source', '').lower()
            ]
            if filtered_docs:
                filtered_store = FAISS.from_documents(filtered_docs, embeddings)
                return filtered_store.as_retriever(search_kwargs={"k": 4})
    return vectorstore.as_retriever(search_kwargs={"k": 4})
```

### 개선 효과
- 문서 혼재 문제 완전 해결
- GLP-1 질문 → GLP-1 문서만 검색
- 검색 정확도 대폭 향상

---

## 개선 4 — Streamlit → ipywidgets UI 전환

### 변경 전 (Streamlit 시도)
- 외부 터널링 필요 (ngrok, localtunnel)
- 코랩 환경에서 불안정
- 3가지 시도 모두 실패

### 변경 후 (ipywidgets)
- 코랩 내장 라이브러리
- 외부 서버 불필요
- 안정적 실행

### 구현
```python
import ipywidgets as widgets
from IPython.display import display, clear_output

query_input = widgets.Textarea(layout=widgets.Layout(width="700px", height="100px"))
search_btn = widgets.Button(description="🔍 검색", button_style="primary")
output = widgets.Output()

def on_search(b):
    with output:
        clear_output()
        result = ask(query_input.value)
        display(widgets.HTML(f"<h3>📋 답변</h3><p>{result.replace(chr(10), '<br>')}</p>"))

search_btn.on_click(on_search)
display(widgets.HTML("<h2>🏥 언더라이팅 RAG Assistant</h2>"),
        query_input, search_btn, output)
```

---

## 향후 개선 계획 (TODO)

### 단기 (다음 세션)
- [ ] 당뇨병 진료지침 2023 PDF 드라이브 업로드 및 추가
- [ ] 언더라이팅 기준 텍스트 직접 작성 (HbA1c 등급, 약물 단계별 기준)
- [ ] 답변에 출처 문서명 + 페이지 표시

### 중기
- [ ] 당뇨병 특화 Agent
  - HbA1c 수치 입력 → 조절 등급 자동 분류
  - 약물명 입력 → 치료 단계 판단
  - 합병증 키워드 감지 → 관련 문서 검색
- [ ] Streamlit Cloud 배포 (로컬 환경 이전)

### 장기
- [ ] LangGraph 멀티스텝 Agent 전환
- [ ] Tool Calling 추가 (HIRA 급여기준 실시간 검색)
- [ ] 사용자 피드백 기반 검색 개선
