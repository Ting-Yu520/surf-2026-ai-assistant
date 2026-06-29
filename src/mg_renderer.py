"""MG 动画渲染器 — HyperFrames 接口

将 TacticAI 真实坐标数据 + 解说文本 → 变量 JSON → HyperFrames 渲染 → MP4 clip
"""

import json
import subprocess
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "experiments" / "ai-scene-mg" / "templates"
TEMPLATE_HTML = TEMPLATE_DIR / "tactical-scene.html"
RENDER_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "mg_clips"
RENDER_TIMEOUT = 120  # 每段 MG 渲染最长等待秒数


def build_scene_variables(
    predictions: list[dict],
    mapping: dict,
    segment_duration: float,
    corner_entry: Optional[dict] = None,
) -> dict:
    """从真实数据构建 HyperFrames 变量 JSON。

    Args:
        predictions: TacticAI 预测列表
        mapping: build_field_mapping() 的输出
        segment_duration: TTS 音频时长（秒），决定动画长度
        corner_entry: 角球原始数据（用于标题等）

    Returns:
        HyperFrames 变量 JSON dict
    """
    if not predictions:
        return {
            "players": [],
            "ball": {"x": 0, "y": 0},
            "highlight": {"x": 0, "y": 0, "label": ""},
            "arrow": {"from_x": 0, "from_y": 0, "to_x": 0, "to_y": 0, "label": ""},
            "cards": [],
            "title": "⚽ 角球战术分析",
            "duration": max(3.0, segment_duration),
        }

    to_px = mapping["to_px"]
    to_py = mapping["to_py"]

    attackers = sorted(
        [p for p in predictions if p.get("is_attacker")],
        key=lambda p: p.get("probability", 0), reverse=True
    )
    defenders = sorted(
        [p for p in predictions if not p.get("is_attacker")],
        key=lambda p: p.get("probability", 0), reverse=True
    )
    top_attacker = attackers[0] if attackers else predictions[0]
    ball_pos = predictions[0]["position"]  # 角球起点 ≈ 角旗区

    # 计算箭头：从球到最高概率接球球员
    arrow_from = to_px(ball_pos[0]), to_py(ball_pos[1])
    arrow_to = to_px(top_attacker["position"][0]), to_py(top_attacker["position"][1])

    # 防守封堵率：最高防守概率 / 最高进攻概率
    top_def_prob = defenders[0]["probability"] if defenders else 0
    top_att_prob = attackers[0]["probability"] if attackers else 1
    block_rate = min(1.0, top_def_prob / max(top_att_prob, 0.01))

    return {
        "players": [
            *[{
                "id": f"att-{i}",
                "x": to_px(p["position"][0]),
                "y": to_py(p["position"][1]),
                "role": "attacker",
                "label": f"#{p['player_index']}",
                "is_top": p == top_attacker,
                "probability": p.get("probability", 0),
            } for i, p in enumerate(attackers[:5])],
            *[{
                "id": f"def-{i}",
                "x": to_px(p["position"][0]),
                "y": to_py(p["position"][1]),
                "role": "defender",
                "label": "",
                "is_top": False,
                "probability": p.get("probability", 0),
            } for i, p in enumerate(defenders[:5])],
        ],
        "ball": {"x": arrow_from[0], "y": arrow_from[1]},
        "highlight": {
            "x": arrow_to[0],
            "y": arrow_to[1],
            "label": "接球最高概率",
        },
        "arrow": {
            "from_x": arrow_from[0], "from_y": arrow_from[1],
            "to_x": arrow_to[0], "to_y": arrow_to[1],
            "label": "内旋球路线",
        },
        "cards": [
            {"type": "term", "title": "近门柱", "sub": "离球最近的球门柱"},
            {"type": "data", "title": "接球概率",
             "value": f"{top_att_prob*100:.0f}%"},
            {"type": "data", "title": "防守封堵率",
             "value": f"{block_rate*100:.0f}%"},
        ],
        "title": f"⚽ 角球战术分析 — {corner_entry.get('match', '')}" if corner_entry else "⚽ 角球战术分析",
        "duration": max(3.0, segment_duration),
    }


def render_mg_clip(variables: dict, output_name: str) -> Optional[str]:
    """调用 HyperFrames 渲染一段 MG 动画。

    Returns: 渲染后的 MP4 文件路径，失败返回 None
    """
    RENDER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RENDER_OUTPUT_DIR / f"{output_name}.mp4"

    # 如果已经渲染过，跳过（幂等）
    if output_path.exists():
        return str(output_path)

    # 把变量写入临时 JSON 文件
    var_file = RENDER_OUTPUT_DIR / f"{output_name}_vars.json"
    with open(var_file, "w", encoding="utf-8") as f:
        json.dump(variables, f, ensure_ascii=False)

    cmd = [
        "npx.cmd", "hyperframes", "render",
        "--composition", str(TEMPLATE_HTML),
        "--variables-file", str(var_file),
        "--width", "1280", "--height", "720",
        "--fps", "30",
        "--quality", "standard",
        "-o", str(output_path),
        str(TEMPLATE_DIR),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=RENDER_TIMEOUT)
        if result.returncode == 0 and output_path.exists():
            return str(output_path)
        else:
            print(f"[mg_renderer] Render failed: {result.stderr[-500:]}")
            return None
    except subprocess.TimeoutExpired:
        print(f"[mg_renderer] Render timeout after {RENDER_TIMEOUT}s")
        return None
    except Exception as e:
        print(f"[mg_renderer] Render error: {e}")
        return None


def render_all_mg_clips(scene_segments: list[dict], predictions: list[dict],
                        mapping: dict, corner_entry: dict, prefix: str) -> dict:
    """为所有 ai_scene 段批量渲染 MG 动画。

    Returns: {segment_index: clip_path_or_none}
    """
    results = {}
    for i, seg in enumerate(scene_segments):
        if seg.get("visual_type") != "ai_scene":
            continue
        variables = build_scene_variables(
            predictions, mapping, seg["actual_duration_sec"], corner_entry
        )
        clip_path = render_mg_clip(variables, f"{prefix}mg_{i:03d}")
        results[i] = clip_path
        print(f"[mg_renderer] Segment {i}: {'OK' if clip_path else 'FAILED'} "
              f"({seg['actual_duration_sec']:.1f}s → {variables['duration']:.1f}s)")
    return results
