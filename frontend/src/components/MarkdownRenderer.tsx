"use client";

import React, { useState } from "react";
import { applyCodeToWorkspace } from "@/lib/api";

interface MarkdownRendererProps {
  content: string;
  workspacePath?: string;
  onOpenWorkspaceModal?: () => void;
  onFileApplied?: (relativePath: string, fullPath: string) => void;
}

interface CodeBlockProps {
  language: string;
  code: string;
  workspacePath?: string;
  onOpenWorkspaceModal?: () => void;
  onFileApplied?: (relativePath: string, fullPath: string) => void;
}

function inferDefaultRelativePath(language: string, code: string): string {
  const lines = code.split("\n").slice(0, 5);
  for (const line of lines) {
    const match = line.match(
      /(?:\/\/|#|\/\*|--)\s*(?:File|Path|Target|Filename):\s*([^\s*]+\.[a-zA-Z0-9]+)/i
    );
    if (match && match[1]) {
      return match[1].trim().replace(/^\/+/, "");
    }
  }

  const lang = language.toLowerCase();
  if (lang === "csharp" || lang === "cs" || lang === "c#") {
    const classMatch = code.match(
      /(?:public|internal|sealed|abstract)?\s*(?:sealed|abstract|partial)?\s*(?:class|struct|interface|enum)\s+([A-Za-z0-9_]+)/
    );
    if (classMatch && classMatch[1]) {
      return `Assets/Scripts/${classMatch[1]}.cs`;
    }
    return "Assets/Scripts/NewBehaviourScript.cs";
  }
  if (lang === "shader" || lang === "hlsl" || lang === "shaderlab") {
    return "Assets/Shaders/CustomEffect.shader";
  }
  if (lang === "python" || lang === "py") {
    return "scripts/automation_pipeline.py";
  }
  if (lang === "bash" || lang === "sh" || lang === "zsh") {
    return "scripts/run_pipeline.sh";
  }
  if (lang === "tsx" || lang === "ts" || lang === "typescript") {
    return "src/components/GeneratedComponent.tsx";
  }
  if (lang === "json") {
    return "config/settings.json";
  }
  return `generated_snippet.${lang || "txt"}`;
}

function formatLanguageBadge(lang: string): string {
  const l = lang.toLowerCase().trim();
  const map: Record<string, string> = {
    csharp: "C# / Unity",
    cs: "C# / Unity",
    "c#": "C# / Unity",
    python: "Python 3",
    py: "Python 3",
    shader: "ShaderLab / HLSL",
    shaderlab: "ShaderLab / HLSL",
    hlsl: "HLSL Shader",
    bash: "Bash / Shell",
    sh: "Shell Script",
    zsh: "Zsh Script",
    json: "JSON",
    typescript: "TypeScript",
    ts: "TypeScript",
    tsx: "React TSX",
    javascript: "JavaScript",
    js: "JavaScript",
    uxml: "Unity UXML",
    uss: "Unity USS",
    sql: "SQL",
    markdown: "Markdown",
    md: "Markdown",
  };
  return map[l] || (l ? l.toUpperCase() : "CODE");
}

function highlightCodeLine(line: string): React.ReactNode {
  const trimmed = line.trim();
  if (
    trimmed.startsWith("//") ||
    (trimmed.startsWith("#") &&
      !trimmed.startsWith("#include") &&
      !trimmed.startsWith("#pragma") &&
      !trimmed.startsWith("#region") &&
      !trimmed.startsWith("#if") &&
      !trimmed.startsWith("#endif"))
  ) {
    return <span className="text-zinc-500 italic">{line}</span>;
  }

  const tokenRegex =
    /("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\[SerializeField[^\]]*\]|\[Header[^\]]*\]|\[Range[^\]]*\]|\[RequireComponent[^\]]*\]|\b(?:using|namespace|public|private|protected|internal|sealed|abstract|static|readonly|const|void|int|float|double|bool|string|var|class|struct|interface|enum|return|if|else|for|foreach|while|switch|case|break|continue|new|true|false|null|async|await|try|catch|finally|def|import|from|as|pass|yield|lambda|self|None|True|False|export|default|function|let|type|Shader|Properties|SubShader|Pass|CGPROGRAM|ENDCG|HLSLPROGRAM|ENDHLSL)\b|\b(?:MonoBehaviour|ScriptableObject|Vector2|Vector3|Vector4|Quaternion|Transform|GameObject|Rigidbody|Coroutine|IEnumerator|Time|Mathf|Debug|SerializeField|Action|List|Dictionary|Task)\b|\b\d+(?:\.\d+)?f?\b)/g;

  const parts = line.split(tokenRegex);
  if (parts.length === 1) return line;

  const keywords = new Set([
    "using",
    "namespace",
    "public",
    "private",
    "protected",
    "internal",
    "sealed",
    "abstract",
    "static",
    "readonly",
    "const",
    "void",
    "class",
    "struct",
    "interface",
    "enum",
    "return",
    "if",
    "else",
    "for",
    "foreach",
    "while",
    "switch",
    "case",
    "break",
    "continue",
    "new",
    "async",
    "await",
    "try",
    "catch",
    "finally",
    "def",
    "import",
    "from",
    "as",
    "pass",
    "yield",
    "lambda",
    "export",
    "default",
    "function",
    "let",
    "var",
    "type",
    "Shader",
    "Properties",
    "SubShader",
    "Pass",
    "CGPROGRAM",
    "ENDCG",
    "HLSLPROGRAM",
    "ENDHLSL",
  ]);

  const typesAndBuiltins = new Set([
    "int",
    "float",
    "double",
    "bool",
    "string",
    "true",
    "false",
    "null",
    "self",
    "None",
    "True",
    "False",
    "MonoBehaviour",
    "ScriptableObject",
    "Vector2",
    "Vector3",
    "Vector4",
    "Quaternion",
    "Transform",
    "GameObject",
    "Rigidbody",
    "Coroutine",
    "IEnumerator",
    "Time",
    "Mathf",
    "Debug",
    "SerializeField",
    "Action",
    "List",
    "Dictionary",
    "Task",
  ]);

  return parts.map((part, i) => {
    if (!part) return null;
    if (
      (part.startsWith('"') && part.endsWith('"')) ||
      (part.startsWith("'") && part.endsWith("'"))
    ) {
      return (
        <span key={i} className="text-amber-200/90">
          {part}
        </span>
      );
    }
    if (part.startsWith("[") && part.endsWith("]")) {
      return (
        <span key={i} className="text-zinc-400">
          {part}
        </span>
      );
    }
    if (keywords.has(part)) {
      return (
        <span key={i} className="text-sky-300 font-medium">
          {part}
        </span>
      );
    }
    if (typesAndBuiltins.has(part)) {
      return (
        <span key={i} className="text-zinc-100 font-medium">
          {part}
        </span>
      );
    }
    if (/^\d+(?:\.\d+)?f?$/.test(part)) {
      return (
        <span key={i} className="text-orange-300">
          {part}
        </span>
      );
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}

function RichCodeBlock({
  language,
  code,
  workspacePath,
  onOpenWorkspaceModal,
  onFileApplied,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [showApplyBar, setShowApplyBar] = useState(false);
  const [relativePath, setRelativePath] = useState(() =>
    inferDefaultRelativePath(language, code)
  );
  const [applying, setApplying] = useState(false);
  const [applyStatus, setApplyStatus] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const cleanCode = code.replace(/\n$/, "");
  const lines = cleanCode.split("\n");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(cleanCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  const handleApplyToWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspacePath) {
      if (onOpenWorkspaceModal) onOpenWorkspaceModal();
      return;
    }
    if (!relativePath.trim()) return;

    setApplying(true);
    setApplyStatus(null);
    try {
      const res = await applyCodeToWorkspace({
        workspace_path: workspacePath,
        relative_path: relativePath.trim(),
        content: cleanCode,
      });
      setApplyStatus({
        type: "success",
        text: `Saved to ${res.relative_path} (${res.bytes_written} bytes)`,
      });
      if (onFileApplied) {
        onFileApplied(res.relative_path, res.full_path);
      }
      setTimeout(() => {
        setShowApplyBar(false);
      }, 2200);
    } catch (err) {
      setApplyStatus({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to write file",
      });
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="my-3.5 rounded-xl border border-zinc-800/90 bg-[#111111] overflow-hidden">
      {/* Top Code Header Bar */}
      <div className="flex items-center justify-between px-3.5 py-2 bg-[#1A1A1A] border-b border-zinc-800/80">
        <div className="flex items-center gap-2.5">
          <span className="text-[11px] font-mono font-medium text-zinc-300">
            {formatLanguageBadge(language)}
          </span>
          <span className="text-[11px] font-mono text-zinc-500">
            {lines.length} {lines.length === 1 ? "line" : "lines"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setApplyStatus(null);
              setShowApplyBar((prev) => !prev);
            }}
            className="px-2.5 py-1 rounded-md text-xs font-medium bg-[#262626] hover:bg-[#303030] text-zinc-200 transition-colors"
          >
            Apply to Workspace
          </button>

          <button
            type="button"
            onClick={handleCopy}
            className="px-2.5 py-1 rounded-md text-xs font-medium bg-[#262626] hover:bg-[#303030] text-zinc-300 transition-colors"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>

      {/* Interactive Apply to Workspace drawer */}
      {showApplyBar && (
        <div className="px-3.5 py-2.5 bg-[#181818] border-b border-zinc-800">
          {!workspacePath ? (
            <div className="flex items-center justify-between gap-3 text-xs">
              <span className="text-zinc-400">
                No active local workspace folder is assigned yet.
              </span>
              {onOpenWorkspaceModal && (
                <button
                  type="button"
                  onClick={onOpenWorkspaceModal}
                  className="px-3 py-1 rounded-md bg-zinc-200 hover:bg-white text-zinc-900 font-medium shrink-0 transition-colors"
                >
                  Assign Folder
                </button>
              )}
            </div>
          ) : (
            <form
              onSubmit={handleApplyToWorkspace}
              className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2"
            >
              <div className="text-xs text-zinc-400 shrink-0 font-mono truncate max-w-[180px]">
                {workspacePath.split("/").pop()}/
              </div>
              <input
                type="text"
                value={relativePath}
                onChange={(e) => setRelativePath(e.target.value)}
                placeholder="Assets/Scripts/MyScript.cs"
                className="flex-1 px-2.5 py-1 rounded-md bg-[#111111] border border-zinc-700/80 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
              />
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  type="submit"
                  disabled={applying || !relativePath.trim()}
                  className="px-3 py-1 rounded-md bg-zinc-200 hover:bg-white disabled:opacity-50 text-xs font-medium text-zinc-900 transition-colors"
                >
                  {applying ? "Writing..." : "Write File"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowApplyBar(false)}
                  className="px-2 py-1 rounded-md text-xs text-zinc-400 hover:text-zinc-200"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
          {applyStatus && (
            <div
              className={`mt-2 text-xs font-mono ${
                applyStatus.type === "success"
                  ? "text-zinc-300"
                  : "text-rose-400"
              }`}
            >
              {applyStatus.text}
            </div>
          )}
        </div>
      )}

      {/* Code Lines with Line Numbers */}
      <div className="overflow-x-auto py-3 px-2 font-mono text-[12.5px] leading-relaxed">
        <table className="w-full border-collapse">
          <tbody>
            {lines.map((line, idx) => (
              <tr key={idx} className="hover:bg-zinc-900/50 transition-colors">
                <td className="select-none pr-3 pl-2 text-right text-[11px] text-zinc-600 w-9 align-top">
                  {idx + 1}
                </td>
                <td className="pr-4 text-zinc-200 whitespace-pre">
                  {highlightCodeLine(line)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function renderInlineFormatting(text: string): React.ReactNode {
  const parts = text.split(
    /(`[^`]+`|\*\*[^*]+\*\*|\*[^*\n]+\*|\[[^\]]+\]\([^)]+\))/g
  );

  return parts.map((part, index) => {
    if (!part) return null;
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return (
        <code
          key={index}
          className="px-1.5 py-0.5 mx-0.5 rounded bg-[#262626] font-mono text-[12px] text-zinc-200"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return (
        <strong key={index} className="font-semibold text-zinc-100">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      return (
        <em key={index} className="italic text-zinc-300">
          {part.slice(1, -1)}
        </em>
      );
    }
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      return (
        <a
          key={index}
          href={linkMatch[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-zinc-200 hover:text-white underline underline-offset-2"
        >
          {linkMatch[1]}
        </a>
      );
    }
    return <React.Fragment key={index}>{part}</React.Fragment>;
  });
}

export default function MarkdownRenderer({
  content,
  workspacePath,
  onOpenWorkspaceModal,
  onFileApplied,
}: MarkdownRendererProps) {
  if (!content) return null;

  const segments: Array<
    | { type: "code"; language: string; code: string }
    | { type: "prose"; text: string }
  > = [];

  const codeBlockRegex = /```([a-zA-Z0-9_+#-]*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      segments.push({
        type: "prose",
        text: content.slice(lastIndex, match.index),
      });
    }
    segments.push({
      type: "code",
      language: match[1] || "text",
      code: match[2] || "",
    });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    segments.push({
      type: "prose",
      text: content.slice(lastIndex),
    });
  }

  const renderProse = (prose: string, segIdx: number) => {
    const lines = prose.split("\n");
    const elements: React.ReactNode[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];
      const trimmed = line.trim();

      if (!trimmed) {
        i++;
        continue;
      }

      if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
        elements.push(
          <hr
            key={`${segIdx}-hr-${i}`}
            className="my-4 border-t border-zinc-800/80"
          />
        );
        i++;
        continue;
      }

      if (trimmed.startsWith("# ")) {
        elements.push(
          <h1
            key={`${segIdx}-h1-${i}`}
            className="text-lg font-semibold text-zinc-100 mt-4 mb-2 tracking-tight"
          >
            {renderInlineFormatting(trimmed.slice(2))}
          </h1>
        );
        i++;
        continue;
      }
      if (trimmed.startsWith("## ")) {
        elements.push(
          <h2
            key={`${segIdx}-h2-${i}`}
            className="text-base font-semibold text-zinc-100 mt-4 mb-2 tracking-tight border-b border-zinc-800/60 pb-1"
          >
            {renderInlineFormatting(trimmed.slice(3))}
          </h2>
        );
        i++;
        continue;
      }
      if (trimmed.startsWith("### ")) {
        elements.push(
          <h3
            key={`${segIdx}-h3-${i}`}
            className="text-sm font-semibold text-zinc-200 mt-3.5 mb-1.5"
          >
            {renderInlineFormatting(trimmed.slice(4))}
          </h3>
        );
        i++;
        continue;
      }
      if (trimmed.startsWith("#### ")) {
        elements.push(
          <h4
            key={`${segIdx}-h4-${i}`}
            className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mt-3 mb-1"
          >
            {renderInlineFormatting(trimmed.slice(5))}
          </h4>
        );
        i++;
        continue;
      }

      if (
        trimmed.startsWith("|") &&
        trimmed.endsWith("|") &&
        i + 1 < lines.length &&
        lines[i + 1].trim().includes("---")
      ) {
        const headerCells = trimmed
          .slice(1, -1)
          .split("|")
          .map((c) => c.trim());
        i += 2;
        const bodyRows: string[][] = [];
        while (
          i < lines.length &&
          lines[i].trim().startsWith("|") &&
          lines[i].trim().endsWith("|")
        ) {
          bodyRows.push(
            lines[i]
              .trim()
              .slice(1, -1)
              .split("|")
              .map((c) => c.trim())
          );
          i++;
        }
        elements.push(
          <div
            key={`${segIdx}-tbl-${i}`}
            className="my-3 overflow-x-auto rounded-lg border border-zinc-800/80"
          >
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#1A1A1A] text-zinc-300 border-b border-zinc-800">
                <tr>
                  {headerCells.map((cell, cIdx) => (
                    <th key={cIdx} className="py-2 px-3 font-semibold">
                      {renderInlineFormatting(cell)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 bg-[#141414]">
                {bodyRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-zinc-900/40">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="py-2 px-3 text-zinc-300">
                        {renderInlineFormatting(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }

      if (trimmed.startsWith("> ")) {
        const quoteLines: string[] = [];
        while (i < lines.length && lines[i].trim().startsWith(">")) {
          quoteLines.push(lines[i].trim().replace(/^>\s?/, ""));
          i++;
        }
        elements.push(
          <blockquote
            key={`${segIdx}-quote-${i}`}
            className="my-2.5 pl-3.5 py-1 border-l-2 border-zinc-600 bg-[#1A1A1A] rounded-r-md text-zinc-300 text-xs leading-relaxed"
          >
            {quoteLines.map((ql, qIdx) => (
              <p key={qIdx} className="my-0.5">
                {renderInlineFormatting(ql)}
              </p>
            ))}
          </blockquote>
        );
        continue;
      }

      if (/^[-*+]\s+/.test(trimmed)) {
        const listItems: string[] = [];
        while (i < lines.length && /^[-*+]\s+/.test(lines[i].trim())) {
          listItems.push(lines[i].trim().replace(/^[-*+]\s+/, ""));
          i++;
        }
        elements.push(
          <ul
            key={`${segIdx}-ul-${i}`}
            className="my-2 space-y-1.5 pl-5 list-disc marker:text-zinc-500 text-zinc-300 text-[13.5px] leading-relaxed"
          >
            {listItems.map((item, idx) => (
              <li key={idx}>{renderInlineFormatting(item)}</li>
            ))}
          </ul>
        );
        continue;
      }

      if (/^\d+\.\s+/.test(trimmed)) {
        const listItems: string[] = [];
        while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
          listItems.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
          i++;
        }
        elements.push(
          <ol
            key={`${segIdx}-ol-${i}`}
            className="my-2 space-y-1.5 pl-5 list-decimal marker:text-zinc-500 marker:font-mono text-zinc-300 text-[13.5px] leading-relaxed"
          >
            {listItems.map((item, idx) => (
              <li key={idx}>{renderInlineFormatting(item)}</li>
            ))}
          </ol>
        );
        continue;
      }

      elements.push(
        <p
          key={`${segIdx}-p-${i}`}
          className="my-2 text-zinc-200 text-[13.5px] leading-relaxed"
        >
          {renderInlineFormatting(line)}
        </p>
      );
      i++;
    }

    return elements;
  };

  return (
    <div className="space-y-1">
      {segments.map((seg, idx) =>
        seg.type === "code" ? (
          <RichCodeBlock
            key={idx}
            language={seg.language}
            code={seg.code}
            workspacePath={workspacePath}
            onOpenWorkspaceModal={onOpenWorkspaceModal}
            onFileApplied={onFileApplied}
          />
        ) : (
          <React.Fragment key={idx}>
            {renderProse(seg.text, idx)}
          </React.Fragment>
        )
      )}
    </div>
  );
}
