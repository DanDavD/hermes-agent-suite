"""Unit & integration tests for Hermes Studio v2 Autonomous Executor & Token Optimization."""

import tempfile
import unittest
from pathlib import Path

from backend.database import (
    create_project,
    create_session,
    delete_project,
    delete_session,
    get_session,
    init_db,
)
from backend.services.autonomous_executor import (
    apply_autonomous_files,
    apply_search_replace_blocks,
    extract_files_from_markdown,
    generate_smart_session_title,
    run_automated_workspace_tests,
)
from backend.services.openrouter_client import _compact_history_content
from backend.services.workspace_scanner import build_workspace_context, estimate_tokens_from_text


class TestAutonomousExecutorAndTokenOptimization(unittest.TestCase):
    """Verifies local disk application, SEARCH/REPLACE patching, and token reduction."""

    def test_search_replace_surgical_patch_on_disk(self) -> None:
        """Verifies that SEARCH/REPLACE blocks surgically update existing files on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            js_dir = Path(tmpdir) / "js"
            js_dir.mkdir(parents=True, exist_ok=True)
            target_file = js_dir / "store.js"
            original_code = (
                "const store = {\n"
                "  currentUser: null,\n"
                "  showPassword: false,\n"
                "  activeRole: 'renter',\n"
                "};\n"
            )
            target_file.write_text(original_code, encoding="utf-8")

            llm_response = (
                "I have removed the redundant `showPassword` property from `js/store.js`:\n\n"
                "```javascript\n"
                "// File: js/store.js\n"
                "<<<<<<< SEARCH\n"
                "  currentUser: null,\n"
                "  showPassword: false,\n"
                "  activeRole: 'renter',\n"
                "=======\n"
                "  currentUser: null,\n"
                "  activeRole: 'renter',\n"
                ">>>>>>> REPLACE\n"
                "```\n"
            )

            actions = apply_autonomous_files(tmpdir, llm_response)
            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0]["type"], "file_written")
            self.assertEqual(actions[0]["status"], "patched")
            self.assertEqual(actions[0]["path"], "js/store.js")

            updated_disk = target_file.read_text(encoding="utf-8")
            self.assertNotIn("showPassword", updated_disk)
            self.assertIn("activeRole: 'renter'", updated_disk)

    def test_skips_before_comparison_code_blocks(self) -> None:
        """Ensures code blocks preceded by '**Before:**' are ignored and only 'After:' blocks apply."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markdown = (
                "**Before:**\n"
                "```javascript\n"
                "// File: js/app.js\n"
                "const oldApp = true;\n"
                "```\n\n"
                "**After:**\n"
                "```javascript\n"
                "// File: js/app.js\n"
                "const newApp = true;\n"
                "```\n"
            )
            extracted = extract_files_from_markdown(markdown)
            self.assertEqual(len(extracted), 1)
            self.assertEqual(extracted[0][0], "js/app.js")
            self.assertIn("const newApp = true;", extracted[0][1])

            actions = apply_autonomous_files(tmpdir, markdown)
            self.assertEqual(len(actions), 1)
            written = (Path(tmpdir) / "js" / "app.js").read_text(encoding="utf-8")
            self.assertIn("const newApp = true;", written)
            self.assertNotIn("oldApp", written)

    def test_web_extensions_html_css_js_supported(self) -> None:
        """Verifies HTML, CSS, and JS files are extracted and written to disk cleanly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markdown = (
                "```html\n"
                "<!-- File: index.html -->\n"
                "<!DOCTYPE html><html><body><h1>MobiRent</h1></body></html>\n"
                "```\n\n"
                "```css\n"
                "/* File: css/styles.css */\n"
                "body { margin: 0; background: #141414; }\n"
                "```\n"
            )
            actions = apply_autonomous_files(tmpdir, markdown)
            self.assertEqual(len(actions), 2)
            self.assertTrue((Path(tmpdir) / "index.html").is_file())
            self.assertTrue((Path(tmpdir) / "css" / "styles.css").is_file())
            html_text = (Path(tmpdir) / "index.html").read_text(encoding="utf-8")
            self.assertFalse(html_text.startswith("<!-- File:"))

    def test_smart_workspace_context_token_reduction(self) -> None:
        """Verifies that targeting a specific file compacts untargeted large files to save >70% tokens."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "js").mkdir()
            (base / "js" / "app.js").write_text("const app = createApp({});\n" * 10, encoding="utf-8")
            (base / "js" / "store.js").write_text("// Store line\nconst s = 1;\n" * 60, encoding="utf-8")
            # Create two large untargeted files (~12,000 chars each = ~3,000 tokens each)
            (base / "js" / "Modals.js").write_text("// Modals line\nconst x = 1;\n" * 500, encoding="utf-8")
            (base / "js" / "AdminView.js").write_text("// Admin line\nconst y = 2;\n" * 500, encoding="utf-8")

            ctx, paths, used_tokens = build_workspace_context(
                folder_path=tmpdir,
                user_prompt="Refactor js/app.js to clean up initialization.",
            )
            self.assertIn("js/app.js", paths)
            self.assertNotIn("js/Modals.js", paths)
            # Without smart compaction, total tokens would be >7,000. With compaction, it should be <800 tokens!
            self.assertLess(used_tokens, 800)
            self.assertIn('summary="true"', ctx)

    def test_conversation_history_code_compaction(self) -> None:
        """Verifies that large assistant code blocks in conversation history are compacted by >85%."""
        giant_code = "\n".join([f"const line_{i} = {i};" for i in range(150)])
        assistant_msg = (
            "Here is the updated file:\n\n"
            f"```javascript\n// File: js/store.js\n{giant_code}\n```\n"
        )
        raw_tokens = estimate_tokens_from_text(assistant_msg)
        compacted = _compact_history_content("assistant", assistant_msg)
        compacted_tokens = estimate_tokens_from_text(compacted)

        self.assertIn("Autonomous Disk Write: js/store.js", compacted)
        self.assertLess(compacted_tokens, raw_tokens * 0.15)

    def test_smart_session_title_ignores_role_and_objective_header(self) -> None:
        """Ensures structured Prompt Enhancer inputs produce a descriptive title instead of 'Role & Objective:'."""
        enhanced_prompt = (
            "### Role & Objective:\n"
            "Explicitly analyze the parts of the Prototipo_MobiRent project that appear to be generated by AI and refactor them.\n\n"
            "### Technical Context & Stack:\n"
            "Vue 3 and Tailwind CSS."
        )
        title = generate_smart_session_title(enhanced_prompt)
        self.assertNotEqual(title.lower(), "role & objective:")
        self.assertNotIn("Role & Objective", title)
        self.assertIn("Prototipo_MobiRent", title)

    def test_js_syntax_verification_runner(self) -> None:
        """Verifies that `run_automated_workspace_tests` checks JS syntax via `node --check`."""
        with tempfile.TemporaryDirectory() as tmpdir:
            js_dir = Path(tmpdir) / "js"
            js_dir.mkdir()
            (js_dir / "app.js").write_text("const a = 1 + 2;\n", encoding="utf-8")
            res = run_automated_workspace_tests(tmpdir)
            if res is not None:
                self.assertEqual(res["runner"], "node --check")
                self.assertTrue(res["passed"])

    def test_session_inherits_project_workspace_path(self) -> None:
        """Verifies that creating or updating a session with a project_id automatically inherits workspace_path."""
        init_db()
        with tempfile.TemporaryDirectory() as tmpdir:
            proj = create_project(name="TestProj", workspace_path=tmpdir)
            sess = None
            try:
                sess = create_session(title="Test Chat", project_id=proj["id"], workspace_path="")
                self.assertEqual(sess["workspace_path"], tmpdir)
                loaded = get_session(sess["id"])
                self.assertIsNotNone(loaded)
                self.assertEqual(loaded["workspace_path"], tmpdir)
            finally:
                if sess:
                    delete_session(sess["id"])
                delete_project(proj["id"])


if __name__ == "__main__":
    unittest.main()
