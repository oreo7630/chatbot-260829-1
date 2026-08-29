import hashlib
from datetime import date
from io import BytesIO

import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder

# --------------------------------------------------
# 페이지 설정
# --------------------------------------------------

st.set_page_config(
    page_title="1인 창업 운영 비서",
    page_icon="🧭",
    layout="centered"
)

st.title("🧭 1인 창업 운영 비서")

st.write(
    """
    혼자 회사를 운영하다 보면 재무, 세무, 인사, 정부지원금까지
    챙기기가 쉽지 않죠. 놓치기 쉬운 부분을 함께 점검해 보세요.
    """
)

# --------------------------------------------------
# API KEY
# --------------------------------------------------

openai_api_key = st.text_input(
    "OpenAI API Key",
    type="password"
)

if not openai_api_key:
    st.info(
        "OpenAI API Key를 입력해주세요.",
        icon="🔑"
    )
    st.stop()

client = OpenAI(api_key=openai_api_key)


# --------------------------------------------------
# 사업자 정보 입력 (사이드바)
# --------------------------------------------------

st.sidebar.header("🏢 우리 회사 정보")

business_type = st.sidebar.selectbox(
    "사업자 형태",
    [
        "예비 창업자 (아직 등록 전)",
        "개인사업자",
        "법인사업자"
    ]
)

industry = st.sidebar.text_input(
    "업종 (예: IT/소프트웨어, 요식업, 도소매 등)",
    value=""
)

founded_date = st.sidebar.date_input(
    "설립일 / 사업자등록일",
    value=date.today()
)

employee_count = st.sidebar.selectbox(
    "직원 수",
    [
        "직원 없음 (1인 운영)",
        "1~4명",
        "5~9명",
        "10명 이상"
    ]
)

revenue_stage = st.sidebar.selectbox(
    "매출 단계",
    [
        "매출 없음 (준비 중)",
        "매출 발생 초기",
        "연 매출 1억 미만",
        "연 매출 1억~10억",
        "연 매출 10억 이상"
    ]
)

st.sidebar.divider()

consulting_topic = st.sidebar.selectbox(
    "오늘 상담하고 싶은 분야",
    [
        "이번 달 전체 체크 (종합)",
        "재무 / 세무",
        "인사 / 노무",
        "정부지원사업",
        "오퍼레이션 / 행정",
        "기타"
    ]
)


# --------------------------------------------------
# AI 역할 설정
# --------------------------------------------------

SYSTEM_PROMPT = f"""
당신은 혼자 모든 업무를 처리하는 1인 창업자를 돕는
운영/재무/인사/정부지원금 전담 비서입니다.

사용자 회사 정보:
- 사업자 형태: {business_type}
- 업종: {industry if industry else "미입력"}
- 설립일/사업자등록일: {founded_date}
- 직원 수: {employee_count}
- 매출 단계: {revenue_stage}
- 오늘 날짜: {date.today()}

오늘 상담 분야:
{consulting_topic}

당신의 역할은 "정보를 검색해주는 것"이 아니라
"1인 창업자가 혼자 일하다 놓치기 쉬운 것을 챙겨주는 것"입니다.

상담 원칙:

1. 사용자의 사업자 형태, 직원 수, 매출 단계를 고려해서
   실제로 해당 사용자에게 필요한 항목만 짚어주세요.
   (예: 직원이 없으면 4대보험/근로계약서 얘기는 하지 않음)
2. 세무 신고, 노무 관련 마감일이나 법정 기한을 언급할 때는
   구체적인 날짜를 단정적으로 지어내지 말고,
   "일반적으로 매월/분기별/연 1회" 등 주기로 안내하고
   정확한 기한은 홈택스, 세무사, 노무사 등 공식 채널 확인을
   권장한다고 알려주세요.
3. 정부지원사업 관련 질문에는 K-스타트업, 기업마당 등
   공식 사이트 확인을 권장하고, 존재 여부가 불확실한
   특정 사업명이나 지원금액을 지어내지 마세요.
4. 어려운 용어(원천세, 4대보험, 부가세 예정고지 등)는
   처음 접하는 사람도 이해할 수 있게 쉽게 풀어서 설명하세요.
5. 답변은 실행 가능한 체크리스트 형태로 정리하세요.
6. 답변은 한국어로 작성하세요.

가능하면 다음 형식을 사용하세요.

### 📋 지금 챙겨야 할 것
사용자 상황에 맞는 항목을 우선순위대로 정리합니다.

### ⚠️ 놓치기 쉬운 부분
1인 운영자가 특히 자주 놓치는 부분을 짚어줍니다.

### 🧾 확인이 필요한 부분
정확한 날짜/금액/자격 요건 등 공식 채널 확인이 필요한 부분을
명확히 표시합니다.

### ✅ 다음 행동
지금 바로 할 수 있는 구체적인 행동 1~3개를 제안합니다.

### ❓ 추가로 알려주시면 좋은 정보
더 정확한 안내를 위해 필요한 정보를 질문합니다.
"""


# --------------------------------------------------
# 음성 -> 텍스트 변환 함수
# --------------------------------------------------

def transcribe_audio(audio_bytes: bytes) -> str:
    """녹음된 음성을 텍스트로 변환 (Whisper API)."""
    audio_file = BytesIO(audio_bytes)
    audio_file.name = "recording.wav"
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="ko",
    )
    return transcript.text


# --------------------------------------------------
# 대화 기록
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": """
안녕하세요! 👋

저는 **1인 창업 운영 비서**입니다.

혼자 모든 업무를 하다 보면 이런 게 궁금하실 거예요.

- 이번 달에 내가 챙겨야 할 세무/행정 일정이 뭐가 있을까요?
- 직원을 처음 뽑았는데 뭐부터 준비해야 하나요?
- 우리 회사도 받을 수 있는 정부지원사업이 있을까요?
- 부가세, 원천세... 이게 다 뭔가요?
- 사업자등록 정보가 바뀌면 어디에 신고해야 하나요?

왼쪽에서 우리 회사 정보를 먼저 입력해주시면
더 정확하게 챙겨드릴 수 있어요. 텍스트든 음성이든 편하게 물어보세요. 🧭
"""
        }
    ]

if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None


# --------------------------------------------------
# 기존 대화 출력
# --------------------------------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --------------------------------------------------
# 사용자 질문: 텍스트 + 음성
# --------------------------------------------------

text_prompt = st.chat_input(
    "창업 아이디어나 고민을 입력해주세요..."
)

st.caption("또는 마이크로 말씀해주세요 🎤")
audio_data = mic_recorder(
    start_prompt="🎤 녹음 시작",
    stop_prompt="⏹ 녹음 종료",
    just_once=False,
    key="ops_recorder",
)

prompt = None

if text_prompt:
    prompt = text_prompt

elif audio_data and audio_data.get("bytes"):
    audio_hash = hashlib.md5(audio_data["bytes"]).hexdigest()
    if audio_hash != st.session_state.last_audio_hash:
        st.session_state.last_audio_hash = audio_hash
        with st.spinner("음성을 텍스트로 변환 중..."):
            try:
                prompt = transcribe_audio(audio_data["bytes"])
            except Exception as e:
                st.error(f"음성 인식 중 오류가 발생했습니다: {e}")

if prompt:

    # 사용자 메시지 저장
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    # 사용자 메시지 출력
    with st.chat_message("user"):
        st.markdown(prompt)


    # --------------------------------------------------
    # OpenAI API
    # --------------------------------------------------

    stream = client.responses.create(

        model="gpt-5.6-terra",

        instructions=SYSTEM_PROMPT,

        input=[
            {
                "role": message["role"],
                "content": message["content"]
            }
            for message in st.session_state.messages
        ],

        stream=True
    )


    # --------------------------------------------------
    # 스트리밍 Generator
    # --------------------------------------------------

    def response_generator():

        for event in stream:

            if event.type == "response.output_text.delta":
                yield event.delta


    # --------------------------------------------------
    # AI 답변 출력
    # --------------------------------------------------

    with st.chat_message("assistant"):

        response = st.write_stream(
            response_generator()
        )


    # AI 답변 저장
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response
        }
    )
