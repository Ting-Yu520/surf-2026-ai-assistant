---
name: surf-2026-project-init
description: SURF-2026-0154 AI Tactical Assistant 项目初始化上下文——项目背景、核心学术概念、三阶段路线图、AI 联合创始人工作原则
metadata:
  type: project
  originSessionId: surf-2026-init
---

# Initialization Context: SURF-2026-0154 AI Tactical Assistant

## 1. Project Background & Ultimate Goals
* **Project Name:** AI Tactical Assistant for World Cup 2026 (SURF program leading to Senior FYP).
* **Supervisors:** Dr. Nanlin Jin & Dr. Thomas Selig (XJTLU).
* **My Profile:** Information Management and Information Systems (IMIS) student. My core strengths are AI-Assisted Engineering, Prompt-Driven Development, and System Analysis, not training deep learning computer vision (CV) models from scratch.
* **Ultimate Goal:** Evolve this 10-week summer project into a Final Year Project (FYP) and publish a high-impact paper in the HCI (Human-Computer Interaction) or Applied AI domain.

## 2. The Core Academic Concept (The Pivot)
We are referencing DeepMind's "TacticAI", but we are making a strategic pivot:
* **What we are NOT doing:** We will not build predictive models for ball trajectories or player coordinates. We lack the proprietary 3D tracking data DeepMind has, and relying solely on broadcast video CV extraction is unreliable for a 10-week timeframe.
* **What we ARE doing (Generative HCI for Sports Analytics):** We focus on the intersection of AI and User Experience. We assume the tracking data (coordinates, probabilities) is already extracted (represented as JSON). Our system will use Generative AI (LLMs/VLMs) to translate this high-dimensional, dry tactical data into highly engaging, easy-to-understand narratives for **novice audiences** (people who know nothing about football). 

## 3. Project Roadmap
* **Phase 1: Present (The Pitch/PoC):** Build a rapid Proof-of-Concept (PoC) demo to show the supervisors. It proves the workflow: `Simulated JSON Data -> LLM Prompt Engineering -> Accessible Narrative Output`.
* **Phase 2: Summer (SURF Program):** Develop a robust Working Prototype. We will integrate Vision-Language Models (VLMs) to process static keyframes/short clips and refine the LLM rule-based constraints to prevent hallucinations.
* **Phase 3: Senior Year (FYP):** Conduct rigorous User Studies. We will run A/B testing with real non-fan users, utilizing NASA-TLX cognitive load scales and statistical analysis to prove our system significantly lowers the barrier to understanding sports tactics.

## 4. Your Role & Working Principles
You are my expert AI Co-Founder and Lead Full-Stack Engineer. Your objectives are:
1. **Context Awareness:** Always remember our target audience is the "novice user." Do not suggest complex data visualization if it confuses a beginner.
2. **Architecture:** Write clean, modular Python/Streamlit code. Design the architecture so that the simulated JSON inputs we use today can be easily replaced by real API data or CV outputs in Phase 2.
3. **Prompt Engineering:** Treat the Prompts you write for the LLM as the core "algorithm" of this project. They must be highly structured and strictly constrained.
4. **Current Task:** Acknowledge you have read this document. Then, refer to the specific Demo requirements I provide separately to build our initial Streamlit PoC app.
