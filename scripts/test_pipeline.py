"""快速测试管线：视频 → Gemini → DeepSeek → TTS"""
import sys, json, time
sys.path.insert(0, "src")

from google import genai
from google.genai import types
from config import GEMINI_API_KEY
from vlm_client import VLM_PROMPT

video_path = "data/videos/wc2026-corner-007-morocco-haiti.mp4"
print(f"Video: {video_path}")

# Step 1: Upload to Gemini
client = genai.Client(api_key=GEMINI_API_KEY)
vf = client.files.upload(file=video_path)
print(f"Uploaded: {vf.name}")

while vf.state == types.FileState.PROCESSING:
    time.sleep(2)
    vf = client.files.get(name=vf.name)
print(f"State: {vf.state}")

# Step 2: VLM analysis (try gemini-2.5-flash)
print("Calling VLM...")
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        types.Content(role="user", parts=[
            types.Part.from_uri(file_uri=vf.uri, mime_type="video/mp4"),
            types.Part(text=VLM_PROMPT)
        ])
    ],
    config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=2048)
)

raw = response.text.strip()
# Clean markdown code block if present
if raw.startswith("```"):
    parts = raw.split("```")
    raw = parts[1]
    if raw.startswith("json"):
        raw = raw[4:]
data = json.loads(raw)
print("VLM JSON extracted!")
print(json.dumps(data, indent=2, ensure_ascii=False)[:1200])
print("...")
print(f"\nVLM complete. JSON keys: {list(data.keys())}")
