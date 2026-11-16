"""Multimodal image analysis and clipboard vision extraction service.

Extracts visual context, UI state, error messages, code snippets, and situation
details from pasted clipboard images or uploaded image attachments, combining
them with the user's prompt for both chat execution and prompt enhancement.
"""

import base64
import logging
import struct
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes.image_analyzer")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

VISION_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "google/gemini-2.5-flash",
    "openai/gpt-4o-mini",
    "anthropic/claude-3.5-sonnet",
]

VISION_ANALYSIS_SYSTEM_PROMPT = """You are the Multimodal Vision & Context Analyzer for Hermes Studio.
Analyze the attached image(s) in relation to the user's prompt and extract all high-signal engineering and situational context.
Maintain strict token efficiency, zero emojis, and high technical precision.

Structure your analysis using these exact sections:
1. Context & Situation: Identify the application, UI state, environment, or scene shown, and what is happening.
2. Extracted Text, Messages & Errors: Transcribe verbatim any visible error messages, logs, stack traces, chat messages, code snippets, or key UI labels.
3. Key Visual Details & Diagnosis: Highlight visual anomalies, layout issues, or technical clues directly relevant to solving the user's prompt."""


def normalize_attachment_dict(item: Any) -> Dict[str, Any]:
    """Normalizes a Pydantic model or dictionary attachment into a standard dict."""
    if isinstance(item, dict):
        fname = str(item.get("filename") or item.get("name") or "attachment")
        raw_content = str(item.get("content") or item.get("text") or "")
        ctype = str(item.get("content_type") or "")
        size = int(item.get("size") or item.get("sizeBytes") or len(raw_content))
    else:
        fname = str(getattr(item, "filename", None) or getattr(item, "name", None) or "attachment")
        raw_content = str(getattr(item, "content", None) or getattr(item, "text", None) or "")
        ctype = str(getattr(item, "content_type", None) or "")
        size = int(getattr(item, "size", None) or len(raw_content))

    return {
        "filename": fname,
        "content": raw_content,
        "content_type": ctype,
        "size": size,
    }


def is_image_attachment(item: Any) -> bool:
    """Determines whether an attachment is an image (via MIME type, data URL prefix, or extension)."""
    norm = normalize_attachment_dict(item)
    ctype = norm["content_type"].lower().strip()
    content = norm["content"].strip()
    fname = norm["filename"].lower().strip()

    if ctype.startswith("image/"):
        return True
    if content.startswith("data:image/"):
        return True
    if any(fname.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return True
    return False


def ensure_image_data_url(raw_content: str, content_type: str = "image/png") -> str:
    """Ensures an image payload is formatted as a valid base64 data URL."""
    cleaned = (raw_content or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith("data:image/"):
        return cleaned
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return cleaned

    mime = content_type.strip().lower() if content_type else "image/png"
    if not mime.startswith("image/"):
        mime = "image/png"

    # Strip any generic data: prefix if present
    if cleaned.startswith("data:") and ";base64," in cleaned:
        b64_part = cleaned.split(";base64,", 1)[1]
        return f"data:{mime};base64,{b64_part}"

    return f"data:{mime};base64,{cleaned}"


def extract_image_metadata(data_url: str) -> Dict[str, Any]:
    """
    Extracts format, byte size, and pixel dimensions (width x height) from a base64
    image data URL using lightweight binary header inspection.
    """
    meta: Dict[str, Any] = {
        "format": "unknown",
        "width": None,
        "height": None,
        "size_bytes": 0,
    }
    if not data_url:
        return meta

    b64_data = data_url
    if ";base64," in data_url:
        header, b64_data = data_url.split(";base64,", 1)
        if "image/" in header:
            meta["format"] = header.split("image/", 1)[1].split(";")[0].lower()

    try:
        raw_bytes = base64.b64decode(b64_data, validate=False)
    except Exception:
        return meta

    meta["size_bytes"] = len(raw_bytes)
    if len(raw_bytes) < 24:
        return meta

    # PNG: starts with \x89PNG\r\n\x1a\n and IHDR chunk at bytes 16..24
    if raw_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        meta["format"] = "png"
        try:
            w, h = struct.unpack(">II", raw_bytes[16:24])
            meta["width"] = int(w)
            meta["height"] = int(h)
        except Exception:
            pass
        return meta

    # GIF: GIF87a or GIF89a
    if raw_bytes[:6] in (b"GIF87a", b"GIF89a"):
        meta["format"] = "gif"
        try:
            w, h = struct.unpack("<HH", raw_bytes[6:10])
            meta["width"] = int(w)
            meta["height"] = int(h)
        except Exception:
            pass
        return meta

    # JPEG: starts with \xff\xd8
    if raw_bytes[:2] == b"\xff\xd8":
        meta["format"] = "jpeg"
        try:
            idx = 2
            length = len(raw_bytes)
            while idx < length - 9:
                if raw_bytes[idx] != 0xFF:
                    idx += 1
                    continue
                marker = raw_bytes[idx + 1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", raw_bytes[idx + 5 : idx + 9])
                    meta["width"] = int(w)
                    meta["height"] = int(h)
                    break
                seg_len = struct.unpack(">H", raw_bytes[idx + 2 : idx + 4])[0]
                if seg_len < 2:
                    break
                idx += 2 + seg_len
        except Exception:
            pass
        return meta

    # WebP: RIFF....WEBP
    if raw_bytes[:4] == b"RIFF" and raw_bytes[8:12] == b"WEBP":
        meta["format"] = "webp"
        try:
            chunk = raw_bytes[12:16]
            if chunk == b"VP8X" and len(raw_bytes) >= 30:
                w = 1 + int.from_bytes(raw_bytes[24:27], "little")
                h = 1 + int.from_bytes(raw_bytes[27:30], "little")
                meta["width"] = w
                meta["height"] = h
        except Exception:
            pass
        return meta

    return meta


def split_attachments(
    attachments: Optional[List[Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Separates incoming attachments into (text_attachments, image_attachments).
    Guarantees binary images are never decoded as UTF-8 text blocks.
    """
    text_items: List[Dict[str, Any]] = []
    image_items: List[Dict[str, Any]] = []

    if not attachments:
        return text_items, image_items

    for raw_item in attachments:
        norm = normalize_attachment_dict(raw_item)
        if not norm["content"]:
            continue
        if is_image_attachment(norm):
            data_url = ensure_image_data_url(norm["content"], norm["content_type"])
            meta = extract_image_metadata(data_url)
            norm["data_url"] = data_url
            norm["metadata"] = meta
            if not norm["content_type"] or not norm["content_type"].startswith("image/"):
                fmt = meta.get("format") if meta.get("format") != "unknown" else "png"
                norm["content_type"] = f"image/{fmt}"
            image_items.append(norm)
        else:
            text_items.append(norm)

    return text_items, image_items


async def analyze_images_with_vision(
    image_attachments: List[Dict[str, Any]],
    user_prompt: str = "",
    api_key: Optional[str] = None,
) -> Tuple[str, int]:
    """
    Analyzes one or more pasted/attached images using a multimodal vision model
    on OpenRouter, extracting context, situation, visible text/messages, and errors.
    """
    if not image_attachments:
        return "", 0

    # Lazy import to avoid circular dependency with openrouter_client
    from backend.services.openrouter_client import get_async_client

    try:
        client = get_async_client(api_key)
    except Exception as exc:
        logger.warning("Cannot initialize OpenRouter client for vision analysis: %s", exc)
        return _build_metadata_fallback_summary(image_attachments), 0

    prompt_context = (user_prompt or "").strip() or "Analyze the attached image and extract all context, messages, and technical details."
    content_parts: List[Dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"User Prompt / Question:\n\"\"\"\n{prompt_context}\n\"\"\"\n\n"
                "Extract the visual context, situation, and any visible messages, errors, code, or UI elements from the attached image(s)."
            ),
        }
    ]

    meta_headers: List[str] = []
    for idx, img in enumerate(image_attachments, start=1):
        data_url = img.get("data_url") or ensure_image_data_url(img["content"], img["content_type"])
        meta = img.get("metadata") or extract_image_metadata(data_url)
        dims = f"{meta['width']}x{meta['height']}px" if meta.get("width") and meta.get("height") else "dimensions unknown"
        size_kb = round(meta.get("size_bytes", 0) / 1024, 1)
        meta_headers.append(
            f"Image #{idx}: {img['filename']} ({img['content_type']}, {dims}, {size_kb} KB)"
        )
        content_parts.append(
            {
                "type": "image_url",
                "image_url": {"url": data_url},
            }
        )

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": VISION_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": content_parts},
    ]

    for model_slug in VISION_MODELS:
        try:
            response = await client.chat.completions.create(
                model=model_slug,
                messages=messages,
                temperature=0.2,
                max_tokens=900,
            )
            analysis_text = (response.choices[0].message.content or "").strip() if response.choices else ""
            if analysis_text:
                tokens_used = 0
                if getattr(response, "usage", None) and getattr(response.usage, "total_tokens", None):
                    tokens_used = int(response.usage.total_tokens)
                header_str = " | ".join(meta_headers)
                formatted_block = (
                    f"<image_context_analysis model=\"{model_slug}\" images=\"{header_str}\">\n"
                    f"{analysis_text}\n"
                    f"</image_context_analysis>"
                )
                return formatted_block, tokens_used
        except Exception as err:
            logger.warning("Vision model %s failed during image analysis: %s", model_slug, err)
            continue

    return _build_metadata_fallback_summary(image_attachments), 0


def _build_metadata_fallback_summary(image_attachments: List[Dict[str, Any]]) -> str:
    """Fallback metadata block when external vision API calls are unavailable."""
    lines: List[str] = []
    for idx, img in enumerate(image_attachments, start=1):
        meta = img.get("metadata") or extract_image_metadata(img.get("data_url", ""))
        dims = f"{meta['width']}x{meta['height']}px" if meta.get("width") and meta.get("height") else "unknown dimensions"
        size_kb = round(meta.get("size_bytes", 0) / 1024, 1)
        lines.append(
            f"- Image #{idx}: {img['filename']} (format={meta.get('format', 'image')}, {dims}, {size_kb} KB)"
        )
    joined = "\n".join(lines)
    return (
        "<image_context_analysis status=\"metadata_only\">\n"
        f"Attached Image Metadata:\n{joined}\n"
        "</image_context_analysis>"
    )
