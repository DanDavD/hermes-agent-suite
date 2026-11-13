"""Unit tests for Hermes Studio v2 Autonomous Tool Execution & Smart Titling."""

import os
import tempfile
import unittest

from backend.services.autonomous_executor import (
    apply_autonomous_files,
    extract_files_from_markdown,
    generate_smart_session_title,
    prompt_needs_workspace_injection,
    run_automated_workspace_tests,
)


class TestAutonomousExecutor(unittest.TestCase):
    """Verifies token optimization, file applicator, test runner, and smart titling."""

    def test_smart_session_title_spanish(self):
        t1 = generate_smart_session_title("ayudame a entender python")
        self.assertEqual(t1, "Help with Python Learning")

        t2 = generate_smart_session_title("ayudame con unity y c#")
        self.assertIn("Unity", t2)

        t3 = generate_smart_session_title("500mil tokens quemados en un prompt")
        self.assertEqual(t3, "Token Usage & Cost Optimization")

        t4 = generate_smart_session_title("corre los tests del proyecto")
        self.assertEqual(t4, "Project Unit Tests")

    def test_smart_session_title_english(self):
        t1 = generate_smart_session_title("What would be the best model included with the hermes agent to generate music and sfx for a game?")
        self.assertEqual(t1, "Game Music & SFX Model Selection")

        t2 = generate_smart_session_title("help me understand python please")
        self.assertEqual(t2, "Help with Python Learning")

    def test_prompt_intent_token_conservation(self):
        # Advisory questions should NOT inject 10k-50k tokens of code
        advisory_queries = [
            "What would be the best model included with the hermes agent to generate music and sfx for a game?",
            "ayudame a entender python",
            "which model is cheapest?",
            "explain what a singleton is",
            "diferencia entre struct y class en c#",
        ]
        for q in advisory_queries:
            self.assertFalse(
                prompt_needs_workspace_injection(q),
                f"Advisory query '{q}' should not trigger full workspace code injection",
            )

        # Code implementation / workspace queries SHOULD inject code
        coding_queries = [
            "crea un script en Assets/_Project/Scripts/Gameplay/HealthComponent.cs",
            "modifica MatchController.cs para agregar sonido",
            "corre los tests",
            "arregla el bug en GodBoard",
        ]
        for q in coding_queries:
            self.assertTrue(
                prompt_needs_workspace_injection(q),
                f"Coding query '{q}' should trigger workspace injection",
            )

    def test_extract_files_from_markdown(self):
        markdown_sample = """
Here is the production implementation:

```csharp
// File: Assets/_Project/Scripts/Gameplay/TestController.cs
using UnityEngine;

public class TestController : MonoBehaviour {}
```

And the editor script:

```csharp
// File: Assets/_Project/Editor/TestSetup.cs
using UnityEditor;

public static class TestSetup {}
```
"""
        extracted = extract_files_from_markdown(markdown_sample)
        self.assertEqual(len(extracted), 2)
        self.assertEqual(extracted[0][0], "Assets/_Project/Scripts/Gameplay/TestController.cs")
        self.assertIn("TestController", extracted[0][1])
        self.assertEqual(extracted[1][0], "Assets/_Project/Editor/TestSetup.cs")

    def test_apply_autonomous_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_response = """
```csharp
// File: Assets/Scripts/Sample.cs
public class Sample {}
```
"""
            actions = apply_autonomous_files(tmpdir, sample_response)
            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0]["type"], "file_written")
            self.assertEqual(actions[0]["path"], "Assets/Scripts/Sample.cs")
            self.assertTrue(os.path.isfile(os.path.join(tmpdir, "Assets/Scripts/Sample.cs")))


if __name__ == "__main__":
    unittest.main()
