import os
from pathlib import Path
import streamlit as st
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import textwrap, random, re

# --------------------------------------
# إعدادات عامة
# --------------------------------------
DEFAULT_WIDTH, DEFAULT_HEIGHT = 1280, 720
DEFAULT_FPS = 24

OUT_IMAGES = Path("data/images")
OUT_AUDIO = Path("data/audio")
OUT_VIDEO = Path("data/video")
for p in (OUT_IMAGES, OUT_AUDIO, OUT_VIDEO):
    p.mkdir(parents=True, exist_ok=True)

# --------------------------------------
# أدوات مساعدة
# --------------------------------------
def safe_filename(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE).strip().lower()
    s = re.sub(r"[\s-]+", "_", s)
    return s or "item"

def split_script_into_shots(script: str, max_chars=140):
    import re
    parts = re.split(r"(?<=[.!؟…])\s+", script.strip())
    shots, buf = [], ""
    for p in parts:
        if not p.strip():
            continue
        if len(buf) + len(p) <= max_chars:
            buf = (buf + " " + p).strip() if buf else p.strip()
        else:
            if buf:
                shots.append(buf)
            buf = p.strip()
    if buf:
        shots.append(buf)
    return shots

def draw_fallback_image(text: str, out_path: Path, size=(DEFAULT_WIDTH, DEFAULT_HEIGHT)):
    img = Image.new("RGB", size, (18, 18, 22))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 42)
    except:
        font = ImageFont.load_default()
    wrapped = textwrap.fill(text, width=40)
    w, h = draw.multiline_textsize(wrapped, font=font)
    x = (size[0] - w) // 2
    y = (size[1] - h) // 2
    draw.multiline_text((x, y), wrapped, font=font, fill=(230, 230, 235), align="center")
    img.save(out_path, "JPEG", quality=92)

def generate_images_for_shots(shots):
    paths = []
    for i, s in enumerate(shots, start=1):
        name = safe_filename(s)[:50] or f"shot_{i}"
        out = OUT_IMAGES / f"{i:02d}_{name}.jpg"
        if not out.exists():
            draw_fallback_image(s, out)
        paths.append(out)
    return paths

def synthesize_speech_gtts(text: str, out_path: Path, lang: str = "ar") -> Path:
    tts = gTTS(text=text, lang=lang)
    tts.save(str(out_path))
    return out_path

def ensure_size_fit(img_clip: ImageClip, target_size):
    tw, th = target_size
    iw, ih = img_clip.size
    scale = max(tw/iw, th/ih)
    return img_clip.resize(scale).crop(x_center=iw/2, y_center=ih/2, width=tw, height=th)

def ken_burns_clip(img_path: Path, duration: float, size=(DEFAULT_WIDTH, DEFAULT_HEIGHT)) -> ImageClip:
    base = ImageClip(str(img_path))
    base = ensure_size_fit(base, size)
    start_zoom, end_zoom = 1.0, 1.05
    dx, dy = random.choice([(-40, 20), (40, -20), (30, 30), (-30, -30)])
    def zoom(t): return start_zoom + (end_zoom - start_zoom) * (t/duration if duration>0 else 1)
    def pos(t): return (dx*(t/duration), dy*(t/duration))
    return base.fx(lambda clip: clip.resize(lambda t: zoom(t)).set_position(lambda t: pos(t))).set_duration(duration)

def build_video_from_assets(image_paths, audio_path, out_path, fps=DEFAULT_FPS, size=(DEFAULT_WIDTH, DEFAULT_HEIGHT)) -> Path:
    audio = AudioFileClip(str(audio_path))
    total = max(audio.duration, 2.0)
    per = total / len(image_paths)
    clips = [ken_burns_clip(p, per, size=size) for p in image_paths]
    video = concatenate_videoclips(clips, method="compose").set_audio(audio)
    video.write_videofile(str(out_path), fps=fps, codec="libx264", audio_codec="aac")
    return out_path

# --------------------------------------
# Streamlit واجهة
# --------------------------------------
st.set_page_config(page_title="🎬 صانع الفيديو الخفيف", layout="centered")

st.title("🎬 صانع الفيديو الخفيف")
st.write("اكتب برومبت هنا وسيُنشأ لك فيديو (نص + صوت + صور متحركة بسيطة).")

prompt = st.text_area("✍️ البرومبت", "فوائد التنظيم اليومي")
lang = st.selectbox("🌐 لغة الصوت", ["ar", "en"], index=0)

if st.button("🚀 أنشئ الفيديو"):
    if not prompt.strip():
        st.warning("الرجاء إدخال برومبت أولاً.")
    else:
        with st.spinner("جاري إنشاء الفيديو..."):
            # 1) النص (هنا نستخدم البرومبت مباشرة كسيناريو)
            script = prompt  

            # 2) تقسيم النص إلى لقطات
            shots = split_script_into_shots(script)

            # 3) صور (fallback نصية)
            img_paths = generate_images_for_shots(shots)

            # 4) صوت
            audio_path = OUT_AUDIO / "voice.mp3"
            synthesize_speech_gtts(script, audio_path, lang=lang)

            # 5) فيديو
            video_path = OUT_VIDEO / "final_video.mp4"
            build_video_from_assets(img_paths, audio_path, video_path)

        st.success("✅ تم إنشاء الفيديو!")
        st.video(str(video_path))

        # زر تحميل
        with open(video_path, "rb") as f:
            st.download_button(
                label="⬇️ تحميل الفيديو",
                data=f,
                file_name="final_video.mp4",
                mime="video/mp4"
            )
