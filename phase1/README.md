# Phase 1 — 视频 → 专业 JSON（工具集成层）

## 整体流程

```
比赛视频 (公开转播)
    │
    ▼
[Phase 1 工具] ← TacticAI Recreation / SoccerAgent / MatchTime
    │
    ▼
专业 JSON 数据 (球员位置、事件、战术分析)
    │
    ▼
───── Phase 1/2 接口界线 ─────
    │
    ▼
[Phase 2 管线] ← duo Prompt + TTS + 视频合成
    │
    ▼
新手友好科普视频
```

## 可用工具

| 工具 | 用途 | 状态 | 接入方式 |
|------|------|------|---------|
| **TacticAI Recreation** | 角球战术预测+分析 | ✅ 代码全 | `git clone https://github.com/mattr-ta95/tactic-ai-recreation.git tools/tactic-ai-recreation` |
| **SoccerAgent** | 多智能体足球问答，理解视频 | ✅ 代码+数据 | `git clone https://github.com/jyrao/SoccerAgent.git tools/soccer-agent` |
| **MatchTime** | 自动足球解说生成 | ✅ 代码+模型 | `git clone https://github.com/jyrao/MatchTime.git tools/matchtime` |
| **SoccerMaster** | 视觉基础模型（检测/注册/事件） | ⚠️ 模型待发布 | `git clone https://github.com/haolinyang-hlyang/SoccerMaster.git tools/soccer-master` |

## 接入方法

每个工具克隆到 `phase1/tools/` 目录后：

```bash
cd phase1/tools
git clone https://github.com/mattr-ta95/tactic-ai-recreation.git
git clone https://github.com/jyrao/SoccerAgent.git
git clone https://github.com/jyrao/MatchTime.git
```

工具的 JSON 输出格式 → 对齐到 Phase 2 的 `src/data/corner_kicks_2026.json` Schema。

## 详细参考

详见 [docs/open-source-tools.md](docs/open-source-tools.md)
