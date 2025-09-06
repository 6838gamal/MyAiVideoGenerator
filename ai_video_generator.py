# ai_video_generator.py
import yaml
from pathlib import Path
from google import genai
from diffusers import StableDiffusionPipeline
import torch
from TTS.api import TTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from animate_diff.animate import AnimateDiff

# ---------------------------
# الإعدادات
# ---------------------------
config = {
    "video": {"width": 1280, "height": 720, "fps": 30},
    "tts": {"voice": "alloy"},
    "paths": {
        "images_dir": "data/images",
        "animated_dir": "data/images_animated",
        "audio_dir": "data/audio",
        "video_dir": "data/video"
    }
}

# إنشاء المجلدات إذا لم تكن موجودة
for path in config['paths'].values():
    Path(path).mkdir(parents=True, exist_ok=True)

# ---------------------------
# 1️⃣ توليد النصوص باستخدام Gemini
# ---------------------------
def generate_script(prompt):
    client = genai.Client()  # تأكد من ضبط مفتاح API في البيئة
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text.strip()

# ---------------------------
# 2️⃣ توليد الصور
# ---------------------------
def generate_image(prompt, output_path, model_name="runwayml/stable-diffusion-v1-5"):
    pipe = StableDiffusionPipeline.from_pretrained(model_name, torch_dtype=torch.float16)
    pipe = pipe.to("cuda")
    image = pipe(prompt).images[0]
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path

# ---------------------------
# 3️⃣ تحريك الصور
# ---------------------------
def animate_image(input_image, output_image, motion_strength=0.5, steps=20):
    Path(output_image).parent.mkdir(parents=True, exist_ok=True)
    animator = AnimateDiff(model_name="animate-diff/v1")
    animator.animate(
        input_image=input_image,
        output_path=output_image,
        motion_strength=motion_strength,
        steps=steps
    )
    return output_image

# ---------------------------
# 4️⃣ تحويل النص إلى صوت
# ---------------------------
def text_to_speech(text, output_path, voice="alloy"):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False, gpu=True)
    tts.tts_to_file(text=text, speaker=voice, file_path=output_path)
    return output_path

# ---------------------------
# 5️⃣ دمج الصور مع الصوت لإنشاء الفيديو
# ---------------------------
def create_video(image_paths, audio_path, output_path, fps=30):
    clips = []
    audio_clip = AudioFileClip(audio_path)
    duration_per_image = audio_clip.duration / len(image_paths)
    for img_path in image_paths:
        clip = ImageClip(img_path).set_duration(duration_per_image)
        clips.append(clip)
    video = concatenate_videoclips(clips, method="compose")
    video = video.set_audio(audio_clip)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    video.write_videofile(output_path, fps=fps)
    return output_path

# ---------------------------
# البرنامج الرئيسي
# ---------------------------
if __name__ == "__main__":
    prompt = input("أدخل البرومبت للفيديو: ")

    # توليد النص
    script = generate_script(prompt)
    print("✅ تم إنشاء النص")

    # توليد الصوت
    audio_path = f"{config['paths']['audio_dir']}/narration.wav"
    text_to_speech(script, audio_path, voice=config['tts']['voice'])
    print("✅ تم إنشاء الصوت")

    # توليد الصور وتحريكها لكل جملة
    sentences = [s for s in script.split(". ") if s]
    animated_paths = []
    for i, sentence in enumerate(sentences):
        img_path = f"{config['paths']['images_dir']}/image_{i+1}.png"
        anim_path = f"{config['paths']['animated_dir']}/image_{i+1}_anim.gif"
        generate_image(sentence, img_path)
        animate_image(img_path, anim_path)
        animated_paths.append(anim_path)
    print("✅ تم إنشاء الصور المتحركة")

    # دمج الصور المتحركة مع الصوت في الفيديو النهائي
    video_path = f"{config['paths']['video_dir']}/final_video.mp4"
    create_video(animated_paths, audio_path, video_path, fps=config['video']['fps'])
    print(f"🎬 الفيديو النهائي تم إنشاؤه: {video_path}")
