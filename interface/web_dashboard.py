import streamlit as st
import pandas as pd
import plotly.express as px
import json
import time
from pathlib import Path

# ==========================================
# 1. 페이지 설정 및 제목
# ==========================================
st.set_page_config(page_title="Mastermind AI 관제 센터", layout="wide")
st.markdown("<h3 style='text-align: center; margin-top: -30px;'>⚾ Mastermind AI 관제 센터</h3>", unsafe_allow_html=True)

# ==========================================
# 2. 세션 상태머신 엔진
# ==========================================
if "live_mode" not in st.session_state:
    st.session_state.live_mode = True
if "selected_log" not in st.session_state:
    st.session_state.selected_log = None
if "standby" not in st.session_state:
    st.session_state.standby = True
if "baseline_mtime" not in st.session_state:
    st.session_state.baseline_mtime = None

def toggle_live():
    if st.session_state.live_mode:
        st.session_state.selected_log = None
        st.session_state.standby = True       
        st.session_state.baseline_mtime = None

def select_history(filename):
    st.session_state.live_mode = False        
    st.session_state.selected_log = filename
    st.session_state.standby = False          

# ==========================================
# 3. 경로 스캔 및 파일 로드
# ==========================================
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent if current_file.parent.name == "interface" else current_file.parent
log_dir = project_root / "logs"

log_files = []
if log_dir.exists():
    log_files = sorted(list(log_dir.glob("*.jsonl")), key=lambda p: p.stat().st_ctime, reverse=True)

# ==========================================
# 4. 사이드바 UI
# ==========================================
st.sidebar.header("🕹️ Control Panel")

if not log_files:
    st.sidebar.warning("저장된 로그 파일이 없습니다.")
    st.stop()

st.sidebar.checkbox("🔴 Live (실시간 모니터링)", key="live_mode", on_change=toggle_live)

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("실시간 자동 갱신", value=True, disabled=not st.session_state.live_mode)
refresh_rate = st.sidebar.slider("갱신 주기 (초)", 0.5, 3.0, 1.0, disabled=not st.session_state.live_mode)

st.sidebar.markdown("### 📂 과거 로그 목록")

with st.sidebar.container(height=400):
    for f in log_files:
        btn_type = "primary" if st.session_state.selected_log == f.name else "secondary"
        st.button(f"📄 {f.name}", key=f"btn_{f.name}", on_click=select_history, args=(f.name,), type=btn_type, use_container_width=True)

# ==========================================
# 5. 데이터 변동 감지
# ==========================================
target_file = None

if st.session_state.live_mode:
    target_file = log_files[0]
    current_mtime = target_file.stat().st_mtime

    if st.session_state.baseline_mtime is None:
        st.session_state.baseline_mtime = current_mtime

    if current_mtime > st.session_state.baseline_mtime:
        st.session_state.standby = False
        st.session_state.baseline_mtime = current_mtime
else:
    if not st.session_state.selected_log:
        st.session_state.selected_log = log_files[0].name
    target_file = log_dir / st.session_state.selected_log

# ==========================================
# 6. 메인 화면 렌더링 (단일 컨테이너 강제 초기화 기법)
# ==========================================
# 이 빈 공간 하나만을 창구로 사용하여, 조건이 바뀔 때마다 무조건 다 때려 부수고 새로 짓습니다.
main_display = st.empty()

if st.session_state.standby:
    main_display.empty() # 프론트엔드 강제 철거
    with main_display.container():
        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        st.info("⏳ **새로운 시뮬레이션이 시작되기를 기다리고 있습니다...**\n\n(백엔드 스크립트를 실행하여 데이터가 기록되는 순간 대시보드가 나타납니다.)")
        # [핵심 방어막] 혹시라도 스트림릿 버그로 이전 차트가 살아남는다면 화면 최하단으로 밀어버립니다.
        st.markdown("<div style='height: 2000px;'></div>", unsafe_allow_html=True)
        
else:
    main_display.empty() # 차트를 그리기 전에도 무조건 철거 명령
    with main_display.container():
        history_data = []
        with open(target_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    history_data.append(json.loads(line))

        if not history_data:
            st.info("데이터가 비어 있습니다...")
        else:
            if not st.session_state.live_mode:
                st.success(f"📽️ **과거 로그 복기 모드(Replay)** 중입니다. (`{target_file.name}`)")

            latest_data = history_data[-1]
            turn = latest_data['turn']
            solver = latest_data['solver_name']
            remains = latest_data['dashboard_2_trend']['remaining_count']
            eval_data = latest_data['dashboard_3_evaluation']
            best_guess = latest_data.get('best_guess', [])

            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Solver", solver)
            m_col2.metric("Current Turn", f"Turn {turn}")
            m_col3.metric("Remaining Candidates", f"{remains}개")
            m_col4.metric("Best Guess", str(best_guess))

            st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

            row1_col1, row1_col2 = st.columns(2)
            with row1_col1:
                st.markdown("**📊 [Dash 1] 자릿수별 확률 히트맵 (%)**")
                probs = latest_data['dashboard_1_heatmap']['probabilities']
                num_pos = len(probs)
                matrix, annotations = [], []
                for d in range(10):
                    row_vals = [probs[pos][d] * 100 for pos in range(num_pos)]
                    matrix.append(row_vals)
                    text_row = []
                    for pos in range(num_pos):
                        val = row_vals[pos]
                        if best_guess and best_guess[pos] == d:
                            text_row.append(f"<b>[{val:.1f}%]</b>")
                        elif val > 0:
                            text_row.append(f"{val:.1f}%")
                        else:
                            text_row.append("-")
                    annotations.append(text_row)
                fig_heat = px.imshow(matrix, x=[f"Pos {i+1}" for i in range(num_pos)], y=[str(i) for i in range(10)], color_continuous_scale="YlOrRd", aspect="auto", range_color=[0, 100])
                fig_heat.update_traces(text=annotations, texttemplate="%{text}")
                fig_heat.update_yaxes(autorange="reversed", tickmode='linear', tick0=0, dtick=1)
                fig_heat.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=260)
                st.plotly_chart(fig_heat, use_container_width=True)

            with row1_col2:
                st.markdown("**📉 [Dash 2] 남은 정답 후보군 추이**")
                trend_df = pd.DataFrame([{"Turn": d["turn"], "Remaining": d["dashboard_2_trend"]["remaining_count"]} for d in history_data])
                fig_trend = px.line(trend_df, x="Turn", y="Remaining", markers=True)
                fig_trend.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=260)
                st.plotly_chart(fig_trend, use_container_width=True)

            row2_col1, row2_col2 = st.columns(2)
            with row2_col1:
                st.markdown(f"**🏆 [Dash 3] {eval_data.get('metric_name', 'Score')} 추천**")
                top_picks = eval_data.get('top_guesses', [])
                if not top_picks:
                    st.info("초반 전략(Seed) 적용 중: 탐색 데이터를 기다리고 있습니다.")
                else:
                    df_top = pd.DataFrame(top_picks)
                    df_top['guess'] = df_top['guess'].apply(lambda x: str(x))
                    df_top.index = df_top.index + 1
                    df_top.columns = ['추천 후보', '점수']
                    st.dataframe(df_top, use_container_width=True, height=180)

            with row2_col2:
                st.markdown("**🧐 [Dash 4] AI의 결정적 근거**")
                if solver == "EntropySolver":
                    splits = eval_data.get('expected_splits', [])
                    worst_comp = eval_data.get('worst_split_comparison', {})
                    if not splits:
                        st.warning("현재 턴은 고정 전략 구간이므로 상세 근거를 생성하지 않습니다.")
                    else:
                        st.markdown(f"✅ **[채택] {best_guess} (최고점)**<br>👉 최악 판정 `{splits[0][0][0]}S {splits[0][0][1]}B` 시 ➔ **{splits[0][1]}개** 남음", unsafe_allow_html=True)
                        st.markdown("<hr style='margin-top: 8px; margin-bottom: 8px;'>", unsafe_allow_html=True)
                        if worst_comp and worst_comp.get('splits'):
                            w_guess = worst_comp['guess']
                            w_splits = worst_comp['splits']
                            st.markdown(f"❌ **[비교] 만약 최하점 {w_guess} 공격 시?**<br>👉 똑같은 판정 `{w_splits[0][0][0]}S {w_splits[0][0][1]}B` 시 ➔ **무려 {w_splits[0][1]}개** 남음", unsafe_allow_html=True)
                        else:
                            st.caption("비교 데이터 계산 중...")
                elif solver == "MinimaxSolver":
                    splits = eval_data.get('expected_splits', [])
                    worst_comp = eval_data.get('worst_split_comparison', {})
                    
                    if not splits:
                        st.warning("현재 턴은 고정 전략 구간이므로 상세 근거를 생성하지 않습니다.")
                    else:
                        # Minimax의 splits[0]는 ["Worst-case", worst_case_count] 형태를 띰
                        st.markdown(f"✅ **[채택] {best_guess} (Worst-case 최소화)**<br>👉 어떤 판정이 나오더라도 최대 **{splits[0][1]}개** 이하로 방어", unsafe_allow_html=True)
                        st.markdown("<hr style='margin-top: 8px; margin-bottom: 8px;'>", unsafe_allow_html=True)
                        
                        if worst_comp and worst_comp.get('splits'):
                            w_guess = worst_comp['guess']
                            w_splits = worst_comp['splits']
                            st.markdown(f"❌ **[비교] 만약 최악의 수 {w_guess} 공격 시?**<br>👉 운이 나쁠 경우 ➔ 무려 **{w_splits[0][1]}개**나 남음", unsafe_allow_html=True)
                        else:
                            st.caption("비교 데이터 계산 중...")
                elif solver == "HeuristicSolver":
                    if remains <= 1:
                        st.info("정답 확정 단계입니다.")
                    else:
                        breakdown = [f"P{pos+1}[{digit}]: {probs[pos][digit] * remains:.1f}점" for pos, digit in enumerate(best_guess)]
                        st.markdown("✅ **빈도 가중치 합산 (가성비 1위)**")
                        st.caption(" + ".join(breakdown))

# ==========================================
# 7. 최하단 폴링
# ==========================================
if st.session_state.live_mode and auto_refresh:
    # 대기 모드일 때는 좀비 화면 방지를 위해 브라우저가 화면을 지울 시간을 넉넉히(1.5초) 줍니다.
    time.sleep(refresh_rate if not st.session_state.standby else 1.5)
    st.rerun()