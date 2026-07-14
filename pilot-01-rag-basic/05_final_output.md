# 05. 최종 산출물 및 회고

## 최종 산출물

### 시스템 구성
```
언더라이팅 RAG Assistant v0.1
├── 지식 베이스: SCOR 세미나 PDF 15개 (217페이지, 277청크)
├── 검색 엔진: FAISS + 키워드 필터링
├── LLM: Groq Llama 3.3 70B
├── 임베딩: jhgan/ko-sroberta-multitask
└── UI: ipywidgets (Google Colab)
```

### 최종 코드 전체

```python
# =============================================
# 언더라이팅 RAG Assistant — 최종 버전
# =============================================

# [셀 1] 라이브러리 설치
# !pip install -q langchain-groq langchain-huggingface langchain-text-splitters
# !pip install -q faiss-cpu pypdf langchain-community sentence-transformers

# [셀 2] API 키 + LLM 설정
import os
from langchain_groq import ChatGroq

os.environ["GROQ_API_KEY"] = "your-api-key-here"

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
)
print("✅ LLM 연결 완료")

# [셀 3] 드라이브 마운트 + PDF 벡터화
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import glob

pdf_files = glob.glob("/content/drive/MyDrive/SCORUN/35411119523378640 (Unzipped Files)/*.pdf")

all_documents = []
for pdf_path in pdf_files:
    try:
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        all_documents.extend(docs)
        print(f"✅ {pdf_path.split('/')[-1]}")
    except Exception as e:
        print(f"❌ {pdf_path.split('/')[-1]}: {e}")

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(all_documents)

embeddings = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")
vectorstore = FAISS.from_documents(chunks, embeddings)
print(f"\n✅ 벡터 DB 완료 — {len(all_documents)}페이지, {len(chunks)}청크")

# [셀 4] 키워드 필터링 + RAG 체인
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

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
                print(f"🔍 '{topic}' 관련 청크 {len(filtered_docs)}개 검색")
                return filtered_store.as_retriever(search_kwargs={"k": 4})
    print("🔍 전체 문서 검색")
    return vectorstore.as_retriever(search_kwargs={"k": 4})

prompt_template = PromptTemplate.from_template("""
당신은 보험 언더라이터를 돕는 의료 정보 어시스턴트입니다.
아래 참고 문서를 바탕으로 질문과 직접 관련된 내용만 답변하세요.
질문과 관련없는 내용은 완전히 무시하세요.
참고 문서에 질문과 관련된 내용이 부족하면 "관련 문서에서 충분한 정보를 찾지 못했습니다"라고 명시하세요.

참고 문서:
{context}

질문: {question}

답변 형식:
1. 핵심 요약 (3줄 이내)
2. 언더라이팅 관련 위험 요소
3. 추가 확인 필요 항목
""")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def ask(query):
    filtered_retriever = get_filtered_retriever(query)
    rag_chain = (
        {"context": filtered_retriever | format_docs, "question": RunnablePassthrough()}
        | prompt_template
        | llm
        | StrOutputParser()
    )
    return rag_chain.invoke(query)

print("✅ RAG 체인 준비 완료")

# [셀 5] UI 실행
import ipywidgets as widgets
from IPython.display import display, clear_output

query_input = widgets.Textarea(
    placeholder="예: GLP-1 수용체 작용제 복용 환자의 언더라이팅 시 주요 고려사항은?",
    layout=widgets.Layout(width="700px", height="100px")
)
search_btn = widgets.Button(
    description="🔍 검색",
    button_style="primary",
    layout=widgets.Layout(width="150px")
)
output = widgets.Output()

def on_search(b):
    with output:
        clear_output()
        if not query_input.value:
            print("질문을 입력해주세요.")
            return
        print("🔄 검색 중...")
        result = ask(query_input.value)
        clear_output()
        display(widgets.HTML(
            f"<h3>📋 답변</h3><p>{result.replace(chr(10), '<br>')}</p>"
        ))

search_btn.on_click(on_search)
display(
    widgets.HTML("<h2>🏥 언더라이팅 RAG Assistant</h2>"),
    widgets.HTML("<p>SCOR 의료 문서 기반 언더라이팅 지원 시스템 v0.1</p>"),
    query_input,
    search_btn,
    output
)
```

---

## 실행 결과 예시

### 질문
```
GLP-1 수용체 작용제 복용 환자의 언더라이팅 시 주요 고려사항은?
```

### 답변 (최종 버전)
```
1. 핵심 요약:
GLP-1 수용체 작용제는 조절이 어려울 때 사용되며,
언더라이팅 시 약물 사용 목적과 관련 위험 요소 평가가 핵심이다.

2. 언더라이팅 관련 위험 요소:
- 기존 치료법 한계와 치료 반응의 변동성
- 부작용 및 약물 중단 가능성
- 동반질환(심혈관, 신장) 여부

3. 추가 확인 필요 항목:
- 환자의 기존 질병 상태 및 치료 이력
- 약물 복용 기간 및 반응 모니터링 결과
- 대체 치료 계획 여부
```

---

## 회고

### 잘 된 점
- 완전 무료 스택으로 작동하는 RAG 파이프라인 완성
- 한국어 특화 임베딩 적용
- 문서 혼재 문제를 직접 디버깅하고 해결
- LangChain 버전 변화에 대응하며 최신 LCEL 방식 습득

### 어려웠던 점
- LangChain의 빠른 버전 변화로 import 오류 반복
- 코랩 환경에서 Streamlit 외부 접속 불안정 (3가지 시도 실패)
- RAG 검색 정확도 — 프롬프트만으로는 해결 불가, 검색 단계 수정 필요

### 핵심 학습
1. **RAG 품질은 검색(Retrieval)에서 결정된다** — 좋은 LLM도 나쁜 컨텍스트 앞에선 무력함
2. **메타데이터 필터링은 RAG 필수 전략** — 문서 종류가 다양할수록 중요
3. **LangChain은 공식 문서를 항상 확인** — 버전 변화가 매우 빠름
4. **코랩 한계를 인지하고 대안을 빠르게 찾는 것** — Streamlit → ipywidgets 전환

### 도메인 지식의 역할
> 이 파일럿에서 가장 중요한 부분은 코드가 아니라
> "어떤 질문이 언더라이팅에 중요한가"와
> "어떤 문서가 어떤 주제를 다루는가"를 설계하는 것이었다.
> 이 부분은 18년의 임상·언더라이팅 경험 없이는 설계할 수 없다.

---

## 버전 이력

| 버전 | 날짜 | 주요 변경사항 |
|---|---|---|
| v0.1 | 2026-07-11 | 최초 RAG 파이프라인 완성, 키워드 필터링 추가 |
| v0.2 | 예정 | 당뇨병 진료지침 추가, 언더라이팅 기준 텍스트 추가 |
| v0.3 | 예정 | 당뇨병 특화 Agent (HbA1c 분류 로직) |
| v1.0 | 예정 | Streamlit Cloud 배포 |
