"""Agent 1: VLM video frame analysis → tactical JSON via DeepSeek multimodal."""
import base64
import json as json_lib
from pathlib import Path

from moviepy import VideoFileClip

from core.interfaces import BaseAgent, AgentInput, AgentOutput
from core.config_loader import load_yaml_and_env
from core.logging import get_logger
from core.exceptions import ModelCallError
from core.llm_client import create_client, call_llm_multimodal

logger = get_logger("video_analyzer")


class VideoAnalyzer(BaseAgent):
    """Extract tactical JSON from video keyframes using DeepSeek VLM."""

    def load_config(self) -> dict:
        return load_yaml_and_env("agents/video_analyzer/config.yaml")

    def run(self, agent_input: AgentInput) -> AgentOutput:
        video_path = agent_input.data.get("video_path")
        frames_data = agent_input.data.get("frames", [])

        if not video_path and not frames_data:
            return AgentOutput(
                status="error", data={}, agent_name="video_analyzer",
                error="No video_path or frames provided",
            )

        # Extract keyframes if not provided
        if not frames_data and video_path:
            frames_data = self._extract_keyframes(video_path)

        # Analyze frames with DeepSeek VLM
        if not frames_data:
            return AgentOutput(
                status="error", data={}, agent_name="video_analyzer",
                error="No frames available for analysis",
            )

        try:
            tactical_json = self._analyze_with_vlm(frames_data)
        except Exception as e:
            logger.error(f"VLM analysis failed: {e}")
            return AgentOutput(
                status="error", data={}, agent_name="video_analyzer",
                error=f"VLM analysis failed: {e}",
            )

        return AgentOutput(
            status="ok",
            data={"tactical_json": tactical_json, "frames": frames_data},
            agent_name="video_analyzer",
        )

    def validate(self, output: AgentOutput) -> bool:
        tj = output.data.get("tactical_json", {})
        return isinstance(tj, dict) and "phase" in tj

    def _extract_keyframes(self, video_path: str) -> list[dict]:
        """Extract keyframes at configured FPS using moviepy (zero subprocess)."""
        fps = self.config.get("fps", 1)
        max_frames = self.config.get("max_frames", 10)
        output_dir = Path("outputs/_keyframes")
        output_dir.mkdir(parents=True, exist_ok=True)

        clip = VideoFileClip(video_path)
        duration = clip.duration
        interval = 1.0 / fps
        frames = []

        for i, t in enumerate([j * interval for j in range(int(duration * fps))]):
            if i >= max_frames:
                break
            frame_path = output_dir / f"frame_{i+1:03d}.jpg"
            clip.save_frame(str(frame_path), t=t)
            frames.append({"path": str(frame_path), "timestamp": t})

        clip.close()
        logger.info(f"Extracted {len(frames)} keyframes from {video_path}")
        return frames

    def _analyze_with_vlm(self, frames: list[dict]) -> dict:
        """Send keyframes to DeepSeek VLM via Anthropic-compatible API."""
        api_key = self.config.get("deepseek_api_key", "")
        if not api_key:
            raise ModelCallError("video_analyzer", "No DEEPSEEK_API_KEY configured")

        base_url = self.config.get("base_url", "https://api.deepseek.com/anthropic")
        model = self.config.get("model", "deepseek-v4-flash")
        timeout = self.config.get("timeout", 60)
        max_tokens = self.config.get("max_tokens", 2048)
        temperature = self.config.get("temperature", 0.3)

        client = create_client(base_url=base_url, api_key=api_key, timeout=timeout)

        prompt = self._load_prompt("frame_analysis.txt")
        images = []
        max_f = self.config.get("max_frames", 10)
        for frame in frames[:max_f]:
            with open(frame["path"], "rb") as img_file:
                images.append({
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(img_file.read()).decode(),
                })

        text = call_llm_multimodal(
            client=client,
            model=model,
            system_prompt="",
            user_text=prompt,
            images=images,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Extract JSON block if wrapped in markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        logger.info(f"VLM response parsed ({len(text)} chars)")
        return json_lib.loads(text.strip())

    def _load_prompt(self, filename: str) -> str:
        path = Path(__file__).parent / "prompts" / filename
        return path.read_text(encoding="utf-8")
