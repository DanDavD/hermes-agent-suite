"""Unit tests for multimodal clipboard image analysis and attachment routing."""

import base64
import struct
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.image_analyzer import (
    ensure_image_data_url,
    extract_image_metadata,
    is_image_attachment,
    split_attachments,
)
from backend.services.openrouter_client import (
    build_multimodal_attachments_block,
    format_attachments_block,
)


def _make_minimal_png_data_url(width: int = 320, height: int = 180) -> str:
    """Builds a valid minimal PNG header encoded as a base64 data URL."""
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_chunk = struct.pack(">I", 13) + b"IHDR" + ihdr_data + b"\x00\x00\x00\x00"
    raw_bytes = signature + ihdr_chunk + b"\xff\xfe\xfd\x80\x81\x82" * 20
    b64_str = base64.b64encode(raw_bytes).decode("ascii")
    return f"data:image/png;base64,{b64_str}"


class TestImageAnalyzer(unittest.IsolatedAsyncioTestCase):
    def test_detect_image_and_extract_png_dimensions(self) -> None:
        data_url = _make_minimal_png_data_url(640, 480)
        att = {
            "filename": "clipboard-120000-1.png",
            "content": data_url,
            "content_type": "image/png",
        }
        self.assertTrue(is_image_attachment(att))
        meta = extract_image_metadata(ensure_image_data_url(att["content"], att["content_type"]))
        self.assertEqual(meta["format"], "png")
        self.assertEqual(meta["width"], 640)
        self.assertEqual(meta["height"], 480)
        self.assertGreater(meta["size_bytes"], 30)

    def test_format_attachments_block_prevents_binary_utf8_corruption(self) -> None:
        data_url = _make_minimal_png_data_url(800, 600)
        attachments = [
            {
                "filename": "clipboard-screenshot.png",
                "content": data_url,
                "content_type": "image/png",
            },
            {
                "filename": "PlayerController.cs",
                "content": "public class PlayerController {}",
                "content_type": "text/plain",
            },
        ]
        formatted = format_attachments_block(attachments)
        # Must NOT contain UTF-8 replacement characters (\ufffd) from decoding PNG bytes
        self.assertNotIn("\ufffd", formatted)
        self.assertIn("<attached_image filename=\"clipboard-screenshot.png\"", formatted)
        self.assertIn("dimensions=\"800x600px\"", formatted)
        self.assertIn("public class PlayerController {}", formatted)

    def test_split_attachments_separates_text_and_images(self) -> None:
        data_url = _make_minimal_png_data_url(256, 256)
        attachments = [
            {"filename": "screenshot.png", "content": data_url, "content_type": "image/png"},
            {"filename": "notes.md", "content": "# Architecture", "content_type": "text/markdown"},
        ]
        text_items, image_items = split_attachments(attachments)
        self.assertEqual(len(text_items), 1)
        self.assertEqual(text_items[0]["filename"], "notes.md")
        self.assertEqual(len(image_items), 1)
        self.assertEqual(image_items[0]["filename"], "screenshot.png")
        self.assertEqual(image_items[0]["metadata"]["width"], 256)

    @patch("backend.services.openrouter_client.analyze_images_with_vision", new_callable=AsyncMock)
    async def test_build_multimodal_attachments_block_combines_vision_and_text(
        self, mock_vision: AsyncMock
    ) -> None:
        mock_vision.return_value = (
            "<image_context_analysis model=\"google/gemini-2.0-flash-exp:free\">\n"
            "1. Context & Situation: Unity Console showing NullReferenceException.\n"
            "</image_context_analysis>",
            145,
        )
        data_url = _make_minimal_png_data_url(1024, 768)
        attachments = [
            {"filename": "unity-error.png", "content": data_url, "content_type": "image/png"},
            {"filename": "GameManager.cs", "content": "void Start() {}", "content_type": "text/plain"},
        ]
        combined_block, image_urls, vision_tok = await build_multimodal_attachments_block(
            attachments=attachments,
            user_prompt="Fix this Unity error",
        )
        self.assertEqual(vision_tok, 145)
        self.assertEqual(len(image_urls), 1)
        self.assertTrue(image_urls[0].startswith("data:image/png;base64,"))
        self.assertIn("NullReferenceException", combined_block)
        self.assertIn("GameManager.cs", combined_block)


if __name__ == "__main__":
    unittest.main()
