"""Agent 6: Decision-level fusion — orchestrates all Agents and merges outputs.

Progressive migration: uses new Agent classes where available,
falls back to legacy src/ modules for agents not yet extracted.
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

        # ── Agent ①: VideoAnalyzer (VLM keyframe analysis) ──
        try:
            from agents.video_analyzer.agent import VideoAnalyzer
            analyzer = VideoAnalyzer()
            analyzer_result = analyzer.run(AgentInput(data={"video_path": video_path}))
            traces.append({"agent": "video_analyzer", "status": analyzer_result.status})
            tactical_json = analyzer_result.data.get("tactical_json", {})
        except Exception as e:
            logger.warning(f"VideoAnalyzer failed: {e}")
            tactical_json = {}
            traces.append({"agent": "video_analyzer", "status": "error", "error": str(e)})

        # ── Agent ②: TacticalExtractor (Phase 1 data) ──
        # Bridge: use legacy src/phase_bridge.py until TacticalExtractor is extracted
        try:
            from src.phase_bridge import get_real_or_sample, build_field_mapping, format_for_prompt

            predictions_data = get_real_or_sample(corner_entry) if corner_entry else None
            if predictions_data and predictions_data.get("predictions"):
                predictions = predictions_data["predictions"]
                mapping = build_field_mapping(predictions)
            else:
                predictions = []
                mapping = None

            # Build formatted input for CommentaryGen
            if predictions_data:
                from src.phase_bridge import tacticai_to_phase2
                phase2_input = tacticai_to_phase2(predictions_data)
                formatted = format_for_prompt(phase2_input, corner_entry)
            else:
                formatted = {"fact_section": "", "tactic_section": ""}
            traces.append({"agent": "tactical_extractor", "status": "ok"})
        except Exception as e:
            logger.warning(f"TacticalExtractor failed: {e}")
            predictions = []
            mapping = None
            formatted = {"fact_section": "", "tactic_section": ""}
            traces.append({"agent": "tactical_extractor", "status": "error", "error": str(e)})

        # ── Agent ③: CommentaryGen (LLM duo commentary) ──
        # Bridge: use legacy src/pipeline.py's LLM call until CommentaryGen is extracted
        try:
            from src.config import DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_API_KEY, API_TIMEOUT, MAX_TOKENS
            from core.llm_client import create_client, call_llm
            from src.prompts.corner_kick import DUO_SYSTEM_PROMPT, DUO_USER_TEMPLATE

            fact = formatted.get("fact_section", "")
            tactic = formatted.get("tactic_section", "")

            # Augment tactic section with real prediction data if available
            if predictions:
                top_preds = sorted(predictions, key=lambda p: p.get("probability", 0), reverse=True)[:3]
                extra = "\nTacticAI 真实预测数据:\n"
                for p in top_preds:
                    role = p.get("role", "球员")
                    prob = p.get("probability", 0)
                    pos = p["position"]
                    extra += f"- {role}#{p['player_index']}: 接球概率 {prob*100:.1f}%, 位置({pos[0]:.0f},{pos[1]:.0f})\n"
                tactic = tactic + extra

            client = create_client(DEEPSEEK_BASE_URL, DEEPSEEK_API_KEY, API_TIMEOUT)
            script = call_llm(
                client=client,
                model=DEEPSEEK_MODEL,
                system_prompt=DUO_SYSTEM_PROMPT,
                user_message=DUO_USER_TEMPLATE.format(fact_section=fact, tactic_section=tactic),
                max_tokens=MAX_TOKENS,
                temperature=0.85,
            )
            traces.append({"agent": "commentary_gen", "status": "ok", "script_len": len(script)})
        except Exception as e:
            logger.error(f"CommentaryGen failed: {e}")
            script = ""
            traces.append({"agent": "commentary_gen", "status": "error", "error": str(e)})

        # ── Parse script into segments ──
        from src.video_overlay import parse_script
        segments = parse_script(script)
        if not segments:
            segments = [{"speaker": "A", "text": script or "角球战术分析", "visual": "clear", "visual_type": "clear"}]

        # ── Agent ④: VoiceGen (TTS) ──
        prefix = output_prefix + "_" if output_prefix else ""
        audio_dir = f"outputs/{prefix}audio_segs"
        audio_path_out = f"outputs/{prefix}narration.mp3"

        try:
            from src.tts_client import generate_timeline_audio, concat_audio_segments
            tts_segments = generate_timeline_audio(
                [{"narration": seg["text"]} for seg in segments],
                audio_dir,
            )
            concat_audio_segments(tts_segments, audio_path_out)
            traces.append({"agent": "voice_gen", "status": "ok", "segments": len(tts_segments)})
        except Exception as e:
            logger.error(f"VoiceGen failed: {e}")
            tts_segments = []
            traces.append({"agent": "voice_gen", "status": "error", "error": str(e)})

        # ── Build timeline ──
        from src.video_overlay import build_timeline
        durations = [s.get("actual_duration_sec", 2.0) for s in tts_segments]
        if len(durations) != len(segments):
            durations = [2.0] * len(segments)
        timeline = build_timeline(segments, durations)

        # ── Auto-upgrade A segments to ai_scene ──
        for seg in segments:
            if seg["speaker"] == "A" and seg.get("visual_type") not in ("ai_scene", "clear"):
                seg["visual"] = "ai_scene"
                seg["visual_type"] = "ai_scene"

        # ── Render MG clips ──
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

        # ── Agent ⑤: VideoComposer ──
        output_video = f"outputs/{prefix}corner_story.mp4"
        if video_path:
            try:
                from src.video_overlay import create_titled_video
                match_info = ""
                if corner_entry:
                    match_info = (
                        f"{corner_entry.get('match', '')} — "
                        f"{corner_entry.get('goal_scorer', '')} "
                        f"({corner_entry.get('minute', '')}')"
                    )
                total_dur = timeline[-1]["end"] if timeline else None
                create_titled_video(
                    video_path=video_path,
                    audio_path=audio_path_out,
                    timeline=timeline,
                    output_path=output_video,
                    match_info=match_info or "⚽ AI 角球战术解说",
                    total_dur=total_dur,
                    tacticai_predictions=predictions if predictions else None,
                    mg_clips=mg_clips,
                )
                traces.append({"agent": "video_composer", "status": "ok"})
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
