# 📚 Literature Review — SURF-2026-0154 AI Tactical Assistant

**Updated:** 2026-06-30
**Purpose:** 足球 AI + 多模态 + HCI 相关论文系统分析，为项目提供学术定位和设计参考

---

## Paper Map (论文地图)

```
                    ┌──────────────────────────────┐
                    │   Our Project: Generative HCI │
                    │   for Sports Analytics        │
                    │   (新手足球战术科普)             │
                    └──────────────┬───────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Football AI Core │    │ Multi-Modal Gen │    │ HCI + User Study │
│ (战术理解层)      │    │ (内容生成层)      │    │ (用户体验层)      │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ ① TacticAI      │    │ ③ TimeSoccer    │    │ ⑦ SportsBuddy   │
│ ② MatchVision   │    │ ④ SoccerComment │    │ ⑧ Sportify       │
│    SoccerReplay  │    │ ⑤ MatchTime     │    │ ⑨ XAI Narrative  │
│                 │    │ ⑥ ExpertComment │    │ ⑩ VR Exergame   │
│                 │    │ ⑪ DHMDL         │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │ ⑫ OPC AI Agent (架构参考)    │
                    │ Multi-Agent + Multi-Modal    │
                    │ Fusion (我们的设计蓝图)        │
                    └─────────────────────────────┘
```

---

## Category 1: Football AI Core (战术理解层)

### ① TacticAI — DeepMind + Liverpool FC
| Field | Detail |
|-------|--------|
| **Title** | TacticAI: an AI assistant for football tactics |
| **Authors** | Zhe Wang, Petar Veličković, et al. (23 authors) |
| **Venue** | Nature Communications, Vol. 15, Mar 2024 |
| **DOI** | 10.1038/s41467-024-45965-x |
| **PDF** | [Nature Comms](https://www.nature.com/articles/s41467-024-45965-x) |

**核心方法：**
- 将角球建模为图（节点=球员，边=关系），使用 **GNN + D2 群等变卷积** 利用足球场的反射对称性
- 三个组件：接收者预测 → 射门预测 → 生成式战术优化（Autoencoder-based）
- 7176 个角球训练，来自 2020-21 英超赛季

**关键结果：**
- 接收者 Top-3 准确率：**78.2%**
- AI 建议在 **90%** 情况下优于人类教练
- 人类专家无法区分 AI 生成 vs 真实战术

**对我们的启示：** 角球是 AI 体育分析的最佳切入点——固定位置、频繁发生、战术密集。TacticAI 证明 AI 能"理解"角球战术，但它输出的是概率和坐标（给教练看的）。我们要做的是**把同样的数据翻译成新手能理解的故事**——这就是"最后一公里"。

---

### ② MatchVision + SoccerReplay-1988 — CVPR 2025
| Field | Detail |
|-------|--------|
| **Title** | Towards Universal Soccer Video Understanding |
| **Authors** | (Multi-institutional) |
| **Venue** | CVPR 2025 |
| **DOI** | IEEE Xplore |

**核心贡献：**
- **SoccerReplay-1988**：最大的多模态足球数据集（1988 场完整比赛，自动标注）
- **MatchVision**：足球专用时空视觉编码器
- 支持：事件分类 / 解说生成 / 多视角犯规识别

**对我们的启示：** 这是足球视频理解的 SOTA 基准。如果我们做 VLM 视频帧分析，可以用 SoccerReplay-1988 的标注格式作为参考 Schema。

---

## Category 2: Multi-Modal Generation (内容生成层)

### ③ TimeSoccer — ACM Multimedia 2025
| Field | Detail |
|-------|--------|
| **Title** | TimeSoccer: An End-to-End Multimodal Large Language Model for Soccer Commentary Generation |
| **Authors** | Ling You*, Wenxuan Huang*, Xinni Xie, Xiangyi Wei, Bangyan Li, Shaohui Lin†, Yang Li†, Changbo Wang |
| **Affiliation** | East China Normal University |
| **Venue** | ACM Multimedia 2025 |
| **arXiv** | 2504.17365 |

**核心方法：**
- 首个**端到端**足球 MLLM：一次性预测时间戳 + 生成解说（不需要两步 Pipeline）
- **MoFA-Select**：训练无关的运动感知帧压缩——粗到细策略压缩 45 分钟长视频
- 渐进式训练 + 位置编码外推处理长序列

**关键结果：** SoccerNet-Caption 数据集上 SOTA

**对我们的启示：** 端到端是大趋势，但我们不一定要走这条路。MoFA-Select 的运动感知帧选择思路可以借鉴——我们的 VLM Agent 也可以用类似策略从视频中智能选取关键帧。

---

### ④ SoccerComment — WACV 2025
| Field | Detail |
|-------|--------|
| **Title** | Multi-Modal Large Language Model with RAG Strategies in Soccer Commentary Generation |
| **Authors** | Xiang Li, Yangfan He, Shuaishuai Zu, Zhengyang Li, Tianyu Shi, Yiting Xie, Kevin Zhang |
| **Venue** | WACV 2025, pp. 6197-6206 |

**核心方法：**
- **RAG (检索增强生成)** + MLLM：用多模态聚类记忆单元检索相似历史场景
- 强零样本性能——不需要持续重训

**对我们的启示：** RAG 可以让我们用已有的 21 条角球解说 + TacticAI 数据库做"案例检索"，新角球进来时找到最相似的旧案例作为参考。这比每次从零生成更稳定、更准确。

---

### ⑤ MatchTime — EMNLP 2024 Oral
| Field | Detail |
|-------|--------|
| **Title** | MatchTime: Towards Automatic Soccer Game Commentary Generation |
| **Authors** | Jiayuan Rao, Haoning Wu, Chang Liu, Yanfeng Wang, Weidi Xie |
| **Affiliation** | Shanghai Jiao Tong University & Shanghai AI Laboratory |
| **Venue** | EMNLP 2024 (Oral) |
| **Code** | [github.com/jyrao/MatchTime](https://github.com/jyrao/MatchTime) |

**核心贡献：**
- **SN-Caption-test-align** 基准：手动标注 49 场比赛的时间戳，修复视频-文本对齐问题
- **MatchTime 数据集**：自动校正的对齐解说数据
- **MatchVoice 模型**：Perceiver 架构 + 冻结 LLM 解码器

**对我们的启示：** 这是 Phase 1 的工具之一（已克隆到 phase1/tools/）。核心价值在于**视频-文本对齐**——我们的 VLM Agent 也需要做类似的对齐，确保提取的战术信息与视频帧准确对应。

---

### ⑥ Expert Comment Generation — Sensors 2025
| Field | Detail |
|-------|--------|
| **Title** | Expert Comment Generation Considering Sports Skill Level Using a Large Multimodal Model with Video and Spatial-Temporal Motion Features |
| **Authors** | Tatsuki Seino, Naoki Saito, Takahiro Ogawa, Satoshi Asamizu, Miki Haseyama |
| **Affiliation** | Hokkaido University |
| **Venue** | Sensors, 25(2), 447, Jan 2025 |

**核心方法：**
- **STA-GCN** (时空注意力图卷积) 提取运动特征 + 技能水平分类
- 将技能水平标签 + 运动特征 + 视频输入 LMM → 生成**分层个性化反馈**

**对我们的启示：** 按受众水平分层生成内容的思路，与我们"面向新手 vs 面向球迷"的多级输出理念一致。未来可以做一个"知识深度选择器"——用户选"我完全不懂足球"或"我偶尔看球"。

---

### ⑪ DHMDL — Applied AI 2025
| Field | Detail |
|-------|--------|
| **Title** | DHMDL: Dynamically Hashed Multimodal Deep Learning Framework for Racket Video Summarization |
| **Venue** | Applied Artificial Intelligence, Feb 2025 |

**核心方法：** 融合解说员声音 + 观众欢呼 + 球员面部表情 → 精彩片段提取

**对我们的启示：** 多模态融合的另一种思路——不只是视频+文本，还可以加入音频情绪检测。我们的 TTS Agent 目前只做输出（生成语音），未来也可以加"输入音频分析"（球场噪音、解说情绪）来辅助判断关键时刻。

---

## Category 3: HCI + User Study (用户体验层)

### ⑦ SportsBuddy — IEEE PacificVis 2025
| Field | Detail |
|-------|--------|
| **Title** | SportsBuddy: Designing and Evaluating an AI-Powered Sports Video Storytelling Tool Through Real-World Deployment |
| **Authors** | Tica Lin, Ruxun Xiang, Gardenia Liu, Divyanshu Tiwari, Meng-Chia Chiang, Chenjiayi Ye, Hanspeter Pfister, Chen Zhu-Tian |
| **Affiliation** | Harvard Visual Computing Group & University of Minnesota |
| **Venue** | IEEE PacificVis 2025, pp. 214-223 |
| **arXiv** | 2502.08621 |

**核心方法：**
- 视频编辑工具：球员追踪 + 嵌入式交互 + 时间线可视化
- **真实部署 150+ 用户**：教练、运动员、内容创作者、家长、球迷

**对我们的启示：** 这是最直接的竞品参考。SportsBuddy 面向"懂球的人做视频"，我们是"让不懂球的人看懂视频"。用户群体互补，可以引用它作为 Related Work 来论证我们的差异化定位。**150+ 真实用户**也是我们 FYP 用户研究设计的参考。

---

### ⑧ Sportify — IEEE TVCG 2025
| Field | Detail |
|-------|--------|
| **Title** | Sportify: Question Answering with Embedded Visualizations and Personified Narratives for Sports Video |
| **Authors** | Chunggi Lee, Tica Lin, Hanspeter Pfister, Zhutian Chen |
| **Venue** | IEEE TVCG, Jan 2025, 31(1):12-22 |
| **DOI** | 10.1109/TVCG.2024.3456332 |

**核心方法：** QA + 嵌入可视化 + **拟人化叙事** 用于体育视频

**对我们的启示：** "Personified Narratives"（拟人化叙事）跟我们的"二人转"策略高度一致。Sportify 用的是单人拟人，我们用双人对抗式拟人——可以论证我们的方法在"降低认知门槛"上更优。

---

### ⑨ LLM Narrative Gamification for XAI — CHI EA 2025
| Field | Detail |
|-------|--------|
| **Title** | Enhancing AI Explainability for Non-technical Users with LLM-Driven Narrative Gamification |
| **Authors** | Yuzhe You, Helen Weixu Chen, Jian Zhao |
| **Affiliation** | University of Waterloo |
| **Venue** | CHI EA 2025 |

**核心方法：** LLM 驱动的叙事游戏化 + 可视化，帮助非技术用户理解 AI 模型

**对我们的启示：** 直接证明了"LLM 可以把复杂技术概念翻译给非专业用户"这个核心假设。我们把它搬到体育领域——相当于 "XAI for Sports"。

---

### ⑩ LLM + VR Exergame Data Visualization — CHI EA 2025
| Field | Detail |
|-------|--------|
| **Title** | Visualizing Exercise Data from Combat Exergame for Exploring the Insight from Personal Informatics with Large Language Models |
| **Authors** | Zong-Ying Li, Yen-Hua Lai, Chi-Yu Lin, Chien-Hsing Chou, Ping-Hsuan Han |
| **Affiliation** | National Taipei University of Technology |
| **Venue** | CHI EA 2025 |

**核心方法：** VR 运动数据 + LLM 个性化叙事 → 促进自我反思

**对我们的启示：** 体育数据 + LLM 叙事在 HCI 领域是被认可的范式。可以作为 Related Work 中的一条引用线。

---

## Category 4: Architecture Reference (架构参考)

### ⑫ OPC AI Agent — IEEE (导师学生论文)
| Field | Detail |
|-------|--------|
| **Title** | One Person Company (OPC) AI Agents System with Multi-Modal Fusion for Health Assistance |
| **Authors** | Xinzhi Li, Nanlin Jin*, Wenning Ma, John R. Woodward, Steven Guan, Baibing Mi |
| **Affiliation** | XJTLU + Heriot-Watt + Xi'an Jiaotong University |
| **PDF** | `papers/2025_IEEE_OPC_AI_Agent_MultiModal_Fusion_Li_XJTLU.pdf` |

**核心贡献：**
- **OPC 概念**：一人管多 Agent → 数字员工
- **三层架构**：支撑层 → 多 Agent 执行层 → 应用层
- **决策级融合**：6 个 Agent 独立处理 → Fusion Agent 综合输出
- **多模态融合**：文本 + 生理信号 + 音视频

**对我们的启示：** 这是我们架构设计的**直接蓝图**。我们的 6 Agent 架构完全对标这篇论文：
- VideoAnalyzer ↔ BellScan + DropScan (CV)
- CommentaryGen ↔ StrokeVoice (NLP + 生成)
- VoiceGen ↔ StrokeVoice (语音)
- TacticalExtractor ↔ VitalRisk (数据处理)
- Fusion ↔ Fusion Agent (决策融合)

---

## Research Gap Summary

| 已有工作 | 做什么 | 不给谁做 |
|---------|--------|---------|
| TacticAI | 角球战术预测 | 不给教练以外的人 |
| TimeSoccer / SoccerComment | 自动足球解说 | 给球迷，用术语 |
| SportsBuddy / Sportify | 体育视频故事化 | 给已有兴趣的用户 |
| MatchVision | 足球视频理解 | 给研究人员 |

> **我们的位置：** 把专业 AI 的输出翻译给**完全不懂足球的新手**——不是做得更准，而是让更多人能懂。这是体育 AI 的"最后一公里"。

---

## Paper Priority for Deep Read

| Priority | Paper | Why |
|----------|-------|-----|
| 🔴 P0 | TacticAI | 角球 AI 的 SOTA，Related Work 核心引用 |
| 🔴 P0 | OPC AI Agent | 架构蓝图，导师推荐 |
| 🟡 P1 | SportsBuddy | 最接近的竞品，User Study 参考 |
| 🟡 P1 | TimeSoccer | 端到端足球 MLLM 最新进展 |
| 🟡 P1 | SoccerComment | RAG 增强解说，技术参考 |
| 🟢 P2 | MatchTime | Phase 1 工具已包含 |
| 🟢 P2 | Sportify | 拟人化叙事参考 |
| 🟢 P2 | XAI Narrative (CHI) | HCI 理论支持 |
