"""
SoccerAgent 增强桥接 — 利用 DeepSeek API + 本地数据库提取比赛上下文。

SoccerAgent 本身用 DeepSeek (deepseek-chat) 做文本推理，
这里直接用 SURF 项目已有的 DeepSeek API 密钥，无需额外配置。

用法:
  from phase1_socceragent import SoccerAgentEnhanced

  sa = SoccerAgentEnhanced()
  context = sa.analyze_match("Croatia vs Ghana")

工具链（按 SoccerAgent 架构）:
  Game Search → Game Info Retrieval → Match History Retrieval
  文本数据库查询 (game_database.csv)
  DeepSeek LLM 增强问答
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd


ROOT = Path(__file__).parent.parent
SA_ROOT = ROOT / "phase1" / "tools" / "soccer-agent"
DB_CSV = SA_ROOT / "database" / "Game_dataset_csv" / "game_database.csv"
GAME_DATASET = SA_ROOT / "database" / "Game_dataset"


class SoccerAgentEnhanced:
    """
    SoccerAgent 核心文本能力封装。
    无需模型下载，基于 game_database.csv + DeepSeek LLM。
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        from openai import OpenAI

        api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        # DeepSeek 的 OpenAI 兼容端点是 /v1
        base_url = base_url or "https://api.deepseek.com/v1"

        self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None
        self._db = self._load_database()
        self._games_index = self._build_games_index()

        print(f"[SoccerAgent] Database: {len(self._db)} games, "
              f"{len(self._games_index)} teams indexed")

    # ================================================================
    # 数据库层
    # ================================================================

    def _load_database(self) -> pd.DataFrame:
        if DB_CSV.exists():
            return pd.read_csv(DB_CSV)
        return pd.DataFrame()

    def _build_games_index(self) -> Dict[str, List[Path]]:
        """建立 球队名 → JSON 文件路径 索引"""
        index = {}
        if not GAME_DATASET.exists():
            return index

        for league_dir in GAME_DATASET.iterdir():
            if not league_dir.is_dir() or league_dir.name.startswith('.'):
                continue
            for match_dir in league_dir.iterdir():
                if match_dir.is_dir():
                    # 从目录名提取球队名
                    parts = match_dir.name.lower()
                    for json_file in match_dir.glob("*.json"):
                        index.setdefault(parts, []).append(json_file)
        return index

    def _find_match_json(self, team_a: str, team_b: str) -> Optional[Path]:
        """模糊搜索比赛 JSON"""
        a_lower = team_a.lower()
        b_lower = team_b.lower()

        # 精确匹配
        for key, paths in self._games_index.items():
            if a_lower in key and b_lower in key:
                return paths[0]

        # 部分匹配
        for key, paths in self._games_index.items():
            if a_lower in key or b_lower in key:
                return paths[0]

        return None

    # ================================================================
    # 游戏搜索 (Game Search) — DeepSeek 提取结构化信息
    # ================================================================

    def game_search(self, query: str) -> Optional[Dict]:
        """
        从自然语言描述中提取比赛信息。
        利用 DeepSeek + game_database.csv。
        """
        # 先尝试 CSV 直接匹配
        csv_match = self._csv_search(query)
        if csv_match:
            return csv_match

        # 否则用 LLM 提取
        if self.client:
            return self._llm_game_search(query)

        return None

    def _csv_search(self, query: str) -> Optional[Dict]:
        """在 CSV 数据库中搜索比赛"""
        if self._db.empty:
            return None

        # 关键词搜索
        query_lower = query.lower()
        for _, row in self._db.iterrows():
            row_str = str(row.values).lower()
            # 检查是否包含两支球队
            parts = query_lower.replace(" vs ", " ").replace(" v ", " ").split()
            team_matches = sum(1 for p in parts if len(p) > 2 and p in row_str)
            if team_matches >= 2:
                return {
                    "league": str(row.get("league", row.get("competition", ""))),
                    "season": str(row.get("season", "")),
                    "date": str(row.get("date", "")),
                    "home_team": str(row.get("home_team", "")),
                    "away_team": str(row.get("away_team", "")),
                    "score": str(row.get("score", "")),
                    "referee": str(row.get("referee", "")),
                    "venue": str(row.get("venue", row.get("stadium", ""))),
                    "attendance": str(row.get("attendance", "")),
                }
        return None

    def _llm_game_search(self, query: str) -> Optional[Dict]:
        """用 DeepSeek 从查询中提取结构化比赛信息"""
        prompt = f"""Extract structured football match information from this query.
Return ONLY valid JSON, no other text.

Query: {query}

Format:
{{
    "league": "competition name or unknown",
    "season": "xxxx-xxxx or unknown",
    "date": "YYYY-MM-DD or unknown",
    "teams": ["team1", "team2"],
    "score": "x - x or unknown"
}}

JSON:"""

        try:
            resp = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=200,
            )
            text = resp.choices[0].message.content.strip()
            # 提取 JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"  [SoccerAgent] LLM game_search failed: {e}")

        return None

    # ================================================================
    # 比赛信息检索 (Game Info Retrieval)
    # ================================================================

    def game_info(self, match_json_path: Path) -> Dict:
        """从比赛 JSON 文件提取赛前信息"""
        if not match_json_path.exists():
            return {}

        try:
            with open(match_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return {
                "referee": data.get("referee", ""),
                "venue": data.get("venue", data.get("stadium_name", "")),
                "attendance": data.get("attendance", ""),
                "home_formation": data.get("home_team_formation", ""),
                "away_formation": data.get("away_team_formation", ""),
                "home_manager": data.get("home_team_manager", ""),
                "away_manager": data.get("away_team_manager", ""),
                "competition": data.get("competition", ""),
                "season": data.get("season", ""),
            }
        except Exception:
            return {}

    # ================================================================
    # 实体搜索 (Textual Entity Search)
    # ================================================================

    def entity_search(self, entity_name: str) -> Optional[Dict]:
        """
        搜索球员/球队背景信息。
        先用 CSV 搜索，再用 LLM 补充。
        """
        if self._db.empty:
            return None

        for _, row in self._db.iterrows():
            row_str = str(row.values).lower()
            if entity_name.lower() in row_str:
                return {
                    "name": entity_name,
                    "found_in": str(row.get("league", "")),
                    "raw": {k: str(v) for k, v in row.items() if pd.notna(v)},
                }
        return None

    # ================================================================
    # 高层接口 — 用于 Phase 1 → Phase 2
    # ================================================================

    def analyze_match(self, match_desc: str) -> Dict:
        """
        给定比赛描述，返回丰富的结构化上下文。
        这是 Phase 1 → Phase 2 的主入口。
        """
        result = {
            "match_query": match_desc,
            "game_search": None,
            "game_info": {},
            "teams_extracted": [],
            "entities": {},
        }

        # Step 1: Game Search
        game = self.game_search(match_desc)
        result["game_search"] = game

        if game and "teams" in game:
            result["teams_extracted"] = game["teams"]

        # Step 2: 如果有 JSON 匹配，获取详细信息
        if game and "teams" in game and len(game["teams"]) >= 2:
            json_path = self._find_match_json(game["teams"][0], game["teams"][1])
            if json_path:
                result["game_info"] = self.game_info(json_path)

        # Step 3: 提取关键实体
        # 尝试识别进球者、踢球者
        for entity in ["Modrić", "Vlašić", "Messi", "Ronaldo", "Mbappé",
                        "Salah", "Kane", "De Bruyne", "Bellingham", "Musiala"]:
            if entity.lower() in match_desc.lower():
                ent_info = self.entity_search(entity)
                if ent_info:
                    result["entities"][entity] = ent_info

        return result

    def enhance_corner_entry(self, corner_entry: Dict) -> Dict:
        """
        增强 Phase 2 角球条目的比赛上下文。
        """
        match = corner_entry.get("match", "")
        kick_taker = corner_entry.get("kick_taker", "")
        scorer = corner_entry.get("goal_scorer", "")

        context = self.analyze_match(match)
        game = context.get("game_search") or {}
        game_info = context.get("game_info") or {}

        # 构建增强的 fact_section
        facts = []
        if match:
            facts.append(f"比赛：{match}")
        if game.get("date") and game["date"] != "unknown":
            facts.append(f"日期：{game['date']}")
        if corner_entry.get("minute") and corner_entry["minute"] != "unknown":
            facts.append(f"时间：{corner_entry['minute']}'")
        else:
            facts.append(f"时间：比赛某时刻")
        if kick_taker and kick_taker != "unknown":
            facts.append(f"角球主罚：{kick_taker}")
        if scorer and scorer != "unknown":
            facts.append(f"进球者：{scorer}")
        if corner_entry.get("score_at_time"):
            facts.append(f"当时比分：{corner_entry['score_at_time']}")
        if game.get("venue"):
            facts.append(f"场馆：{game['venue']}")
        if game.get("referee"):
            facts.append(f"主裁判：{game['referee']}")
        if game.get("attendance"):
            facts.append(f"观众人数：{game['attendance']}")
        if game_info.get("home_formation"):
            facts.append(f"主队阵型：{game_info['home_formation']}")
        if game_info.get("away_formation"):
            facts.append(f"客队阵型：{game_info['away_formation']}")
        if corner_entry.get("tactical_note"):
            facts.append(f"战术描述：{corner_entry['tactical_note']}")

        return {
            "corner_id": corner_entry.get("id"),
            "fact_section": "\n".join(facts),
            "socceragent_context": context,
        }


# ================================================================
# 自检
# ================================================================

if __name__ == "__main__":
    # 设置 API 密钥
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    sa = SoccerAgentEnhanced()

    # 测试
    print("\n--- Test 1: 比赛搜索 ---")
    result = sa.analyze_match("Croatia vs Ghana World Cup 2026")
    print(json.dumps(result["game_search"], indent=2, ensure_ascii=False))

    print("\n--- Test 2: 角球增强 ---")
    corner = {
        "id": "wc2026-corner-021",
        "match": "Croatia vs Ghana",
        "minute": "unknown",
        "score_at_time": "Croatia 1-0 Ghana",
        "corner_type": "in-swinging",
        "kick_taker": "Luka Modrić",
        "goal_scorer": "Nikola Vlašić",
        "tactical_note": "Modrić delivered a trademark precise corner.",
    }
    enhanced = sa.enhance_corner_entry(corner)
    print(enhanced["fact_section"])
