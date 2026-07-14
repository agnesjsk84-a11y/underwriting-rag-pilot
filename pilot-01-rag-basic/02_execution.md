# 02. 실행 과정

## Step 1 — 환경 세팅 및 라이브러리 설치

### 환경
- Google Colab (무료 티어)
- Python 3.12

### 설치 명령어
```bash
pip install langchain langchain-groq faiss-cpu pypdf
pip install langchain-community sentence-transformers
pip install langchain-huggingface langchain-text-splitters
pip install streamlit pyngrok  # UI 시도 (후에 변경)
```

---

## Step 2 — LLM 연결 테스트

```python
import os
from langchain_groq import ChatGroq

os.environ["GROQ_API_KEY"] = "your-api-key"

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
)

response = llm.invoke("당뇨병 환자의 HbA1c 7.5%는 어떤 의미인가요? 한국어로 답해주세요.")
print(response.content)
```

### 결과 ✅
HbA1c 7.5%에 대한 한국어 설명 정상 출력 확인
- 정상/전당뇨/당뇨병 기준 설명
- 조절 목표(7% 이하) 언급
- LLM 연결 성공 확인

---

## Step 3 — PDF 로드 및 벡터 DB 구축

### 지식 베이스 구성
구글 드라이브 SCORUN 폴더의 PDF 15개 활용
```
경로: /content/drive/MyDrive/SCORUN/35411119523378640 (Unzipped Files)/
```

### 코드
```python
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import glob

# PDF 전체 로드
pdf_files = glob.glob("/content/drive/MyDrive/SCORUN/.../  *.pdf")

all_documents = []
for pdf_path in pdf_files:
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    all_documents.extend(docs)

# 청크 분할
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
chunks = splitter.split_documents(all_documents)

# 한국어 임베딩
embeddings = HuggingFaceEmbeddings(
    model_name="jhgan/ko-sroberta-multitask"
)

# FAISS 벡터 DB
vectorstore = FAISS.from_documents(chunks, embeddings)
```

### 결과 ✅
```
총 페이지 수: 217
총 청크 수: 277
벡터 DB 구축 완료
```

---

## Step 4 — RAG 체인 구성

### LangChain LCEL 방식 (최신)
```python
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

prompt_template = PromptTemplate.from_template("""
당신은 보험 언더라이터를 돕는 의료 정보 어시스턴트입니다.
아래 참고 문서를 바탕으로 언더라이터에게 유용한 정보를 정리해주세요.

참고 문서:
{context}

질문: {question}

답변 형식:
1. 핵심 요약 (3줄 이내)
2. 언더라이팅 관련 위험 요소
3. 추가 확인 필요 항목
""")

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt_template
    | llm
    | StrOutputParser()
)
```

---

## Step 5 — UI 구현

### 시도 1: Streamlit + ngrok → 실패
### 시도 2: Streamlit + localtunnel → 실패
### 시도 3: Streamlit + 코랩 포트 포워딩 → 404 오류
### 최종: ipywidgets ✅

```python
import ipywidgets as widgets
from IPython.display import display, clear_output

query_input = widgets.Textarea(
    placeholder="질문을 입력하세요...",
    layout=widgets.Layout(width="700px", height="100px")
)
search_btn = widgets.Button(
    description="🔍 검색",
    button_style="primary"
)
output = widgets.Output()

def on_search(b):
    with output:
        clear_output()
        result = ask(query_input.value)
        display(widgets.HTML(
            f"<h3>📋 답변</h3><p>{result.replace(chr(10), '<br>')}</p>"
        ))

search_btn.on_click(on_search)
display(
    widgets.HTML("<h2>🏥 언더라이팅 RAG Assistant</h2>"),
    query_input, search_btn, output
)
```

---

## Step 6 — 키워드 필터링 추가

문서 혼재 문제 발견 후 필터링 로직 추가 (상세 내용은 03_errors_and_fixes.md 참조)

```python
TOPIC_MAP = {
    "glp": "GLP-1",
    "당뇨": "GLP-1",
    "ckm": "CKM",
    "masld": "MASLD",
    "심혈관": "심혈관",
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
