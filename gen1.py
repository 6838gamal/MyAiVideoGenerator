import streamlit as st
from gtts import gTTS
from pathlib import Path
import textwrap, subprocess
from PIL import Image, ImageDraw, ImageFont

# -------------------------------
# إعدادات عامة
# -------------------------------
OUT = Path("output")
OUT.mkdir(exist_ok=True)

WIDTH, HEIGHT = 1280, 720

def make_slides(text: str):
    """إنشاء صور شرائح من النص"""
    shots = textwrap.wrap(text, width=50)
    slides = []
    for i, shot in enumerate(shots, 1):
        img = Image.new("RGB", (WIDTH, HEIGHT), color=(20, 20, 30))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except:
            font = ImageFont.load_default()
        w, h = draw.textsize(shot, font=font)
        draw.text(((WIDTH-w)//2, (HEIGHT-h)//2), shot, fill=(230,230,235), font=font)
        path = OUT / f"slide_{i}.jpg"
        img.save(path)
        slides.append(path)
    return slides

def make_voice(text: str, lang: str = "ar"):
    """تحويل النص إلى كلام"""
    out = OUT / "voice.mp3"
    gTTS(text=text, lang=lang).save(str(out))
    return out

def build_video(slides, audio_path):
    """دمج الصور مع الصوت باستخدام ffmpeg"""
    # إنشاء ملف نصي لشرائح ffmpeg
    slides_txt = OUT / "slides.txt"
    with open(slides_txt, "w", encoding="utf-8") as f:
        for slide in slides:
            f.write(f"file '{slide.resolve()}'\n")
            f.write("duration 3\n")  # مدة كل شريحة

    # لتفادي مشكلة المدة في آخر صورة
    with open(slides_txt, "a", encoding="utf-8") as f:
        f.write(f"file '{slides[-1].resolve()}'\n")

    video_path = OUT / "final.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(slides_txt),
        "-i", str(audio_path),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        str(video_path)
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return video_path

# -------------------------------
# واجهة Streamlit
# -------------------------------
st.title("🎬 صانع الفيديو الجاهز للتنزيل")

prompt = st.text_area("✍️ النص", "فوائد النظام اليومي")
lang = st.selectbox("🌐 اللغة", ["ar", "en"], index=0)

if st.button("🚀 أنشئ الفيديو"):
    if not prompt.strip():
        st.warning("اكتب نص أولاً")
    else:
        with st.spinner("جارٍ توليد الفيديو..."):
            # 1. الشرائح
            slides = make_slides(prompt)

            # 2. الصوت
            audio = make_voice(prompt, lang=lang)

            # 3. الفيديو
            video = build_video(slides, audio)

        st.success("✅ الفيديو جاهز")
        st.video(str(video))

        with open(video, "rb") as f:
            st.download_button(
                "⬇️ تحميل الفيديو",
                f,
                file_name="final.mp4",
                mime="video/mp4"
            )
