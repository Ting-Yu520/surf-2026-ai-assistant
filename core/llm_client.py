"""Generic LLM client — OpenAI-compatible API. Zero business logic."""
import time
from anthropic import Anthropic
from core.exceptions import ModelCallError


def create_client(base_url: str, api_key: str, timeout: int = 60) -> Anthropic:
    """Create an Anthropic-compatible client. Works with DeepSeek, OpenAI, etc.

    Args:
        base_url: API base URL
        api_key: API key (never hardcoded)
        timeout: Request timeout in seconds

    Returns:
        Configured Anthropic client
    """
    return Anthropic(api_key=api_key, base_url=base_url, timeout=float(timeout))


def _extract_response_text(response, caller_tag: str, elapsed: float) -> str:
    """Extract text from an Anthropic Messages API response.

    Handles both text blocks and content blocks, raising ModelCallError
    if the result is empty.

    Args:
        response: Anthropic API response object
        caller_tag: Agent name tag for error messages
        elapsed: Elapsed time in seconds for error messages

    Returns:
        Extracted text string

    Raises:
        ModelCallError: If the response contains no usable text
    """
    text_parts = []
    for block in response.content:
        if hasattr(block, "text") and block.text:
            text_parts.append(block.text)
        elif hasattr(block, "content") and block.content:
            text_parts.append(str(block.content))

    result = "\n".join(text_parts)
    if not result.strip():
        raise ModelCallError(caller_tag, f"Empty response after {elapsed:.1f}s")

    return result


def call_llm(
    client: Anthropic,
    model: str,
    system_prompt: str,
    user_message: str,
    max_tokens: int = 2048,
    temperature: float = 0.85,
) -> str:
    """Generic LLM call with error handling and timing.

    Args:
        client: Anthropic client from create_client()
        model: Model name string
        system_prompt: System prompt
        user_message: User message
        max_tokens: Max tokens to generate
        temperature: Sampling temperature

    Returns:
        Generated text string

    Raises:
        ModelCallError: On API failure
    """
    t0 = time.time()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as e:
        raise ModelCallError("llm_client", f"API call failed: {e}", original=e)

    elapsed = time.time() - t0
    return _extract_response_text(response, "llm_client", elapsed)


def call_llm_multimodal(
    client: Anthropic,
    model: str,
    system_prompt: str,
    user_text: str,
    images: list[dict],
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """Multimodal LLM call — text + images via Anthropic Messages API.

    Used by VideoAnalyzer to send keyframes to DeepSeek vision models.

    Args:
        client: Anthropic client from create_client()
        model: Model name string (e.g. "deepseek-v4-flash")
        system_prompt: System prompt
        user_text: Text portion of the user message
        images: List of {"data": "<base64_str>", "media_type": "image/jpeg"}
        max_tokens: Max tokens to generate
        temperature: Sampling temperature

    Returns:
        Generated text string

    Raises:
        ModelCallError: On API failure
    """
    t0 = time.time()

    # Validate images before the API call
    for i, img in enumerate(images):
        if "data" not in img:
            raise ModelCallError(
                "llm_client_multimodal",
                f"Image at index {i} is missing required 'data' key",
            )

    # Build content blocks: text first, then images
    content_blocks = [{"type": "text", "text": user_text}]
    for img in images:
        content_blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": img.get("media_type", "image/jpeg"),
                "data": img["data"],
            },
        })

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": content_blocks}],
        )
    except Exception as e:
        raise ModelCallError("llm_client_multimodal", f"API call failed: {e}", original=e)

    elapsed = time.time() - t0
    return _extract_response_text(response, "llm_client_multimodal", elapsed)
