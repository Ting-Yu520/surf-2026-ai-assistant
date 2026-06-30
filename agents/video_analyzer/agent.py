"""Agent 1: VLM video frame analysis → tactical JSON."""
import base64
import json as json_lib
from pathlib import Path

from moviepy import VideoFileClip

from core.interfaces import BaseAgent, AgentInput, AgentOutput
from core.config_loader import load_yaml_and_env
from core.logging import get_logger
from core.exceptions import ModelCallError

logger = get_logger("video_analyzer")

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    logger.warning("google-generativeai not installed. VideoAnalyzer will use stub mode.")


class VideoAnalyzer(BaseAgent):
    """Extract tactical JSON from video keyframes using VLM (Gemini Vision)."""

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

        # Analyze frames with VLM
        if HAS_GEMINI and frames_data:
            try:
                tactical_json = self._analyze_with_vlm(frames_data)
            except Exception as e:
                logger.warning(f"VLM analysis failed, using stub: {e}")
                tactical_json = self._stub_analysis(frames_data)
        else:
            tactical_json = self._stub_analysis(frames_data)

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
        """Call Gemini Vision to analyze keyframes."""
        api_key = self.config.get("gemini_api_key", "")
        if not api_key:
            raise ModelCallError("video_analyzer", "No GEMINI_API_KEY configured")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self.config.get("model", "gemini-2.5-flash"))

        prompt = self._load_prompt("frame_analysis.txt")
        image_parts = []
        max_f = self.config.get("max_frames", 10)
        for frame in frames[:max_f]:
            with open(frame["path"], "rb") as img_file:
                image_parts.append({
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(img_file.read()).decode(),
                })

        content = [prompt] + image_parts
        timeout_ms = self.config.get("timeout", 30) * 1000
        response = model.generate_content(
            content,
            request_options={"timeout": timeout_ms},
        )

        text = response.text
        # Extract JSON block if wrapped in markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        logger.info(f"VLM response parsed ({len(text)} chars)")
        return json_lib.loads(text.strip())

    def _stub_analysis(self, frames: list[dict]) -> dict:
        """Stub mode: return empty tactical JSON when VLM not available.
        Callers should detect and fall back to TacticalExtractor's sample data.
        """
        return {
            "players": [],
            "ball_position": None,
            "corner_type": "",
            "formation": "4-4-2",
            "phase": "corner_kick",
            "tactical_notes": "[stub] VLM not available — using simulated data",
        }

    def _load_prompt(self, filename: str) -> str:
        path = Path(__file__).parent / "prompts" / filename
        return path.read_text(encoding="utf-8")
