"""Agent 3: LLM duo-commentary generation.

Uses core/llm_client.py for generic LLM calling — no hardcoded API logic.
Prompt templates are loaded from prompts/*.txt at runtime.
"""
from pathlib import Path

from core.interfaces import BaseAgent, AgentInput, AgentOutput
from core.config_loader import load_yaml_and_env
from core.llm_client import create_client, call_llm
from core.logging import get_logger
from core.exceptions import ModelCallError

logger = get_logger("commentary_gen")


class CommentaryGenerator(BaseAgent):
    """Generate duo-commentary (A: 懂哥 + B: 小白) from tactical data."""

    def load_config(self) -> dict:
        return load_yaml_and_env("agents/commentary_gen/config.yaml")

    def run(self, agent_input: AgentInput) -> AgentOutput:
        fact_section = agent_input.data.get("fact_section", "")
        tactic_section = agent_input.data.get("tactic_section", "")

        system_prompt = self._load_prompt("system.txt")
        user_message = self._build_user_message(fact_section, tactic_section)

        api_key = self.config.get("api_key", "")
        if not api_key:
            return AgentOutput(
                status="error", data={}, agent_name="commentary_gen",
                error="No API key configured (set DEEPSEEK_API_KEY in secrets.env)",
            )

        client = create_client(
            base_url=self.config["base_url"],
            api_key=api_key,
            timeout=self.config.get("timeout", 60),
        )

        try:
            script = call_llm(
                client=client,
                model=self.config["model"],
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=self.config.get("max_tokens", 2048),
                temperature=self.config.get("temperature", 0.85),
            )
        except ModelCallError as e:
            logger.error(f"LLM call failed: {e}")
            return AgentOutput(
                status="error", data={}, agent_name="commentary_gen",
                error=str(e),
            )

        return AgentOutput(
            status="ok",
            data={"script": script},
            agent_name="commentary_gen",
        )

    def validate(self, output: AgentOutput) -> bool:
        script = output.data.get("script", "")
        return len(script) > 50 and ("A:" in script or "B:" in script)

    def _load_prompt(self, filename: str) -> str:
        path = Path(__file__).parent / "prompts" / filename
        if not path.exists():
            logger.warning(f"Prompt file not found: {path}")
            return ""
        return path.read_text(encoding="utf-8")

    def _build_user_message(self, fact: str, tactic: str) -> str:
        return f"""请根据下面的足球比赛信息，写一段双口相声科普脚本。

## 比赛事实
{fact}

## 战术彩蛋（可选）
下面这些战术分析数据 A 可偶尔引用：
{tactic}

## 要求
- 3-4 轮对话
- A 上来先卖弄知识
- B 一脸懵逼，逼 A 解释人话
- 最后 B 表示懂了
- 每段 A 台词后紧跟 ##VISUAL## 视觉指令
- 对话里不要出现坐标数字"""
