"""
TTS 客户端 — Edge TTS (免费，微软边缘浏览器 TTS 引擎)

功能：将中文文本转化为自然语音 (mp3)

使用方法：
    from tts_client import generate_audio
    audio_path = generate_audio("这是一段解说文本", "output.mp3")
"""

import asyncio
import edge_tts
from config import TTS_VOICE, TTS_SPEED


async def _generate(text: str, output_path: str) -> str:
    """异步生成语音文件"""
    communicate = edge_tts.Communicate(
        text=text,
        voice=TTS_VOICE,
        rate=TTS_SPEED,
    )
    await communicate.save(output_path)
    return output_path


def generate_audio(text: str, output_path: str) -> str:
    """
    生成中文语音文件。

    Args:
        text: 要朗读的中文文本
        output_path: 输出的 mp3 文件路径

    Returns:
        str: 音频文件路径
    """
    return asyncio.run(_generate(text, output_path))
