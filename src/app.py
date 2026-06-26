"""
SURF-2026-0154 Demo v2 — 教授汇报版

展示16个2026世界杯角球的完整数据集 + AI科普解说管线。
"""

import streamlit as st
import json, os
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUTPUTS = ROOT / "outputs"
DATA = ROOT / "src" / "data"
VIDEO_DIR = ROOT / "data" / "videos"
AUDIO_DIR = OUTPUTS / "audio"
VIDEO_OUT = OUTPUTS / "videos"
TEXTS_DIR = OUTPUTS / "texts"

st.set_page_config(page_title="SURF-2026 · AI Tactical Translator", page_icon="⚽", layout="wide")

st.markdown("""
<style>
.stButton>button{font-size:1rem;font-weight:600;padding:.5rem 2rem;border-radius:8px}
.card{border:1px solid #e0e0e0;border-radius:10px;padding:1rem 1.5rem;margin:.5rem 0}
.video-card{border:2px solid #4a90d9;border-radius:10px;padding:1rem;margin:.5rem 0;background:#f8fbff}
.audio-card{border:1px solid #e8e8e8;border-radius:10px;padding:1rem;margin:.5rem 0;background:#fafafa}
.metric{text-align:center;padding:0.5rem}
.metric .num{font-size:2rem;font-weight:800;color:#4a90d9}
.metric .label{font-size:0.8rem;color:#666}
</style>
""", unsafe_allow_html=True)


def load_data():
    with open(DATA / "corner_kicks_2026.json", "r", encoding="utf-8") as f:
        return json.load(f)


def find_video(eid):
    for f in VIDEO_DIR.glob(f"{eid}*.mp4"):
        return str(f)
    return None


def find_story(eid):
    for f in VIDEO_OUT.glob(f"{eid}*_corner_story.mp4"):
        return str(f)
    return None


def find_audio(eid):
    for f in AUDIO_DIR.glob(f"{eid}*.mp3"):
        return str(f)
    return None


def find_narration_text(eid):
    for f in TEXTS_DIR.glob(f"{eid}*_narration.txt"):
        with open(f, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        return "".join(lines[4:]).strip() if len(lines) > 4 else ""
    return ""


def main():
    dataset = load_data()
    entries = dataset["entries"]

    # ── Header ──
    st.markdown("""
    <div style="text-align:center;padding:1rem 0">
        <h1 style="margin:0;font-size:2rem">⚽ AI 角球战术翻译官</h1>
        <p style="color:#666;margin:0.3rem 0 0 0">
            SURF-2026-0154 · Generative HCI for Sports Analytics · Demo v2
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── 关键指标 ──
    cols = st.columns(5)
    with cols[0]: st.markdown('<div class="metric"><div class="num">16</div><div class="label">角球条目</div></div>', unsafe_allow_html=True)
    with cols[1]: st.markdown('<div class="metric"><div class="num">8</div><div class="label">带原视频</div></div>', unsafe_allow_html=True)
    with cols[2]: st.markdown('<div class="metric"><div class="num">6</div><div class="label">AI解说视频</div></div>', unsafe_allow_html=True)
    with cols[3]: st.markdown('<div class="metric"><div class="num">16</div><div class="label">AI解说音频</div></div>', unsafe_allow_html=True)
    with cols[4]: st.markdown('<div class="metric"><div class="num">2.0</div><div class="label">数据集版本</div></div>', unsafe_allow_html=True)

    st.divider()

    # ── 数据集表格 ──
    st.markdown("## 📊 2026世界杯角球数据集")

    rows = []
    for e in entries:
        vid = find_video(e["id"])
        story = find_story(e["id"])
        audio = find_audio(e["id"])
        text = find_narration_text(e["id"])

        has_vid = "📹" if vid else "—"
        has_story = "📺" if story else "—"
        has_audio = "🎙️" if audio else "—"
        has_text = "📝" if text else "—"

        rows.append({
            "ID": e["id"].replace("wc2026-corner-", "#"),
            "比赛": e["match"],
            "进球者": e["goal_scorer"],
            "时间": e["minute"] + "'",
            "原视频": has_vid,
            "AI解说": has_story,
            "音频": has_audio,
            "文本": has_text,
            "_eid": e["id"],
        })

    # 用 st.dataframe 排序展示
    st.dataframe(
        rows,
        column_config={
            "ID": st.column_config.TextColumn(width="small"),
            "比赛": st.column_config.TextColumn(width="medium"),
            "进球者": st.column_config.TextColumn(width="medium"),
            "时间": st.column_config.TextColumn(width="small"),
            "原视频": st.column_config.TextColumn(width="small"),
            "AI解说": st.column_config.TextColumn(width="small"),
            "音频": st.column_config.TextColumn(width="small"),
            "文本": st.column_config.TextColumn(width="small"),
        },
        hide_index=True,
        use_container_width=True,
    )

    st.divider()

    # ── 详细查看 ──
    st.markdown("## 🔍 查看详情")

    selected = st.selectbox(
        "选择一个角球",
        [f"{e['id'].replace('wc2026-corner-','#')} — {e['match']} — {e['goal_scorer']} ({e['minute']}')" for e in entries],
        label_visibility="collapsed",
    )

    eid_num = selected.split(" — ")[0].replace("#", "")
    eid = f"wc2026-corner-{eid_num}"
    entry = next((e for e in entries if e["id"] == eid), None)

    if entry:
        c1, c2 = st.columns([1, 1], gap="large")

        with c1:
            st.markdown("### 📹 原视频 + AI解说")
            story = find_story(eid)
            if story:
                st.video(story)
                st.caption(f"AI解说视频 · {entry['match']} · {entry['goal_scorer']}")
            else:
                vid = find_video(eid)
                if vid:
                    st.video(vid)
                    st.caption(f"原视频 (待处理)")
                else:
                    st.info("该条目无视频源")

                audio = find_audio(eid)
                if audio:
                    st.markdown("### 🎙️ AI解说音频")
                    st.audio(audio)

        with c2:
            st.markdown("### 📝 AI解说文本")
            text = find_narration_text(eid)
            if text:
                st.markdown(f'<div class="card" style="line-height:1.9;font-size:0.95rem">{text}</div>', unsafe_allow_html=True)

            st.markdown("### 📋 战术数据")
            st.json({
                "match": entry["match"],
                "group": entry.get("group", ""),
                "date": entry.get("date", ""),
                "minute": entry["minute"],
                "score": entry.get("score_at_time", ""),
                "corner_type": entry.get("corner_type", ""),
                "result": entry.get("result", ""),
                "tactical_note": entry.get("tactical_note", ""),
            })

    st.divider()
    st.markdown("""
    <div style="text-align:center;color:#999;font-size:0.75rem">
        SURF-2026-0154 · Generative HCI for Sports Analytics · Demo v2<br>
        Ting-Yu (IMIS, XJTLU) · Dr. Nanlin Jin & Dr. Thomas Selig · Summer 2026
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
