import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from duckduckgo_search import DDGS
from config import OPENROUTER_BASE_URL, OPENROUTER_API_KEY, DEFAULT_ROLES

def get_client(api_key: Optional[str] = None) -> OpenAI:
    key = api_key or OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        raise ValueError("OpenRouter API key is missing. Set it in .env or the UI.")
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=key,
    )

def search_web_ddg(query: str, max_results: int = 6) -> List[Dict[str, str]]:
    """Executes live web search via DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return results
    except Exception as e:
        return [{"title": "Search Error", "body": str(e), "href": ""}]

class JobAssistant:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.client = get_client(api_key)
        self.model = model or DEFAULT_ROLES["job_hunter"]

    def find_openings(self, keywords: str, max_results: int = 8) -> str:
        """Searches live web for matching remote/entry openings and formats them."""
        # Query engineering for maximum recall on remote + entry/internship jobs
        query = (
            f'({keywords}) ("remote worldwide" OR "remote anywhere" OR "any location" OR "remote") '
            f'("entry level" OR "junior" OR "internship" OR "new grad") job'
        )
        raw_results = search_web_ddg(query, max_results=max_results)
        
        system_prompt = (
            "You are a Senior Technical Talent Scout. Analyze raw web search listings and extract clean, "
            "legitimate job postings matching entry-level, junior, internship, or remote positions.\n"
            "Format each job strictly in Markdown as:\n"
            "### [Job Title] - [Company Name]\n"
            "- **Location**: [e.g. Remote Worldwide / US / EU]\n"
            "- **Role Type**: [Entry Level / Junior / Internship]\n"
            "- **Key Tech Stack**: [e.g. Unity, C#, C++, Git]\n"
            "- **Summary**: [1-2 sentences on what they are looking for]\n"
            "- **Link**: [URL from results]\n"
            "---\n"
            "If no link exists, do not invent one. Omit irrelevant or spam links."
        )
        
        user_prompt = f"Target Keywords: {keywords}\nRaw Search Data:\n{json.dumps(raw_results, indent=2)}"
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or "No matching listings found."

    def mine_interview_intel(self, target_company_or_role: str) -> str:
        """Finds firsthand interview feedback and real test questions from Reddit and forums."""
        query = f'site:reddit.com ("{target_company_or_role}") ("interview questions" OR "technical test" OR "got the job" OR "rejected")'
        raw_experiences = search_web_ddg(query, max_results=6)
        
        system_prompt = (
            "You are an Elite Career Intelligence Analyst. Synthesize candidate experiences, Reddit threads, "
            "and forum posts about interviews for this role or company.\n"
            "Organize your report into:\n"
            "1. **Common Technical Questions Asked** (C#, Unity lifecycles, memory, shaders, DSA)\n"
            "2. **Take-Home or Live Coding Tests** (What was the format? Time limits? Gotchas?)\n"
            "3. **What Passed Candidates Did Right** (Stand-out projects, demo portfolios)\n"
            "4. **Red Flags & Warning Signs**\n"
            "Be direct, candid, and actionable."
        )
        
        user_prompt = f"Target Target/Company: {target_company_or_role}\nCommunity Data:\n{json.dumps(raw_experiences, indent=2)}"
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or "No interview reports available."

    def tailor_resume(self, master_profile: str, job_description: str) -> str:
        """Customizes master resume to match target job description with high ATS score."""
        system_prompt = (
            "You are an Elite Technical Resume Strategist and Former Lead Technical Recruiter.\n"
            "Your mission: Re-engineer the candidate's master profile to align with the target job description.\n"
            "Strict Rules:\n"
            "1. NEVER invent fictional experience, degrees, or tools the candidate did not list.\n"
            "2. Reframe existing bullet points using the Google 'Accomplished [X] as measured by [Y] by doing [Z]' framework.\n"
            "3. Front-load relevant technologies (e.g. Unity, C#, ShaderLab, Git, OOP, Data Structures) that match the JD.\n"
            "4. Include an optimized 'Professional Summary' tailored directly to this role.\n"
            "5. Output clean, ATS-compliant Markdown ready to export to PDF."
        )
        
        user_prompt = f"CANDIDATE MASTER PROFILE:\n{master_profile}\n\nTARGET JOB DESCRIPTION:\n{job_description}"
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content or "Failed to tailor resume."

    def mock_interview_reply(self, conversation_history: List[Dict[str, str]], user_answer: str) -> str:
        """Simulates a technical interview session, grading responses and asking the next question."""
        system_prompt = (
            "You are a Senior Principal Game & Software Engineer conducting a mock technical interview "
            "for an entry-level or junior Unity / Software Developer role.\n"
            "Flow:\n"
            "- If the candidate answers, evaluate their response with technical precision (point out edge cases, memory traps, or praise good design).\n"
            "- Then, ask the NEXT question (moving through OOP, C# internals, Unity game loop, or practical problem solving).\n"
            "- Keep questions realistic, challenging, and one question at a time."
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_answer})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""
