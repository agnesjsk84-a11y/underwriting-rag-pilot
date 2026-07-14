# 02. 실행 계획 — 단계별 구현

## 전체 실행 순서

```
Step 1. 환경 세팅 (Day 1)
Step 2. 지식 스키마 설계 (Day 1~2)
Step 3. PDF 섹션 분할 + 메타데이터 태깅 (Day 3~5)
Step 4. ChromaDB 구축 (Day 6~7)
Step 5. 메타데이터 필터링 RAG 체인 (Day 8~10)
Step 6. 출처 표시 + UI (Day 11~14)
```

---

## Step 1 — 환경 세팅

```python
!pip install -q chromadb langchain-groq langchain-huggingface
!pip install -q langchain-text-splitters pypdf sentence-transformers
```

---

## Step 2 — 지식 스키마 설계

메타데이터 구조를 코드로 정의한다.

```python
# 메타데이터 스키마 정의
DIABETES_SCHEMA = {
    "disease": "diabetes",
    "sections": [
        "definition",       # 정의 · 분류
        "epidemiology",     # 역학
        "risk_factors",     # 위험요인
        "diagnosis",        # 진단
        "severity",         # 중증도
        "treatment",        # 치료
        "complications",    # 합병증
        "prognosis",        # 예후
        "underwriting"      # 언더라이팅
    ],
    "evidence_levels": ["A", "B", "C", "E"],
    "status_values": ["active", "superseded", "archived"]
}

# 섹션 키워드 매핑 (자동 분류용)
SECTION_KEYWORDS = {
    "definition": ["정의", "분류", "제1형", "제2형", "LADA"],
    "diagnosis": ["진단", "HbA1c", "공복혈당", "당부하검사", "기준"],
    "severity": ["조절", "목표", "양호", "불량", "중증도"],
    "treatment": ["치료", "metformin", "GLP-1", "SGLT2", "인슐린", "약물"],
    "complications": ["합병증", "망막", "신증", "신경", "심혈관", "족부"],
    "prognosis": ["예후", "사망률", "생존"],
    "underwriting": ["언더라이팅", "위험", "보험", "심사"]
}
```

---

## Step 3 — PDF 섹션 분할 + 메타데이터 태깅

### 3-1. PDF 로드

```python
from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader("/content/drive/MyDrive/2023 당뇨병 진료지침_전문_240620.pdf")
pages = loader.load()
print(f"총 페이지: {len(pages)}")
```

### 3-2. 섹션 자동 분류 함수

```python
def classify_section(text: str) -> str:
    """텍스트 내용을 보고 섹션 자동 분류"""
    text_lower = text.lower()
    for section, keywords in SECTION_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return section
    return "general"

def extract_evidence_level(text: str) -> str:
    """근거 수준 추출 (A/B/C/E)"""
    import re
    match = re.search(r'근거수준\s*([ABCE])', text)
    if match:
        return match.group(1)
    return "unknown"
```

### 3-3. 청크 분할 + 메타데이터 태깅

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
import hashlib

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

chunks_with_metadata = []
for i, page in enumerate(pages):
    chunks = splitter.split_text(page.page_content)
    for j, chunk in enumerate(chunks):
        # 섹션 자동 분류
        section = classify_section(chunk)
        evidence_level = extract_evidence_level(chunk)

        # 고유 ID 생성
        knowledge_id = f"KNO-DM-{i:03d}-{j:03d}"

        # 내용 해시 (버전 관리용)
        content_hash = hashlib.md5(chunk.encode()).hexdigest()[:8]

        metadata = {
            # 기본
            "knowledge_id": knowledge_id,
            "disease": "diabetes",
            "disease_type": "type2",

            # 섹션
            "section": section,

            # 근거
            "guideline": "KDA_2023",
            "version": "2023",
            "source": "대한당뇨병학회",
            "source_type": "guideline",
            "page": i + 1,
            "evidence_level": evidence_level,

            # 임상
            "country": "KR",

            # 버전 관리
            "content_hash": content_hash,
            "last_reviewed": "2026-07-15",
            "status": "active"
        }

        chunks_with_metadata.append({
            "text": chunk,
            "metadata": metadata
        })

print(f"총 청크 수: {len(chunks_with_metadata)}")
print(f"섹션 분포:")
from collections import Counter
sections = [c["metadata"]["section"] for c in chunks_with_metadata]
for section, count in Counter(sections).most_common():
    print(f"  {section}: {count}개")
```

---

## Step 4 — ChromaDB 구축

```python
import chromadb
from langchain_huggingface import HuggingFaceEmbeddings

# 임베딩 모델
embeddings = HuggingFaceEmbeddings(
    model_name="jhgan/ko-sroberta-multitask"
)

# ChromaDB 클라이언트
chroma_client = chromadb.Client()
collection = chroma_client.create_collection(
    name="medical_knowledge",
    metadata={"hnsw:space": "cosine"}
)

# 데이터 저장
texts = [c["text"] for c in chunks_with_metadata]
metadatas = [c["metadata"] for c in chunks_with_metadata]
ids = [c["metadata"]["knowledge_id"] for c in chunks_with_metadata]

# 임베딩 생성
vectors = embeddings.embed_documents(texts)

# ChromaDB에 저장
collection.add(
    embeddings=vectors,
    documents=texts,
    metadatas=metadatas,
    ids=ids
)

print(f"✅ ChromaDB 저장 완료 — {collection.count()}개 청크")
```

---

## Step 5 — 메타데이터 필터링 RAG 체인

```python
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

os.environ["GROQ_API_KEY"] = "your-api-key"
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

def search_with_metadata(query: str, section_filter: str = None, k: int = 4):
    """메타데이터 필터링 검색"""
    query_vector = embeddings.embed_query(query)

    # 필터 조건 설정
    where_filter = {"disease": "diabetes", "status": "active"}
    if section_filter:
        where_filter["section"] = section_filter

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=k,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )

    return results

def format_results_with_citations(results):
    """검색 결과를 출처 정보와 함께 포맷"""
    formatted = []
    citations = []

    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        formatted.append(doc)
        citations.append(
            f"[{meta['guideline']} p.{meta['page']} | 근거수준: {meta['evidence_level']}]"
        )

    context = "\n\n".join(formatted)
    citation_text = "\n".join(set(citations))
    return context, citation_text

# 프롬프트 템플릿
prompt = PromptTemplate.from_template("""
당신은 보험 언더라이터를 돕는 의료 정보 어시스턴트입니다.
아래 참고 문서를 바탕으로 질문과 직접 관련된 내용만 답변하세요.
관련 없는 내용은 무시하고, 정보가 부족하면 "관련 정보를 찾지 못했습니다"라고 명시하세요.

참고 문서:
{context}

질문: {question}

답변 형식:
1. 핵심 요약 (3줄 이내)
2. 언더라이팅 관련 위험 요소
3. 추가 확인 필요 항목
""")

def ask_with_citations(query: str, section_filter: str = None):
    """출처 포함 답변 생성"""
    # 검색
    results = search_with_metadata(query, section_filter)
    context, citations = format_results_with_citations(results)

    # 답변 생성
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": query})

    return answer, citations

print("✅ RAG 체인 준비 완료")
```

---

## Step 6 — 출처 표시 UI

```python
import ipywidgets as widgets
from IPython.display import display, clear_output

# 섹션 필터 드롭다운
section_dropdown = widgets.Dropdown(
    options=[
        ("전체", None),
        ("진단", "diagnosis"),
        ("치료", "treatment"),
        ("합병증", "complications"),
        ("예후", "prognosis"),
    ],
    description="섹션:",
    layout=widgets.Layout(width="300px")
)

query_input = widgets.Textarea(
    placeholder="예: HbA1c 8% 이상 제2형 당뇨 환자의 언더라이팅 고려사항은?",
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
        answer, citations = ask_with_citations(
            query_input.value,
            section_dropdown.value
        )
        clear_output()
        display(widgets.HTML(f"""
            <h3>📋 답변</h3>
            <p>{answer.replace(chr(10), '<br>')}</p>
            <hr>
            <h4>📚 참고 출처</h4>
            <p style="color: gray; font-size: 0.9em;">
                {citations.replace(chr(10), '<br>')}
            </p>
        """))

search_btn.on_click(on_search)

display(
    widgets.HTML("<h2>🏥 언더라이팅 지식 플랫폼 v0.2</h2>"),
    widgets.HTML("<p>메타데이터 기반 의료 문서 검색 시스템</p>"),
    widgets.HBox([section_dropdown]),
    query_input,
    search_btn,
    output
)
```
