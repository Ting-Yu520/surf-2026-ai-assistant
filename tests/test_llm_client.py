"""Tests for core.llm_client — multimodal content block construction."""
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.llm_client import call_llm_multimodal
from core.exceptions import ModelCallError


class TestCallLlmMultimodal:
    """Test call_llm_multimodal content block construction and error handling."""

    def test_single_image_content_block_structure(self):
        """Content blocks contain text block + image block with correct structure."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="{}", content=None)]
        mock_client.messages.create.return_value = mock_response

        call_llm_multimodal(
            client=mock_client,
            model="deepseek-v4-flash",
            system_prompt="You are a VLM.",
            user_text="Analyze this frame.",
            images=[{"data": "aW1hZ2VieXRlcw==", "media_type": "image/jpeg"}],
            max_tokens=512,
            temperature=0.3,
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "deepseek-v4-flash"
        assert call_kwargs["max_tokens"] == 512
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["system"] == "You are a VLM."

        content = call_kwargs["messages"][0]["content"]
        assert len(content) == 2  # text + 1 image
        assert content[0] == {"type": "text", "text": "Analyze this frame."}
        assert content[1]["type"] == "image"
        assert content[1]["source"]["type"] == "base64"
        assert content[1]["source"]["media_type"] == "image/jpeg"
        assert content[1]["source"]["data"] == "aW1hZ2VieXRlcw=="

    def test_multiple_images(self):
        """Multiple images produce multiple image content blocks."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="{}", content=None)]
        mock_client.messages.create.return_value = mock_response

        call_llm_multimodal(
            client=mock_client,
            model="deepseek-v4-flash",
            system_prompt="",
            user_text="Compare these frames.",
            images=[
                {"data": "aW1nMQ==", "media_type": "image/jpeg"},
                {"data": "aW1nMg==", "media_type": "image/png"},
                {"data": "aW1nMw==", "media_type": "image/jpeg"},
            ],
        )

        content = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert len(content) == 4  # text + 3 images
        assert content[1]["source"]["media_type"] == "image/jpeg"
        assert content[1]["source"]["data"] == "aW1nMQ=="
        assert content[2]["source"]["media_type"] == "image/png"
        assert content[3]["source"]["data"] == "aW1nMw=="

    def test_empty_images_list(self):
        """Empty images list produces text-only content."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="response", content=None)]
        mock_client.messages.create.return_value = mock_response

        result = call_llm_multimodal(
            client=mock_client,
            model="deepseek-v4-flash",
            system_prompt="",
            user_text="Hello",
            images=[],
        )

        content = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert len(content) == 1
        assert content[0] == {"type": "text", "text": "Hello"}
        assert result == "response"

    def test_default_media_type_is_jpeg(self):
        """Image dict without media_type defaults to image/jpeg."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="ok", content=None)]
        mock_client.messages.create.return_value = mock_response

        call_llm_multimodal(
            client=mock_client,
            model="deepseek-v4-flash",
            system_prompt="",
            user_text="x",
            images=[{"data": "Zm9v"}],  # no media_type key
        )

        content = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert content[1]["source"]["media_type"] == "image/jpeg"

    def test_api_failure_raises_model_call_error(self):
        """API exception is wrapped in ModelCallError."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("Connection timeout")

        with pytest.raises(ModelCallError, match="API call failed"):
            call_llm_multimodal(
                client=mock_client,
                model="deepseek-v4-flash",
                system_prompt="",
                user_text="test",
                images=[{"data": "Zm9v"}],
            )

    def test_empty_response_raises_model_call_error(self):
        """Empty/missing text in response raises ModelCallError."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="", content="")]
        mock_client.messages.create.return_value = mock_response

        with pytest.raises(ModelCallError, match="Empty response"):
            call_llm_multimodal(
                client=mock_client,
                model="deepseek-v4-flash",
                system_prompt="",
                user_text="test",
                images=[],
            )

    def test_content_block_with_content_attr(self):
        """Blocks with .content attr (not .text) are also extracted."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        block = MagicMock()
        block.text = ""
        block.content = "payload from .content attr"
        mock_response.content = [block]
        mock_client.messages.create.return_value = mock_response

        result = call_llm_multimodal(
            client=mock_client,
            model="deepseek-v4-flash",
            system_prompt="",
            user_text="test",
            images=[],
        )

        assert "payload from .content attr" in result
