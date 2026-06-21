"""
====================================================================
초개인화 통증 메커니즘 기반 월경 주기 예측 및 맞춤형 약물 타이밍 솔루션
----------------------------------------------------------------------
고등학교 인공지능 기초 수행평가용 프로토타입
실행 방법: streamlit run app.py
====================================================================
"""

import streamlit as st
from datetime import date, timedelta

# ============================================================
# 0. 페이지 기본 설정 & 디자인 톤
#    - 메인 컬러: 세이지 그린(#6B8F71) - 안정/신뢰
#    - 포인트 컬러: 테라코타(#D98C6F) - 경고/주의 알림용
#    - 배경: 따뜻한 오프화이트(#FAF7F2)
# ============================================================
st.set_page_config(
    page_title="루나케어 | 초개인화 생리주기 솔루션",
    page_icon="🌙",
    layout="centered",
)

# 커스텀 CSS (Streamlit 기본 테마 위에 톤앤매너 입히기)
st.markdown(
    """
    <style>
    .stApp { background-color: #FAF7F2; }
    h1, h2, h3 { color: #3E4A3D; font-family: 'Georgia', serif; }
    .stButton>button {
        background-color: #6B8F71; color: white; border-radius: 8px;
        border: none; padding: 0.5em 1.2em; font-weight: 600;
    }
    .stButton>button:hover { background-color: #587A5E; }
    .alert-box {
        background-color: #FCEEE7; border-left: 5px solid #D98C6F;
        padding: 1em; border-radius: 6px; margin: 0.8em 0;
    }
    .info-box {
        background-color: #EFF3EC; border-left: 5px solid #6B8F71;
        padding: 1em; border-radius: 6px; margin: 0.8em 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 1. 세션 상태(데이터베이스 역할) 초기화
#    실제 서비스라면 DB(SQLite 등)로 대체되지만,
#    프로토타입에서는 st.session_state로 사용자 데이터를 누적 관리한다.
# ============================================================
if "profiled" not in st.session_state:
    st.session_state.profiled = False          # 초기 프로파일링 완료 여부
    st.session_state.cycle_regularity = None    # 주기 패턴: 일정/아니오/불규칙
    st.session_state.lifestyle_sensitivity = None  # 생활 영향 민감도: 많음/없음/잘모름
    st.session_state.baseline_pain = None       # 평소 통증 수준: 상/중/하
    st.session_state.drug_history = {}          # {약물명: 효과} 누적 딕셔너리

# 약물 마스터 데이터: (표시명, 주성분 계열, 주요 타겟 증상)
DRUG_DB = {
    "타이레놀": {"성분": "아세트아미노펜", "타겟": ["가벼운 통증", "발열"]},
    "이지엔6 애니": {"성분": "이부프로펜", "타겟": ["일반 생리통", "염증성 통증"]},
    "이지엔6 이브/그날엔": {"성분": "이부프로펜+파마브롬", "타겟": ["붓기", "부종 동반 통증"]},
    "탁센/이지엔6 프로": {"성분": "나프록센/덱시부프로펜", "타겟": ["강한 통증", "허리 통증"]},
    "부스코판": {"성분": "부틸스코폴라민(진경제)", "타겟": ["쥐어짜는 통증", "경련성 복통"]},
}

# 생활 영향 민감도 → 가중치 매핑 (핵심 로직 1)
SENSITIVITY_WEIGHT = {"많음": 1.0, "잘 모름": 0.5, "없음": 0.1}

# 라이프스타일 입력값 → 점수 매핑
STRESS_SCORE = {"하": 0, "중": 1, "상": 2}
SLEEP_SCORE = {"잘잠": 0, "보통": 1, "부족": 2}


# ============================================================
# 2. 사이드바: 진행 단계 안내
# ============================================================
st.sidebar.title("🌙 루나케어")
st.sidebar.caption("초개인화 생리주기 예측 솔루션")
step = "STEP 1. 초기 프로파일링" if not st.session_state.profiled else "STEP 2. 일상 입력 & 예측"
st.sidebar.info(f"현재 단계\n\n**{step}**")


# ============================================================
# 3. STEP 1 - 초기 민감도 및 통증 프로파일링 (Baseline 설정)
#    최초 1회만 수집. 이후 모든 예측/추천의 '가중치'로 작동.
# ============================================================
if not st.session_state.profiled:
    st.title("🌙 초기 프로파일링")
    st.write("처음 한 번만 입력하면 돼요. 이 정보는 앞으로의 예측과 약물 추천에 "
             "**개인 맞춤 가중치**로 계속 활용됩니다.")

    with st.form("baseline_form"):
        st.subheader("1️⃣ 주기 패턴")
        cycle_regularity = st.radio(
            "평소 생리 주기가 일정한가요?",
            ["예", "아니오", "불규칙"],
            horizontal=True,
        )

        st.subheader("2️⃣ 생활 영향 민감도")
        lifestyle_sensitivity = st.radio(
            "평소 스트레스나 수면 부족이 있을 때 주기에 영향을 받는 편인가요?",
            ["많음", "없음", "잘 모름"],
            horizontal=True,
            help="이 답변이 향후 스트레스/수면 입력의 보정 강도(가중치)를 결정합니다.",
        )

        st.subheader("3️⃣ 평소 통증 수준")
        baseline_pain = st.radio(
            "평소 생리통은 어느 정도인가요?",
            ["상", "중", "하"],
            horizontal=True,
            help="'상'으로 답하시면 통증이 시작되기 전, 선제적 복용 타이밍을 안내해 드려요.",
        )

        st.subheader("4️⃣ 평소 복용 약물 및 효과")
        st.caption("자주 드셨던 약물을 선택하고, 각각의 효과를 평가해 주세요. (복수 선택 가능)")

        drug_options = list(DRUG_DB.keys()) + ["기타"]
        selected_drugs = st.multiselect("자주 복용한 약물", drug_options)

        # 선택한 약물 각각에 대해 효과 입력 (동적 폼)
        drug_feedback = {}
        for drug in selected_drugs:
            if drug == "기타":
                custom_name = st.text_input("기타 약물명을 입력해 주세요", key="custom_drug_name")
                if custom_name:
                    effect = st.radio(
                        f"'{custom_name}'의 효과는 어땠나요?",
                        ["효과 좋음", "보통", "효과 없음"],
                        horizontal=True, key="custom_drug_effect",
                    )
                    drug_feedback[custom_name] = effect
            else:
                effect = st.radio(
                    f"'{drug}'의 효과는 어땠나요?",
                    ["효과 좋음", "보통", "효과 없음"],
                    horizontal=True, key=f"effect_{drug}",
                )
                drug_feedback[drug] = effect

        submitted = st.form_submit_button("프로파일링 완료하고 시작하기")

        if submitted:
            st.session_state.cycle_regularity = cycle_regularity
            st.session_state.lifestyle_sensitivity = lifestyle_sensitivity
            st.session_state.baseline_pain = baseline_pain
            st.session_state.drug_history = drug_feedback
            st.session_state.profiled = True
            st.rerun()

# ============================================================
# 4. STEP 2 - 일상 입력 + AI 예측 + 약물 추천
# ============================================================
else:
    st.title("🌙 이번 주기 체크인")

    # 현재 프로파일 요약 (사이드바에 표시 → 사용자가 언제든 본인 baseline 확인 가능)
    with st.sidebar.expander("내 프로파일 보기"):
        st.write(f"- 주기 패턴: **{st.session_state.cycle_regularity}**")
        st.write(f"- 생활 영향 민감도: **{st.session_state.lifestyle_sensitivity}**")
        st.write(f"- 평소 통증 수준: **{st.session_state.baseline_pain}**")
        st.write("- 약물 기록:")
        for d, e in st.session_state.drug_history.items():
            st.write(f"   · {d}: {e}")
        if st.button("프로파일 다시 설정"):
            st.session_state.profiled = False
            st.rerun()

    # --------------------------------------------------------
    # 4-1. 라이프스타일 간편 입력
    # --------------------------------------------------------
    st.subheader("📋 오늘의 컨디션 입력")
    col1, col2 = st.columns(2)
    with col1:
        stress_level = st.radio("스트레스 정도", ["하", "중", "상"], horizontal=True, key="stress_today")
    with col2:
        sleep_level = st.radio("평균 수면 상태", ["잘잠", "보통", "부족"], horizontal=True, key="sleep_today")

    st.subheader("📍 주요 증상 (해당되는 것을 모두 선택)")
    symptoms = st.multiselect(
        "현재 또는 예상되는 증상",
        ["쥐어짜는 듯한 통증", "붓기/부종", "허리 통증", "두통", "일반적인 둔통"],
    )

    last_period_date = st.date_input("최근 생리 시작일", value=date.today() - timedelta(days=20))
    avg_cycle = st.number_input("평소 평균 주기(일)", min_value=20, max_value=45, value=28)

    predict_btn = st.button("🔮 다음 주기 예측 및 약물 추천 받기")

    # ============================================================
    # 5. AI 기반 예측 + 추천 알고리즘 (핵심 로직)
    # ============================================================
    if predict_btn:
        st.divider()
        st.header("📊 예측 결과")

        # ---- (A) 동적 주기 예측 ----------------------------------
        # 가중치 = 프로파일링에서 결정된 '생활 영향 민감도'
        weight = SENSITIVITY_WEIGHT[st.session_state.lifestyle_sensitivity]

        # 보정치 = (스트레스 점수 + 수면 점수) × 가중치
        # → 민감도가 '없음'(0.1)인 사람은 스트레스가 '상'이어도 거의 보정 안 됨
        # → 민감도가 '많음'(1.0)인 사람은 그대로 보정 반영
        raw_adjustment = STRESS_SCORE[stress_level] + SLEEP_SCORE[sleep_level]
        adjustment_days = round(raw_adjustment * weight)

        # 불규칙 주기인 경우 예측 신뢰구간을 더 넓게 설정
        uncertainty = 3 if st.session_state.cycle_regularity == "불규칙" else 1

        predicted_date = last_period_date + timedelta(days=avg_cycle + adjustment_days)

        st.markdown(
            f"""
            <div class="info-box">
            <b>예상 다음 생리 시작일</b><br>
            📅 {predicted_date.strftime('%Y년 %m월 %d일')}
            （±{uncertainty}일 오차 범위）<br><br>
            <small>계산 근거: 평균 주기 {avg_cycle}일 + 컨디션 보정 {adjustment_days}일
            (민감도 가중치 {weight} 적용)</small>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ---- (B) 복용 타이밍 추천 ----------------------------------
        st.subheader("⏰ 맞춤형 복용 타이밍")
        if st.session_state.baseline_pain == "상":
            timing_msg = (
                f"평소 통증이 강한 편이시네요. 통증 유발 물질이 퍼지기 전, "
                f"**{(predicted_date - timedelta(days=1)).strftime('%m월 %d일')} 저녁** 또는 "
                f"**{predicted_date.strftime('%m월 %d일')} 아침**, 증상이 본격화되기 전에 "
                f"미리 복용하는 것을 권장해요."
            )
            st.markdown(f'<div class="alert-box">⚠️ {timing_msg}</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="info-box">평소 통증이 강하지 않은 편이므로, '
                '증상이 실제로 느껴질 때 복용해도 충분해요.</div>',
                unsafe_allow_html=True,
            )

        # ---- (C) 성분 추천 (과거 효과 없음 약물 필터링) -------------
        st.subheader("💊 맞춤형 성분 추천")

        # 증상 → 약물 매칭 점수 계산
        candidates = []
        for drug_name, info in DRUG_DB.items():
            # 1) 과거에 '효과 없음'으로 기록된 약물은 추천 후보에서 제외
            past_effect = st.session_state.drug_history.get(drug_name)
            if past_effect == "효과 없음":
                continue

            # 2) 현재 증상과 약물의 타겟이 얼마나 겹치는지 점수화
            score = 0
            symptom_map = {
                "쥐어짜는 듯한 통증": "쥐어짜는 통증",
                "붓기/부종": "붓기",
                "허리 통증": "허리 통증",
                "두통": "가벼운 통증",
                "일반적인 둔통": "일반 생리통",
            }
            for s in symptoms:
                mapped = symptom_map.get(s)
                if mapped and any(mapped in t for t in info["타겟"]):
                    score += 1

            # 3) 과거 '효과 좋음' 기록이 있으면 가중치 +2 (우선순위 상승)
            if past_effect == "효과 좋음":
                score += 2

            candidates.append((drug_name, info, score, past_effect))

        # 점수 높은 순 정렬
        candidates.sort(key=lambda x: x[2], reverse=True)

        if not candidates:
            st.warning("추천 가능한 약물이 없어요. 약사 또는 의사와 상담을 권장합니다.")
        else:
            top = candidates[0]
            st.markdown(
                f"""
                <div class="info-box">
                <b>1순위 추천: {top[0]}</b> ({top[1]['성분']})<br>
                {'✅ 과거 효과 좋음으로 기록된 약물이에요.' if top[3] == '효과 좋음' else ''}
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("다른 후보 약물 보기"):
                for name, info, score, eff in candidates[1:]:
                    st.write(f"- **{name}** ({info['성분']}) — 과거 기록: {eff or '없음'}")

            excluded = [d for d, e in st.session_state.drug_history.items() if e == "효과 없음"]
            if excluded:
                st.caption(f"🚫 과거 효과가 없었던 것으로 기록되어 제외된 약물: {', '.join(excluded)}")

        # ---- (D) 의료 면책 고지 ----------------------------------
        st.warning(
            "⚠️ 이 추천은 사용자가 입력한 데이터를 기반으로 한 참고용 정보이며, "
            "의학적 진단이나 처방을 대체하지 않습니다. 증상이 심하거나 지속되면 "
            "반드시 의사·약사와 상담하세요."
        )

    # --------------------------------------------------------
    # 6. 피드백 누적 (매달 복용 후 효과 입력 → drug_history 갱신)
    # --------------------------------------------------------
    st.divider()
    st.subheader("📝 이번 달 복용 피드백 남기기")
    st.caption("입력하신 효과는 다음 추천 때 자동으로 반영돼요.")

    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        fb_drug = st.selectbox("복용한 약물", list(DRUG_DB.keys()) + ["기타"])
    with fb_col2:
        fb_effect = st.radio("효과는 어땠나요?", ["효과 좋음", "보통", "효과 없음"], horizontal=True)

    if st.button("피드백 저장"):
        st.session_state.drug_history[fb_drug] = fb_effect
        st.success(f"'{fb_drug}'에 대한 피드백('{fb_effect}')이 저장되었어요. 다음 추천부터 반영됩니다.")
