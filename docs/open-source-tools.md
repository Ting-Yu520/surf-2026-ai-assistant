# 开源足球 AI 工具清单

整理日期：2026-06-28
用途：作为 Phase 1（视频→专业 JSON/战术理解）的可复用工具池。

---

## 已发表论文的开源项目（高优先级）

| 项目 | 作者/机构 | 发表 | GitHub | 用途 | 可用代码 |
|------|---------|------|--------|------|---------|
| **TacticAI Recreation** | Mattr-TA95 | 社区版 | [mattr-ta95/tactic-ai-recreation](https://github.com/mattr-ta95/tactic-ai-recreation) | 角球战术预测与分析，含 API、可视化面板 | ✅ `src/` `data/` `configs/` `scripts/` |
| **SoccerMaster** | Haolin Yang (SJTU) | CVPR 2026 Oral | [haolinyang-hlyang/SoccerMaster](https://github.com/haolinyang-hlyang/SoccerMaster) | 足球视觉基础模型：球员检测、场地注册、事件分类 | ✅ `codes/`（代码）❌ 模型未发布 |
| **SoccerAgent** | Jiayuan Rao (SJTU) | ACM MM 2025 | [jyrao/SoccerAgent](https://github.com/jyrao/SoccerAgent) | 多智能体足球问答系统 | ✅ 完整代码+数据库 |
| **MatchTime** | Jiayuan Rao (SJTU) | EMNLP 2024 Oral | [jyrao/MatchTime](https://github.com/jyrao/MatchTime) | 自动足球解说生成 | ✅ 完整代码+模型 |
| **UniSoccer** | Jiayuan Rao (SJTU) | CVPR 2025 | [jyrao/UniSoccer](https://github.com/jyrao/UniSoccer) | 统一足球视频理解 | ✅ `web/` 主分支 |

## SoccerNet 官方工具系列

| 项目 | 用途 | GitHub |
|------|------|--------|
| **sn-spotting** | 动作检测（含角球标注 17 类） | [SoccerNet/sn-spotting](https://github.com/SoccerNet/sn-spotting) |
| **sn-tracking** | 球员追踪 | [SoccerNet/sn-tracking](https://github.com/SoccerNet/sn-tracking) |
| **sn-calibration** | 相机标定 | [SoccerNet/sn-calibration](https://github.com/SoccerNet/sn-calibration) |
| **SoccerNet-v3D** | 3D 场景重建 | [mguti97/SoccerNet-v3D](https://github.com/mguti97/SoccerNet-v3D) |
| **TACDEC** | 战术分析数据集 | [SimulaMet-HOST/TACDEC](https://huggingface.co/datasets/SimulaMet-HOST/TACDEC) |

## 社区工具

| 项目 | 用途 | GitHub |
|------|------|--------|
| **roboflow/sports** | 体育 CV 工具集 | [roboflow/sports](https://github.com/roboflow/sports) |
| **SoccerTrack-v2** | 4K 全景足球追踪 | [AtomScott/SoccerTrack-v2](https://github.com/AtomScott/SoccerTrack-v2) |

---

## 视频合成工具

| 项目 | 用途 | GitHub |
|------|------|--------|
| **OpenMontage** | AI 视频合成系统 | [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) |
