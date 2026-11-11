# Hermes Autonomous Agent Suite ⚡

An autonomous, pay-as-you-go multi-agent system built for **Software & Game Engineering** and **Career Intelligence**, powered by **Nous Hermes 3** and specialized open-weights models via OpenRouter.

---

## 🎯 What This Suite Does

1. **5-Agent Autonomous Dev Squad**:
   - **Leader (Architect)**: Breaks down tasks into modular design specs.
   - **Code Maker**: Writes production-ready C#, Unity, or software code (powered by Qwen 2.5 Coder or Hermes 70B).
   - **Code Reviewer**: Hermes 3 70B reviewing for logic errors, GC allocations in game loops, and edge cases.
   - **UI Maker**: Generates responsive UI controllers and layout hierarchies.
   - **UI Reviewer**: Evaluates UX clarity, accessibility, and visual hierarchy.

2. **Career Intelligence & Job Hunter**:
   - **Live Openings Scanner**: Searches the web for remote entry-level, junior, and internship positions (`Unity developer`, `software developer`, `game developer`).
   - **Reddit / Forum Intelligence Miner**: Scrapes and synthesizes firsthand technical test feedback, interview questions, and candidate experiences.
   - **ATS Resume Tailor**: Adapts your master resume to match target job descriptions with keyword alignment.
   - **Mock Technical Interview Coach**: Interactive C# / Unity technical drills with an uncompromising AI lead engineer.

---

## 🚀 Quick Start Guide

### 1. Configure Your API Key
1. Get an API key from [OpenRouter](https://openrouter.ai/keys) and fund your account with **$5 - $10**.
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Open `.env` and paste your key:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here
   ```

### 2. Launch the Web Dashboard (GUI)
Run this command from inside the `hermes-agent-suite` folder:
```bash
source .venv/bin/activate
streamlit run app.py
```
Your browser will open automatically to `http://localhost:8501`.

---

## 💻 Command Line Interface (CLI)

If you prefer working directly from your terminal:

* **Run a Dev Squad Task**:
  ```bash
  source .venv/bin/activate
  python cli.py dev "Build an inventory grid system in Unity C# using ScriptableObjects"
  ```

* **Search Live Remote Job Openings**:
  ```bash
  python cli.py jobs "Unity developer entry level remote"
  ```

* **Mine Interview Experiences**:
  ```bash
  python cli.py intel "Junior Unity Developer technical interview"
  ```

---

## 💰 Economics: Why This Saves You Money
- **No Monthly $20 Subscription Lockouts**: Claude Pro rate limits you after 3-4 multi-agent tasks.
- **Pay Only for What You Use**: Hermes 70B costs ~$0.40/1M input tokens. Running 150 dev tasks and monthly job searches costs **~$3.00 to $5.00 total per month**.
