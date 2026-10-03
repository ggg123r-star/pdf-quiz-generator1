import streamlit as st
from pypdf import PdfReader
import json, re, io

st.set_page_config(page_title="PDF AI 문제 생성기", page_icon="📚", layout="wide")

st.title("📚 PDF AI 문제 자동 생성기")
st.caption("PDF 내용을 바탕으로 4지선다 시험문제를 생성합니다.")

with st.sidebar:
    st.header("⚙️ 문제 설정")
    api_key = st.text_input("OpenAI API Key", type="password",
                            help="OpenAI API에서 발급한 API 키를 입력하세요. 이 프로그램은 입력한 키를 저장하지 않습니다.")
    model = st.selectbox("AI 모델", ["gpt-6-luna", "gpt-6-sol"], index=0)
    count = st.slider("문제 수", 1, 50, 10)
    difficulty = st.selectbox("난이도", ["하", "중", "상"], index=1)
    qtype = st.selectbox("문제 유형", [
        "혼합형",
        "개념형",
        "옳은 것/옳지 않은 것",
        "임상 상황형",
        "사례형"
    ])
    include_explanation = st.checkbox("정답 해설 포함", value=True)

uploaded = st.file_uploader("📄 PDF 파일을 업로드하세요", type=["pdf"])

def extract_pdf(file):
    reader = PdfReader(file)
    pages = []
    for i, page in enumerate(reader.pages, 1):
        txt = page.extract_text() or ""
        if txt.strip():
            pages.append(f"\n[페이지 {i}]\n{txt}")
    return "\n".join(pages), len(reader.pages)

def clean_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text

def generate_with_ai(text, n, difficulty, qtype, model, api_key):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    # 너무 긴 PDF는 앞부분만 보내지 않고 앞/중간/뒤를 균형 있게 사용
    max_chars = 90000
    if len(text) > max_chars:
        third = max_chars // 3
        text_for_ai = text[:third] + "\n[중간 생략]\n" + text[len(text)//2-third//2:len(text)//2+third//2] + "\n[중간 생략]\n" + text[-third:]
    else:
        text_for_ai = text

    prompt = f"""
너는 대학 시험문제 출제 전문가다.
아래 PDF 학습자료만 근거로 한국어 객관식 시험문제를 만들어라.

조건:
- 총 {n}문제
- 모든 문제는 4지선다(A~D)
- 난이도: {difficulty}
- 문제 유형: {qtype}
- PDF에 없는 사실을 정답의 근거로 추가하지 말 것
- 정답은 반드시 1개만 명확하게
- 오답은 그럴듯하지만 PDF 내용과 비교하면 틀리게 만들 것
- 단순히 문장에서 단어 하나를 지우는 방식으로 만들지 말 것
- 물리치료/보건계열 시험에 적합한 표현을 사용할 것
- 비슷한 문제가 반복되지 않게 할 것
- 정답은 answer에 A/B/C/D 중 하나로 표시
- 해설은 PDF의 근거를 설명하는 짧고 명확한 문장으로 작성
- 반드시 JSON 배열만 출력할 것. 마크다운이나 다른 글은 출력하지 말 것.

JSON 형식:
[
  {{
    "question": "문제 내용",
    "options": {{
      "A": "보기1",
      "B": "보기2",
      "C": "보기3",
      "D": "보기4"
    }},
    "answer": "A",
    "explanation": "정답인 이유"
  }}
]

학습자료:
{text_for_ai}
"""

    response = client.responses.create(
        model=model,
        input=prompt
    )
    raw = response.output_text
    return json.loads(clean_json(raw))

def make_txt(questions, title):
    out = [title, "=" * 60, ""]
    for i, q in enumerate(questions, 1):
        out.append(f"{i}. {q['question']}")
        for key in ["A", "B", "C", "D"]:
            out.append(f"   {key}. {q['options'][key]}")
        out.append("")
    return "\n".join(out)

def make_answer_txt(questions, title):
    out = [title + " - 정답 및 해설", "=" * 60, ""]
    for i, q in enumerate(questions, 1):
        out.append(f"{i}. 정답: {q['answer']}")
        out.append(f"   해설: {q.get('explanation','')}")
        out.append("")
    return "\n".join(out)

if uploaded:
    try:
        pdf_text, page_count = extract_pdf(uploaded)
        st.success(f"PDF 확인 완료 — 총 {page_count}페이지, 추출 텍스트 {len(pdf_text):,}자")
    except Exception as e:
        st.error(f"PDF를 읽는 중 오류가 발생했습니다: {e}")
        st.stop()

    if not pdf_text.strip():
        st.error("텍스트를 읽을 수 없는 PDF입니다. 스캔본이면 OCR 기능을 추가해야 합니다.")
    elif st.button("🚀 AI 문제 생성하기", type="primary"):
        if not api_key:
            st.warning("왼쪽 메뉴에 OpenAI API Key를 입력해주세요.")
            st.stop()

        with st.spinner("PDF 내용을 분석해서 시험문제를 만드는 중입니다..."):
            try:
                questions = generate_with_ai(
                    pdf_text, count, difficulty, qtype, model, api_key
                )
            except Exception as e:
                st.error("문제 생성 중 오류가 발생했습니다.")
                st.code(str(e))
                st.stop()

        st.success(f"총 {len(questions)}문제가 생성되었습니다.")

        st.subheader("📝 시험지")
        for i, q in enumerate(questions, 1):
            st.markdown(f"### {i}. {q['question']}")
            for key in ["A", "B", "C", "D"]:
                st.write(f"**{key}.** {q['options'][key]}")
            if include_explanation:
                with st.expander(f"{i}번 정답/해설 보기"):
                    st.write(f"**정답: {q['answer']}**")
                    st.write(q.get("explanation", ""))

        title = uploaded.name.rsplit(".", 1)[0]
        exam = make_txt(questions, title + " 시험지")
        answers = make_answer_txt(questions, title)

        st.divider()
        st.subheader("📥 파일 저장")
        st.download_button(
            "시험지 TXT 다운로드", exam,
            file_name=f"{title}_시험지.txt",
            mime="text/plain"
        )
        st.download_button(
            "정답·해설 TXT 다운로드", answers,
            file_name=f"{title}_정답해설.txt",
            mime="text/plain"
        )
else:
    st.info("왼쪽에서 문제 설정을 선택한 뒤 PDF를 업로드하세요.")
