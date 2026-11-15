"""Unit tests for Hermes Studio v2 Prompt Enhancer & Architect Router."""

import unittest
from fastapi.testclient import TestClient

from backend.main import app


class TestPromptEnhancerRouter(unittest.TestCase):
    """Verifies schema validation and endpoint availability for the $0 Prompt Architect."""

    def setUp(self):
        self.client = TestClient(app)

    def test_prompt_enhancer_empty_payload_rejected(self):
        res = self.client.post("/api/prompt-enhancer/chat", json={"prompt": ""})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Prompt draft cannot be empty", res.json()["detail"])

    def test_prompt_enhancer_whitespace_rejected(self):
        res = self.client.post("/api/prompt-enhancer/chat", json={"prompt": "   \n\t  "})
        self.assertEqual(res.status_code, 400)

    def test_strip_emojis_utility(self):
        from backend.routers.prompt_enhancer import strip_emojis, EMOJI_PATTERN
        sample = "🎯 **Role & Objective**: 🛠️ Step 1 ⚠️ Warning 📤 Output"
        cleaned = strip_emojis(sample)
        self.assertEqual(len(EMOJI_PATTERN.findall(cleaned)), 0)
        self.assertIn("Role & Objective", cleaned)

