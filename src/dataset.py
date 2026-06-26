"""
数据集管理模块 — 2026 世界杯角球语料库

支持：加载数据集、筛选、添加新条目、批量处理
设计原则：与 VLM/LLM/TTS 模块完全解耦，只管理数据
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CornerKickEntry:
    """单个角球事件的数据结构"""
    entry_id: str
    match: str
    group: str
    date: str
    minute: str
    score_at_time: str
    corner_type: str
    kick_taker: str
    goal_scorer: str
    goal_type: str
    result: str  # "goal" | "save" | "miss" | "clearance"
    video_urls: list[str] = field(default_factory=list)
    tactical_note: str = ""
    vlm_json: Optional[dict] = None  # VLM 提取的 JSON（处理时填充）
    narration: Optional[str] = None  # LLM 生成的故事（处理时填充）


class CornerKickDataset:
    """
    2026 世界杯角球数据集。

    用法:
        ds = CornerKickDataset()
        entries = ds.filter_by_team("Netherlands")
        ds.process_all(pipeline_func)
    """

    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = Path(__file__).parent / "data" / "corner_kicks_2026.json"
        self.data_path = Path(data_path)
        self.entries: list[CornerKickEntry] = []
        self._load()

    def _load(self):
        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for e in data.get("entries", []):
            self.entries.append(CornerKickEntry(
                entry_id=e.get("id", ""),
                match=e.get("match", ""),
                group=e.get("group", ""),
                date=e.get("date", ""),
                minute=e.get("minute", ""),
                score_at_time=e.get("score_at_time", ""),
                corner_type=e.get("corner_type", ""),
                kick_taker=e.get("kick_taker", ""),
                goal_scorer=e.get("goal_scorer", ""),
                goal_type=e.get("goal_type", ""),
                result=e.get("result", ""),
                video_urls=e.get("video_urls", []),
                tactical_note=e.get("tactical_note", ""),
            ))
        self.metadata = {k: v for k, v in data.items() if k != "entries"}

    def filter_by_team(self, team: str) -> list[CornerKickEntry]:
        """按球队名筛选"""
        return [e for e in self.entries if team.lower() in e.match.lower()]

    def filter_by_result(self, result: str) -> list[CornerKickEntry]:
        """按结果筛选: goal / save / miss"""
        return [e for e in self.entries if e.result == result]

    def filter_by_type(self, corner_type: str) -> list[CornerKickEntry]:
        """按角球类型筛选: in-swinging / short_corner / scramble"""
        return [e for e in self.entries if corner_type in e.corner_type]

    def get_goal_entries(self) -> list[CornerKickEntry]:
        return self.filter_by_result("goal")

    def add_entry(self, entry: CornerKickEntry):
        """添加新角球条目（世界杯进行中可以不断添加）"""
        self.entries.append(entry)
        self._save()

    def _save(self):
        """保存数据集回 JSON 文件"""
        data = {
            **self.metadata,
            "total_entries": len(self.entries),
            "entries": [
                {
                    "id": e.entry_id,
                    "match": e.match,
                    "group": e.group,
                    "date": e.date,
                    "minute": e.minute,
                    "score_at_time": e.score_at_time,
                    "corner_type": e.corner_type,
                    "kick_taker": e.kick_taker,
                    "goal_scorer": e.goal_scorer,
                    "goal_type": e.goal_type,
                    "result": e.result,
                    "video_urls": e.video_urls,
                    "tactical_note": e.tactical_note,
                }
                for e in self.entries
            ],
        }
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def __len__(self):
        return len(self.entries)

    def __repr__(self):
        return f"CornerKickDataset({len(self)} entries, {self.data_path})"
