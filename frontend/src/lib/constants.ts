import { ModelDirectoryItem, WorkflowModeOption } from "./types";

export const WORKFLOW_MODES: WorkflowModeOption[] = [
  {
    id: "team:dev-squad",
    name: "Game/Soft Dev Team",
    shortLabel: "Game/Soft Dev Team",
    badge: "5-Agent Squad",
    category: "team",
    description:
      "Sequential 5-agent pipeline: Leader (DeepSeek V3) -> Code Maker (Qwen 32B) -> Reviewer (DeepSeek R1 Reasoning) -> UI Maker -> UI Reviewer.",
    agents: [
      { role: "Leader (Architect)", model: "deepseek/deepseek-chat" },
      { role: "Code Maker", model: "qwen/qwen-2.5-coder-32b-instruct" },
      { role: "Code Reviewer", model: "deepseek/deepseek-r1" },
      { role: "UI Maker", model: "qwen/qwen-2.5-coder-32b-instruct" },
      { role: "UI Reviewer", model: "google/gemini-2.5-flash" },
    ],
  },
  {
    id: "team:career-hunter",
    name: "Career Team",
    shortLabel: "Career Team",
    badge: "4-Agent Squad",
    category: "team",
    description:
      "Live job search (Hermes 4 + DuckDuckGo), Reddit interview intel (DeepSeek V3), ATS resume tailoring, and mock technical interviews.",
    agents: [
      { role: "Job Hunter (Live Web)", model: "nousresearch/hermes-4-70b" },
      { role: "Reddit Intel Miner", model: "deepseek/deepseek-chat" },
      { role: "ATS Resume Strategist", model: "nousresearch/hermes-4-70b" },
      { role: "Tech Interview Coach", model: "deepseek/deepseek-chat" },
    ],
  },
  {
    id: "team:content-video",
    name: "Content Team",
    shortLabel: "Content Team",
    badge: "3-Agent Squad",
    category: "team",
    description:
      "Unity Recorder C# scripts, macOS FFmpeg and MoviePy automated video editing pipelines, and YouTube SEO metadata.",
    agents: [
      { role: "Capture Engineer (Unity/FFmpeg)", model: "qwen/qwen-2.5-coder-32b-instruct" },
      { role: "Video Automation (MoviePy)", model: "qwen/qwen-2.5-coder-32b-instruct" },
      { role: "YouTube SEO Strategist", model: "deepseek/deepseek-chat" },
    ],
  },
  {
    id: "raw:deepseek-v3",
    name: "DeepSeek V3",
    shortLabel: "DeepSeek V3",
    badge: "Daily Workhorse",
    category: "raw",
    modelId: "deepseek/deepseek-chat",
    description:
      "Sonnet-grade coding and general systems reasoning at ultra-low cost ($0.14/M tokens). Your primary daily development driver.",
  },
  {
    id: "raw:qwen-coder-32b",
    name: "Qwen 2.5 Coder 32B",
    shortLabel: "Qwen 2.5 Coder 32B",
    badge: "C# & Unity Specialist",
    category: "raw",
    modelId: "qwen/qwen-2.5-coder-32b-instruct",
    description:
      "Specialist coding model tuned for Unity C#, MonoBehaviour architecture, shaders, and procedural sound code.",
  },
  {
    id: "raw:deepseek-r1",
    name: "DeepSeek R1",
    shortLabel: "DeepSeek R1",
    badge: "Reasoning & Bug Hunter",
    category: "raw",
    modelId: "deepseek/deepseek-r1",
    description:
      "Deep thinking chain-of-thought model. Solves complex physics, vector math, memory leaks, and impossible bugs.",
  },
  {
    id: "raw:gemini-pro",
    name: "Gemini 2.5 Pro",
    shortLabel: "Gemini 2.5 Pro",
    badge: "1M Token Project Analyzer",
    category: "raw",
    modelId: "google/gemini-2.5-pro",
    description:
      "Massive 1M+ token context window. Ingests entire game projects and multi-file codebases simultaneously.",
  },
  {
    id: "raw:gemini-flash",
    name: "Gemini 2.5 Flash",
    shortLabel: "Gemini 2.5 Flash",
    badge: "Sub-Second Fast Q&A",
    category: "raw",
    modelId: "google/gemini-2.5-flash",
    description:
      "Ultra-fast, sub-second responses for syntax checks, quick questions, and game music/audio prompt ideas.",
  },
  {
    id: "raw:hermes-70b",
    name: "Nous Hermes 4 70B",
    shortLabel: "Nous Hermes 4 70B",
    badge: "Autonomous & Uncensored",
    category: "raw",
    modelId: "nousresearch/hermes-4-70b",
    description:
      "Nous Research flagship 70B model for autonomous agent loops, strict JSON adherence, and career intelligence.",
  },
  {
    id: "raw:claude-sonnet",
    name: "Claude 3.5 Sonnet",
    shortLabel: "Claude 3.5 Sonnet",
    badge: "Frontier Benchmark",
    category: "raw",
    modelId: "anthropic/claude-3.5-sonnet",
    description:
      "Anthropic frontier model for complex multi-file refactoring and high-stakes tasks.",
  },
  {
    id: "raw:free-deepseek",
    name: "DeepSeek V3 (Free)",
    shortLabel: "DeepSeek V3 (Free)",
    badge: "100% Free Sandbox",
    category: "raw",
    modelId: "deepseek/deepseek-chat:free",
    description:
      "Free-tier endpoint on OpenRouter ($0.00 spend) for casual queries, practice, and non-critical tasks.",
  },
];

export const MODEL_DIRECTORY_DATA: ModelDirectoryItem[] = [
  {
    id: "deepseek-v3",
    name: "DeepSeek V3",
    provider: "DeepSeek",
    powerRating: "9.6 / 10",
    speedRating: "Fast",
    costLabel: "$0.14 in / $0.28 out",
    contextWindow: "128k tokens",
    roleBadge: "Daily Workhorse",
    specializedFor: [
      "Gameplay Architecture",
      "Game Lore & Narrative",
      "Music Composition Prompts (Suno/Udio)",
      "General C# & Python Systems",
    ],
    description:
      "Matches Claude 3.5 Sonnet across SWE-bench and coding while costing ~20x less. Perfect as your default daily driver for building software and game mechanics.",
  },
  {
    id: "qwen-coder-32b",
    name: "Qwen 2.5 Coder 32B",
    provider: "Alibaba Cloud",
    powerRating: "9.3 / 10",
    speedRating: "Very Fast",
    costLabel: "$0.20 in / $0.40 out",
    contextWindow: "131k tokens",
    roleBadge: "C# & Unity Specialist",
    specializedFor: [
      "Unity C# & MonoBehaviours",
      "UI Toolkit & Canvas Scripts",
      "Procedural Sound / AudioSource Code",
      "HLSL & ShaderLab Shaders",
    ],
    description:
      "Dedicated programming powerhouse trained directly on open-source code repositories. Writes idiomatic C# with zero conversational filler and strict memory awareness.",
  },
  {
    id: "deepseek-r1",
    name: "DeepSeek R1",
    provider: "DeepSeek",
    powerRating: "9.8 / 10",
    speedRating: "Deliberate",
    costLabel: "$0.55 in / $2.19 out",
    contextWindow: "128k tokens",
    roleBadge: "Bug Hunter & Physics Math",
    specializedFor: [
      "Impossible Bugs & Race Conditions",
      "3D Vector & Quaternion Math",
      "Physics Collision Glitches",
      "Garbage Collection Leak Audits",
    ],
    description:
      "Reasoning model with an internal chain-of-thought scratchpad. Best used when code compiles but physics behave abnormally, numbers drift, or game loops suffer frame drops.",
  },
  {
    id: "gemini-pro",
    name: "Google Gemini 2.5 Pro",
    provider: "Google",
    powerRating: "9.7 / 10",
    speedRating: "Moderate",
    costLabel: "$1.25 in / $5.00 out",
    contextWindow: "1,000,000+ tokens",
    roleBadge: "Whole-Project Context",
    specializedFor: [
      "Entire Codebase Ingestion (50-100+ scripts)",
      "Cross-File Dependency Audits",
      "Large GDD / Bible Lore Indexing",
      "Refactoring Inter-Class Architecture",
    ],
    description:
      "Industry-leading 1M+ token context window. Ingests your entire Unity Assets/Scripts folder in a single turn with flawless recall across distant files.",
  },
  {
    id: "gemini-flash",
    name: "Google Gemini 2.5 Flash",
    provider: "Google",
    powerRating: "8.8 / 10",
    speedRating: "Sub-Second",
    costLabel: "$0.075 in / $0.30 out",
    contextWindow: "1,000,000 tokens",
    roleBadge: "Instant Q&A & SFX Prompts",
    specializedFor: [
      "Quick Syntax & Function Explanations",
      "Console Error Diagnostic",
      "Sound FX Descriptors (ElevenLabs)",
      "Game SFX Freq / Pitch Presets",
    ],
    description:
      "Ultra-low latency with 1M tokens context. Delivers immediate responses for quick development questions and fast iteration on sound design prompts.",
  },
  {
    id: "hermes-70b",
    name: "Nous Hermes 4 70B",
    provider: "Nous Research",
    powerRating: "9.2 / 10",
    speedRating: "Fast",
    costLabel: "$0.40 in / $0.80 out",
    contextWindow: "131k tokens",
    roleBadge: "Agent & Career Scout",
    specializedFor: [
      "Autonomous Multi-Step Scraping",
      "ATS Resume Formatting (Google XYZ)",
      "Reddit Forum Intel Extraction",
      "Zero-Refusal Unaligned Execution",
    ],
    description:
      "Fine-tuned specifically for agentic loops and tool calling. Never lectures or adds moralizing disclaimers, executing strict JSON and structured schemas reliably.",
  },
  {
    id: "claude-sonnet",
    name: "Claude 3.5 Sonnet",
    provider: "Anthropic",
    powerRating: "9.9 / 10",
    speedRating: "Fast",
    costLabel: "$3.00 in / $15.00 out",
    contextWindow: "200k tokens",
    roleBadge: "Frontier Benchmark",
    specializedFor: [
      "Nuanced Creative UI Decisions",
      "High-Stakes Architecture Pivots",
      "Multi-File System Refactoring",
    ],
    description:
      "The gold standard for zero-shot coding and nuanced design. Ideal as an occasional on-demand escalation without recurring subscriptions.",
  },
  {
    id: "free-deepseek",
    name: "DeepSeek V3 (Free)",
    provider: "DeepSeek (OpenRouter Free Tier)",
    powerRating: "9.4 / 10",
    speedRating: "Variable",
    costLabel: "$0.00 / Free",
    contextWindow: "128k tokens",
    roleBadge: "Zero-Cost Sandbox",
    specializedFor: [
      "Practice & Casual Coding Queries",
      "Non-Critical Explanations",
      "Zero Balance Consumption",
    ],
    description:
      "Community free-tier endpoint provided by OpenRouter. Full DeepSeek intelligence at zero cost for non-urgent tasks and experimentation.",
  },
];

export const WORKSPACE_PRESETS = [
  {
    label: "Hermes Suite Repo",
    path: "/Users/Damid/.gemini/antigravity/scratch/hermes-agent-suite",
  },
  {
    label: "Scratch Projects",
    path: "/Users/Damid/.gemini/antigravity/scratch",
  },
  {
    label: "macOS Desktop",
    path: "~/Desktop",
  },
];
