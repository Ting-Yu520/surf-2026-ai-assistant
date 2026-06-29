"""
MatchTime 接口预留 — 当硬件满足条件（>16GB VRAM）时可接入。

MatchTime (EMNLP 2024 Oral): 视频 → CLIP 特征 → MatchVoice(Q-Former + Llama-3-8B) → AI 解说

硬件要求:
  - GPU 显存 > 16GB（Llama-3-8B bf16 ≈ 16GB）
  - 或使用 int4 量化（待适配）

依赖:
  - openai-clip (ViT-B/32)
  - transformers >= 4.42.3
  - MatchVoice checkpoint: huggingface.co/Homie0609/MatchVoice
  - Llama-3-8B: huggingface.co/meta-llama/Meta-Llama-3-8B（需授权）

接入方式:
  1. 满足上述依赖
  2. 下载 MatchVoice checkpoint → phase1/tools/matchtime/ckpt/
  3. 修改下方 MATCHTIME_AVAILABLE = True
  4. Phase 1 管线自动调用 generate_commentary()
"""

from pathlib import Path
from typing import Optional, Dict

MATCHTIME_AVAILABLE = False  # ← 准备好后改为 True
MATCHTIME_CKPT = Path(__file__).parent.parent / "phase1" / "tools" / "matchtime" / "ckpt" / "CLIP_matchvoice.pth"


def generate_commentary(video_path: str, device: str = "cuda:0") -> Optional[str]:
    """
    MatchTime 单人 AI 解说生成。

    Args:
        video_path: 角球视频路径（30s clip）
        device: 推理设备

    Returns:
        AI 解说文本，或 None（不可用时）
    """
    if not MATCHTIME_AVAILABLE:
        return None

    # ================================================================
    # TODO: 实现 MatchTime 推理
    # 参考: phase1/tools/matchtime/inference_single_video_CLIP.py
    #
    # import clip
    # from models.matchvoice_model import matchvoice_model
    #
    # model, preprocess = clip.load("ViT/B-32", device=device)
    # clip_encoder = model.encode_image
    #
    # predict_model = matchvoice_model(
    #     llm_ckpt="meta-llama/Meta-Llama-3-8B",
    #     tokenizer_ckpt="meta-llama/Meta-Llama-3-8B",
    #     num_video_query_token=32, num_features=512,
    #     device=device, inference=True,
    # )
    # predict_model.load_state_dict(torch.load(MATCHTIME_CKPT))
    # predict_model.eval()
    #
    # 从视频提取 CLIP 特征 → MatchVoice 推理 → 返回解说文本
    # ================================================================
    pass


def commentary_to_phase2(commentary: str) -> Dict:
    """将 MatchTime 解说转为 Phase 2 兼容格式"""
    return {
        "source": "matchtime",
        "style": "single_narrator",
        "text": commentary,
    }
