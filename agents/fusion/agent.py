"""Agent 6: Decision-level fusion — orchestrates all 5 Agents and merges outputs.

Now uses native Agent classes directly (no more src/ bridges for Agents ①-⑤).
Only utility functions (parse_script, build_timeline) still come from src/video_overlay.py.
"""
import time
from pathlib import Path

from core.interfaces import BaseAgent, AgentInput, AgentOutput
from core.config_loader import load_yaml_and_env
from core.logging import get_logger

logger = get_logger("fusion")


class FusionAgent(BaseAgent):
    """Orchestrate all 5 Agents and produce the final video.

    Pipeline:
    ① VideoAnalyzer → ② TacticalExtractor → ③ CommentaryGen
                                                ↙           ↘
                              ④ VoiceGen (parallel)  ⑤ VideoComposer (parallel)
                                                ↘           ↙
                                        ⑥ Fusion → final video
    """

    def load_config(self) -> dict:
        return load_yaml_and_env("agents/fusion/config.yaml")

    def run(self, agent_input: AgentInput) -> AgentOutput:
        t0 = time.time()
        traces = []

        video_path = agent_input.data.get("video_path")
        corner_entry = agent_input.data.get("corner_entry", {})
        output_prefix = agent_input.data.get("output_prefix", "")

        # ═══════════════════════════════════════════
        # Agent ①: VideoAnalyzer (VLM keyframe analysis)
        # ═══════════════════════════════════════════
        tactical_json = {}
        try:
            from agents.video_analyzer.agent import VideoAnalyzer
            analyzer = VideoAnalyzer()
            ar = analyzer.run(AgentInput(data={"video_path": video_path}))
            traces.append({"agent": "video_analyzer", "status": ar.status})
            tactical_json = ar.data.get("tactical_json", {})
        except Exception as e:
            logger.warning(f"VideoAnalyzer failed: {e}")
            traces.append({"agent": "video_analyzer", "status": "error", "error": str(e)})

        # ═══════════════════════════════════════════
        # Agent ②: TacticalExtractor (Phase 1 data)
        # ═══════════════════════════════════════════
        formatted = {"fact_section": "", "tactic_section": ""}
        predictions = []
        mapping = None
        try:
            from agents.tactical_extractor.agent import TacticalExtractor
            extractor = TacticalExtractor()
            er = extractor.run(AgentInput(data={
                "corner_entry": corner_entry,
                "tacticai_json": tactical_json if tactical_json.get("players") else None,
            }))
            traces.append({"agent": "tactical_extractor", "status": er.status})
            if er.status == "ok":
                formatted = er.data.get("formatted", formatted)
                predictions = er.data.get("predictions", [])
                mapping = er.data.get("mapping")
        except Exception as e:
            logger.warning(f"TacticalExtractor failed: {e}")
            traces.append({"agent": "tactical_extractor", "status": "error", "error": str(e)})

        # Augment tactic section with real prediction data
        if predictions:
            top_preds = sorted(predictions, key=lambda p: p.get("probability", 0), reverse=True)[:3]
            extra = "\nTacticAI 真实预测数据:\n"
            for p in top_preds:
                role = p.get("role", "球员")
                prob = p.get("probability", 0)
                pos = p["position"]
                extra += f"- {role}#{p['player_index']}: 接球概率 {prob*100:.1f}%, 位置({pos[0]:.0f},{pos[1]:.0f})\n"
            formatted["tactic_section"] = formatted.get("tactic_section", "") + extra

        # ═══════════════════════════════════════════
        # Agent ③: CommentaryGen (LLM duo commentary)
        # ═══════════════════════════════════════════
        script = ""
        try:
            from agents.commentary_gen.agent import CommentaryGenerator
            cg = CommentaryGenerator()
            cr = cg.run(AgentInput(data={
                "fact_section": formatted.get("fact_section", ""),
                "tactic_section": formatted.get("tactic_section", ""),
            }))
            traces.append({"agent": "commentary_gen", "status": cr.status, "script_len": len(cr.data.get("script", ""))})
            script = cr.data.get("script", "")
        except Exception as e:
            logger.error(f"CommentaryGen failed: {e}")
            traces.append({"agent": "commentary_gen", "status": "error", "error": str(e)})

        # Parse script into segments (utility, not an Agent)
        from src.video_overlay import parse_script
        segments = parse_script(script)
        if not segments:
            segments = [{"speaker": "A", "text": script or "角球战术分析", "visual": "clear", "visual_type": "clear"}]

        # ═══════════════════════════════════════════
        # Agent ④: VoiceGen (TTS)
        # ═══════════════════════════════════════════
        prefix = output_prefix + "_" if output_prefix else ""
        audio_dir = f"outputs/{prefix}audio_segs"
        audio_path_out = f"outputs/{prefix}narration.mp3"
        tts_segments = []

        try:
            from agents.voice_gen.agent import VoiceGenerator
            vg = VoiceGenerator()
            vr = vg.run(AgentInput(data={
                "segments": [{"narration": seg["text"]} for seg in segments],
                "output_dir": audio_dir,
                "audio_path": audio_path_out,
            }))
            traces.append({"agent": "voice_gen", "status": vr.status, "segments": len(vr.data.get("segments", []))})
            tts_segments = vr.data.get("segments", [])
        except Exception as e:
            logger.error(f"VoiceGen failed: {e}")
            traces.append({"agent": "voice_gen", "status": "error", "error": str(e)})

        # Build timeline (utility, not an Agent)
        from src.video_overlay import build_timeline
        durations = [s.get("actual_duration_sec", 2.0) for s in tts_segments]
        if len(durations) != len(segments):
            durations = [2.0] * len(segments)
        timeline = build_timeline(segments, durations)

        # Auto-upgrade A segments to ai_scene
        for seg in segments:
            if seg["speaker"] == "A" and seg.get("visual_type") not in ("ai_scene", "clear"):
                seg["visual"] = "ai_scene"
                seg["visual_type"] = "ai_scene"

        # Render MG clips for ai_scene segments
        mg_clips = {}
        if predictions and mapping and tts_segments:
            from src.mg_renderer import render_all_mg_clips
            ai_scenes = [
                {**seg, "actual_duration_sec": d}
                for seg, d in zip(segments, durations)
                if seg.get("visual_type") == "ai_scene"
            ]
            if ai_scenes:
                try:
                    mg_clips = render_all_mg_clips(ai_scenes, predictions, mapping, corner_entry, prefix)
                except Exception as e:
                    logger.warning(f"MG rendering failed: {e}")

        # ═══════════════════════════════════════════
        # Agent ⑤: VideoComposer (ffmpeg synthesis)
        # ═══════════════════════════════════════════
        output_video = f"outputs/{prefix}corner_story.mp4"
        if video_path:
            try:
                from agents.video_composer.agent import VideoComposer
                match_info = ""
                if corner_entry:
                    match_info = (
                        f"{corner_entry.get('match', '')} — "
                        f"{corner_entry.get('goal_scorer', '')} "
                        f"({corner_entry.get('minute', '')}')"
                    )
                vc = VideoComposer()
                vcr = vc.run(AgentInput(data={
                    "video_path": video_path,
                    "audio_path": audio_path_out,
                    "timeline": timeline,
                    "segments": segments,
                    "match_info": match_info or "⚽ AI 角球战术解说",
                    "mg_clips": mg_clips,
                    "predictions": predictions,
                    "output_path": output_video,
                }))
                traces.append({"agent": "video_composer", "status": vcr.status})
            except Exception as e:
                logger.error(f"VideoComposer failed: {e}")
                traces.append({"agent": "video_composer", "status": "error", "error": str(e)})
        else:
            logger.info("No video source — skipping VideoComposer")

        elapsed = time.time() - t0
        logger.info(f"Pipeline complete in {elapsed:.1f}s, {len(traces)} agent traces")

        return AgentOutput(
            status="ok",
            data={
                "output_video": output_video if video_path else "",
                "script": script,
                "audio_path": audio_path_out,
                "segments": segments,
                "elapsed_sec": elapsed,
                "agent_traces": traces,
            },
            agent_name="fusion",
        )

    def validate(self, output: AgentOutput) -> bool:
        traces = output.data.get("agent_traces", [])
        return len(traces) > 0
