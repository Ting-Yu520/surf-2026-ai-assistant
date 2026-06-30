"""Agent 5: Video composition — overlays, titles, animations, final export.

Delegates to src/video_overlay.py for complex ffmpeg operations.
This Agent provides the clean interface; the legacy module does the heavy lifting.
"""
from pathlib import Path

from core.interfaces import BaseAgent, AgentInput, AgentOutput
from core.config_loader import load_yaml_and_env
from core.logging import get_logger

logger = get_logger("video_composer")


class VideoComposer(BaseAgent):
    """Compose final video with overlays, captions, and MG animations."""

    def load_config(self) -> dict:
        return load_yaml_and_env("agents/video_composer/config.yaml")

    def run(self, agent_input: AgentInput) -> AgentOutput:
        video_path = agent_input.data.get("video_path")
        audio_path = agent_input.data.get("audio_path")
        timeline = agent_input.data.get("timeline", [])
        segments = agent_input.data.get("segments", [])
        match_info = agent_input.data.get("match_info", "⚽ AI Tactical Commentary")
        mg_clips = agent_input.data.get("mg_clips", {})
        predictions = agent_input.data.get("predictions", [])
        output_path = agent_input.data.get(
            "output_path", "outputs/corner_story.mp4"
        )

        if not video_path or not audio_path:
            return AgentOutput(
                status="skipped", data={}, agent_name="video_composer",
                error="Missing video_path or audio_path — skipping composition",
            )

        try:
            # Delegate to legacy ffmpeg pipeline (complex drawtext/drawbox logic)
            from src.video_overlay import create_titled_video

            total_dur = timeline[-1]["end"] if timeline else None
            create_titled_video(
                video_path=video_path,
                audio_path=audio_path,
                timeline=timeline,
                output_path=output_path,
                match_info=match_info,
                total_dur=total_dur,
                tacticai_predictions=predictions if predictions else None,
                mg_clips=mg_clips,
            )
        except Exception as e:
            logger.error(f"Video composition failed: {e}")
            return AgentOutput(
                status="error", data={}, agent_name="video_composer",
                error=str(e),
            )

        return AgentOutput(
            status="ok",
            data={"output_video": output_path},
            agent_name="video_composer",
        )

    def validate(self, output: AgentOutput) -> bool:
        path = output.data.get("output_video", "")
        return bool(path) and Path(path).exists()
