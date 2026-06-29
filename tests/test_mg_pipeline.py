"""端到端测试：真实数据 → LLM 脚本 → TTS → MG 渲染 → 合成"""
import json
import sys
import pytest
from pathlib import Path

# 遵循项目导入约定：将 src/ 加入 sys.path，使用裸 import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pipeline import process_corner_kick
from phase_bridge import get_real_predictions, build_field_mapping, get_real_or_sample

TEST_CORNER_ID = "wc2026-corner-021"
TEST_VIDEO = Path("data/videos/wc2026-corner-021.mp4")


def test_real_data_loading():
    """真实数据可正确加载"""
    preds = get_real_predictions(TEST_CORNER_ID)
    assert preds is not None, f"无法加载 {TEST_CORNER_ID} 的真实数据"
    assert len(preds["predictions"]) > 0
    assert all("position" in p for p in preds["predictions"])
    assert all("probability" in p for p in preds["predictions"])


def test_coordinate_mapping_adaptive():
    """坐标映射自适应数据范围，无越界"""
    preds = get_real_predictions(TEST_CORNER_ID)["predictions"]
    mapping = build_field_mapping(preds)
    assert mapping is not None

    for p in preds:
        px = mapping["to_px"](p["position"][0])
        py = mapping["to_py"](p["position"][1])
        assert 0 <= px <= 1280, f"X 越界: {px}"
        assert 0 <= py <= 720, f"Y 越界: {py}"


def test_scene_variables_built():
    """场景变量 JSON 构建成功"""
    from mg_renderer import build_scene_variables

    preds = get_real_predictions(TEST_CORNER_ID)["predictions"]
    mapping = build_field_mapping(preds)
    vars = build_scene_variables(preds, mapping, 6.5, {"match": "Croatia vs Ghana"})

    assert len(vars["players"]) > 0
    assert "x" in vars["players"][0]
    assert "y" in vars["players"][0]
    assert vars["duration"] > 0
    assert len(vars["cards"]) >= 1


def test_empty_predictions_handled():
    """空预测数据不崩溃"""
    from mg_renderer import build_scene_variables
    from phase_bridge import build_field_mapping

    vars = build_scene_variables([], build_field_mapping([]), 5.0)
    assert vars["players"] == []


def test_prompt_parsing_all_types():
    """三种 visual_type 正确解析"""
    from prompts.corner_kick import parse_duo_output

    sample = """A: 测试
##VISUAL## ai_scene
B: 问题
##VISUAL## clear
A: 回答
##VISUAL## highlight pos=(65,40)
"""
    segments = parse_duo_output(sample)
    types = [s["visual_type"] for s in segments]
    assert types == ["ai_scene", "clear", "highlight"]


@pytest.mark.slow
@pytest.mark.skipif(not TEST_VIDEO.exists(), reason="需要角球视频文件")
def test_full_pipeline_with_mg():
    """完整管线 + MG 动画生成"""
    with open("src/data/corner_kicks_2026.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data if isinstance(data, list) else data.get("entries", data)
    entry = next(e for e in entries if e.get("id") == TEST_CORNER_ID)

    result = process_corner_kick(
        video_path=str(TEST_VIDEO),
        corner_entry=entry,
        output_prefix="test_e2e",
    )

    assert "script" in result
    assert "audio_path" in result
    assert "output_video" in result
    assert Path(result["output_video"]).exists()

    # 验证 MG 动画 clip 文件存在
    mg_clips = result.get("mg_clips", {})
    for idx, path in mg_clips.items():
        if path:
            assert Path(path).exists(), f"MG clip {idx} 不存在: {path}"
