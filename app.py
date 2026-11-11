import streamlit as st
import os
import json
from agents.dev_team import DevSquad
from agents.job_hunter import JobAssistant
from config import MODELS, DEFAULT_ROLES

st.set_page_config(
    page_title="Hermes Autonomous Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for clean UI styling
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #4F46E5; margin-bottom: 0px; }
    .sub-title { font-size: 1.05rem; color: #6B7280; margin-bottom: 20px; }
    .agent-card { border-left: 4px solid #4F46E5; padding: 12px 16px; background-color: #F9FAFB; border-radius: 6px; margin-bottom: 12px; }
    .cost-badge { background-color: #DEF7EC; color: #03543F; padding: 4px 10px; border-radius: 9999px; font-size: 0.85rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SIDEBAR CONFIGURATION
# -------------------------------------------------------------
st.sidebar.markdown("## ⚡ Hermes Suite Controls")

# API Key handling
api_key_env = os.getenv("OPENROUTER_API_KEY", "")
api_key = st.sidebar.text_input(
    "OpenRouter API Key",
    value=api_key_env,
    type="password",
    help="Get this from openrouter.ai/keys (fund with $5-$10)"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🤖 Model Assignments")

col_m1, col_m2 = st.sidebar.columns(2)
leader_model = st.sidebar.selectbox(
    "Leader (Architect)",
    options=list(MODELS.values()),
    index=list(MODELS.values()).index(DEFAULT_ROLES["leader"]) if DEFAULT_ROLES["leader"] in MODELS.values() else 0
)

code_maker_model = st.sidebar.selectbox(
    "Code Maker",
    options=list(MODELS.values()),
    index=list(MODELS.values()).index(DEFAULT_ROLES["code_maker"]) if DEFAULT_ROLES["code_maker"] in MODELS.values() else 3,
    help="Hermes 70B or Qwen 2.5 Coder 32B recommended"
)

code_rev_model = st.sidebar.selectbox(
    "Code Reviewer",
    options=list(MODELS.values()),
    index=list(MODELS.values()).index(DEFAULT_ROLES["code_reviewer"]) if DEFAULT_ROLES["code_reviewer"] in MODELS.values() else 0
)

ui_maker_model = st.sidebar.selectbox(
    "UI Maker",
    options=list(MODELS.values()),
    index=list(MODELS.values()).index(DEFAULT_ROLES["ui_maker"]) if DEFAULT_ROLES["ui_maker"] in MODELS.values() else 0
)

ui_rev_model = st.sidebar.selectbox(
    "UI Reviewer",
    options=list(MODELS.values()),
    index=list(MODELS.values()).index(DEFAULT_ROLES["ui_reviewer"]) if DEFAULT_ROLES["ui_reviewer"] in MODELS.values() else 1
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="font-size: 0.85rem; color: #64748B;">
<b>💡 Token Economy Tip:</b><br>
Using Hermes 70B & Qwen Coder runs 150 monthly tasks for roughly <b>$3.00 - $5.00 total</b>.
No weekly throttling limits!
</div>
""", unsafe_allow_html=True)

role_config = {
    "leader": leader_model,
    "code_maker": code_maker_model,
    "code_reviewer": code_rev_model,
    "ui_maker": ui_maker_model,
    "ui_reviewer": ui_rev_model,
    "job_hunter": leader_model,
}

# -------------------------------------------------------------
# MAIN APP TABS
# -------------------------------------------------------------
st.markdown('<div class="main-title">Hermes Autonomous Agent Suite</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">High-efficiency, zero-refusal AI agents for Game/Software Engineering & Career Intelligence</div>', unsafe_allow_html=True)

tab_dev, tab_jobs, tab_interview = st.tabs([
    "🎮 5-Agent Dev Squad", 
    "💼 Job Hunter & Resume Tailor", 
    "🎙️ Mock Technical Interview"
])

# =============================================================
# TAB 1: 5-AGENT DEV SQUAD
# =============================================================
with tab_dev:
    st.markdown("### 5-Agent Autonomous Software & Game Development Team")
    st.markdown("Run full architectural planning, code authoring, code review, UI development, and UX validation in a continuous loop.")

    dev_task = st.text_area(
        "Describe your Feature or Bugfix:",
        placeholder="e.g. Build an inventory grid system in Unity C# using ScriptableObjects for item definitions, complete with stack count, tooltip on hover, and custom UI Toolkit layout.",
        height=100
    )

    project_ctx = st.text_input(
        "Project Context (Optional):",
        placeholder="e.g. 2D Platformer, Unity 2023.3 LTS, Input System package installed."
    )

    if st.button("🚀 Launch Dev Squad Pipeline", type="primary", use_container_width=True):
        if not api_key:
            st.error("Please enter your OpenRouter API Key in the left sidebar.")
        elif not dev_task.strip():
            st.warning("Please provide a task description.")
        else:
            try:
                squad = DevSquad(api_key=api_key, role_models=role_config)
                progress_bar = st.progress(0)
                status_text = st.empty()
                results_container = st.container()

                accumulated_output = {}

                for event in squad.run_squad(dev_task, project_ctx):
                    step = event["step"]
                    progress_bar.progress(step / 5)
                    
                    if "output" in event:
                        accumulated_output[event["agent"]] = event["output"]
                        with results_container:
                            with st.expander(f"✅ Step {step}: {event['agent']} ({event['model']})", expanded=(step in [2, 3])):
                                st.markdown(event["output"])
                    else:
                        status_text.info(f"⏳ **Step {step}/5: {event['agent']}** is working... ({event['status']})")

                status_text.success("🎉 Dev Squad Pipeline Completed Successfully!")
                progress_bar.progress(1.0)

                # Export full markdown
                full_export = f"# Task: {dev_task}\n\n"
                for agent_name, text in accumulated_output.items():
                    full_export += f"## {agent_name}\n\n{text}\n\n---\n\n"

                st.download_button(
                    label="📥 Download Full Output as Markdown",
                    data=full_export,
                    file_name="dev_squad_output.md",
                    mime="text/markdown"
                )

            except Exception as e:
                st.error(f"Error executing squad: {str(e)}")

# =============================================================
# TAB 2: JOB HUNTER & RESUME TAILOR
# =============================================================
with tab_jobs:
    st.markdown("### Career Intelligence & Job Hunting Assistant")
    
    subtab_find, subtab_intel, subtab_resume = st.tabs([
        "🔍 Find Openings", 
        "🕵️ Mine Interview Intel (Reddit/Forums)", 
        "📝 Tailor Resume (ATS Optimizer)"
    ])

    with subtab_find:
        st.markdown("#### Live Web Search for Remote Entry-Level Openings")
        col_kw1, col_kw2 = st.columns([3, 1])
        with col_kw1:
            job_keywords = st.text_input(
                "Search Keywords",
                value="Unity developer OR game developer OR software developer entry level"
            )
        with col_kw2:
            num_results = st.number_input("Max Listings", min_value=3, max_value=15, value=8)

        if st.button("🔎 Scan Live Openings", type="primary"):
            if not api_key:
                st.error("Please enter your OpenRouter API Key in the sidebar.")
            else:
                with st.spinner("Scanning web sources via DuckDuckGo and extracting with Hermes..."):
                    try:
                        assistant = JobAssistant(api_key=api_key, model=leader_model)
                        openings = assistant.find_openings(job_keywords, max_results=num_results)
                        st.markdown(openings)
                    except Exception as e:
                        st.error(f"Search failed: {str(e)}")

    with subtab_intel:
        st.markdown("#### Firsthand Technical Interview Experience Mining")
        st.markdown("Uncover what questions are actually asked and what past candidates experienced on Reddit and forums.")
        
        target_role_company = st.text_input(
            "Company or Role Target",
            placeholder="e.g. Junior Unity Developer or Ubisoft Technical Interview"
        )
        
        if st.button("🕵️ Extract Interview Intel"):
            if not api_key:
                st.error("Please enter your OpenRouter API Key in the sidebar.")
            elif not target_role_company.strip():
                st.warning("Please enter a target company or role.")
            else:
                with st.spinner("Mining Reddit and forums for candidate reports..."):
                    try:
                        assistant = JobAssistant(api_key=api_key, model=leader_model)
                        intel = assistant.mine_interview_intel(target_role_company)
                        st.markdown(intel)
                    except Exception as e:
                        st.error(f"Intelligence extraction failed: {str(e)}")

    with subtab_resume:
        st.markdown("#### ATS Resume Tailor")
        st.markdown("Adapt your master background to perfectly hit the keywords and requirements of a target job.")

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            master_resume = st.text_area(
                "Your Master Experience & Projects:",
                height=250,
                placeholder="Paste your general resume, GitHub project summaries, C#/Unity skills, education..."
            )
        with col_r2:
            target_jd = st.text_area(
                "Target Job Description (JD):",
                height=250,
                placeholder="Paste the target job description requirements, responsibilities, and qualifications..."
            )

        if st.button("📄 Generate Tailored ATS Resume", type="primary"):
            if not api_key:
                st.error("Please enter your OpenRouter API Key in the sidebar.")
            elif not master_resume.strip() or not target_jd.strip():
                st.warning("Please provide both your master profile and the job description.")
            else:
                with st.spinner("Hermes is aligning keywords and engineering impact bullet points..."):
                    try:
                        assistant = JobAssistant(api_key=api_key, model=leader_model)
                        tailored = assistant.tailor_resume(master_resume, target_jd)
                        st.markdown("### Tailored Resume")
                        st.markdown(tailored)
                        st.download_button(
                            label="📥 Download Tailored Resume (.md)",
                            data=tailored,
                            file_name="tailored_resume.md",
                            mime="text/markdown"
                        )
                    except Exception as e:
                        st.error(f"Resume tailoring failed: {str(e)}")

# =============================================================
# TAB 3: MOCK TECHNICAL INTERVIEW
# =============================================================
with tab_interview:
    st.markdown("### Interactive Technical Mock Interview")
    st.markdown("Practice technical drills for C#, Unity lifecycles, and software engineering with an uncompromising AI lead engineer.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display past messages
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_reply = st.chat_input("Type your response to the interviewer...")

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("🔄 Start New Interview"):
            st.session_state.chat_history = []
            st.rerun()

    if user_reply:
        if not api_key:
            st.error("Please enter your OpenRouter API Key in the sidebar.")
        else:
            # Display user message
            with st.chat_message("user"):
                st.markdown(user_reply)
            
            with st.chat_message("assistant"):
                with st.spinner("Evaluating your response..."):
                    try:
                        assistant = JobAssistant(api_key=api_key, model=leader_model)
                        response = assistant.mock_interview_reply(
                            conversation_history=st.session_state.chat_history,
                            user_answer=user_reply
                        )
                        st.markdown(response)
                        # Save state
                        st.session_state.chat_history.append({"role": "user", "content": user_reply})
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"Interview response failed: {str(e)}")
