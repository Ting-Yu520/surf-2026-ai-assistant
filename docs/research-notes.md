# Research Notes — SURF-2026-0154 AI Tactical Assistant

## 关键论文

### 核心参考

| 论文 | 发表 | 关键发现 | 与本项目关系 |
|------|------|---------|-------------|
| **TacticAI** (Wang et al.) | Nature Comms 2024 | GNN+群等变CNN预测角球；AI建议90%优于人类教练 | 证明AI能理解战术；但我们填补"面向非专家"的空白 |
| **SportsBuddy** (Harvard/UMN) | IEEE PacificVis 2025 | AI体育视频故事化工具，部署150+用户 | 竞品分析：仍面向已有兴趣的球迷 |
| **Sportify** (Harvard/UMN) | IEEE TVCG | LLM+RAG篮球战术VQA | LLM+体育的可行性证明 |
| **PXAI-Coach** (Stevens) | ABC 2025 | 运动健康XAI仪表盘，27人用户研究 | 用户研究方法参考 |

### HCI + 体育分析

| 论文 | 发表 | 关键发现 |
|------|------|---------|
| Cricket XAI (TU Delft) | 2025 | 按专业水平分层解释：初级→视觉、中级→对比、专家→统计 |
| AI Fitness Feedback (Shalawadi et al.) | DIS 2026 | 新手用户对AI运动反馈的4种张力类型 |
| Democratizing Soccer Data (Malmö) | 2024 | 足球数据叙事对非数据专家的可访问性 |

## 目标发表渠道

| 渠道 | 级别 | 接收率 | 投稿时间 | 匹配原因 |
|------|------|--------|---------|---------|
| **ACM CHI** | CCF-A, HCI #1 | ~25% | 约每年9月 | AI叙事+用户体验 |
| **ACM IUI** | HCI专项 | ~24% | 约每年10月 | 智能UI+AI生成内容 |
| **ACM DIS** | HCI专项 | ~28% | 约每年11月 | 交互系统设计+用户评估 |
| **IEEE TVCG** | SCI一区, CCF-A | ~25% | 滚动 | 可视化+体育 |
| **ACM CSCW** | CCF-A | ~25% | 约每年4/10月 | 人机协作+AI辅助理解 |

## 用户研究方法论

### 量表
- **NASA-TLX**: 认知负荷（6维度：脑力需求、体力需求、时间压力、努力程度、绩效、挫折）
- **SUS (System Usability Scale)**: 系统可用性
- **自研量表**: 趣味性、理解度、观看意愿

### 实验设计
- **设计**: 被试间设计（Between-subjects）
- **自变量**: 解说类型（传统 vs AI生成）
- **因变量**: 认知负荷、理解准确度、观看意愿
- **样本量**: ≥30人/组（G*Power先行计算）
- **统计**: 独立样本t检验 / Mann-Whitney U（非正态）

## 待读文献清单
- [ ] Rapp & Tirabeni (2018) Personal informatics for sport — ACM TOCHI
- [ ] Clegg et al. (2020) Data Everyday in Division I Sports — ACM CHI
- [ ] Wang et al. (2019) Designing Theory-Driven User-Centric XAI — ACM CHI
- [ ] TacticAI 完整论文 + Supplementary Materials
- [ ] Sportify 系统架构细节
- [ ] SportsBuddy 部署数据和用户反馈
