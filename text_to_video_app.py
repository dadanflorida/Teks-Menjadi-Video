#!/usr/bin/env python3
"""
Aplikasi Text-to-Video Natural
Mengubah teks menjadi video dengan narasi suara natural, dukungan bahasa Indonesia,
pilihan format (landscape, portrait, square), dan musik latar.
"""

import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
from pathlib import Path
from moviepy import (
    AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip
)
from moviepy.audio.fx import AudioLoop, MultiplyVolume
from PIL import Image, ImageDraw, ImageFont
import re

st.set_page_config(
    page_title="Text ke Video Natural | Bahasa Indonesia",
    page_icon="🎬",
    layout="wide"
)

# ==================== CSS ====================
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.3rem;
    }
    .sub-header {
        color: #555;
        margin-bottom: 1.5rem;
    }
    .stButton>button {
        background: linear-gradient(90deg, #6C63FF, #4A47A3);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #5a52e0, #3d3a8a);
    }
</style>
""", unsafe_allow_html=True)

# ==================== HELPER ====================
def split_into_sentences(text: str) -> list[str]:
    """Pisahkan teks menjadi kalimat-kalimat."""
    # Pola sederhana untuk bahasa Indonesia
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]

def create_background_image(width: int, height: int, color: tuple = (26, 26, 46)) -> Image.Image:
    """Buat background gradient sederhana."""
    img = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(img)
    # Gradient vertikal lembut
    for y in range(height):
        ratio = y / height
        r = int(color[0] + (40 - color[0]) * ratio)
        g = int(color[1] + (40 - color[1]) * ratio)
        b = int(color[2] + (80 - color[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return img

def wrap_text(text: str, font, max_width: int) -> list[str]:
    """Wrap teks agar muat di lebar tertentu."""
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = font.getbbox(test_line)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def create_text_image(
    text: str,
    width: int,
    height: int,
    bg_color: tuple = (26, 26, 46),
    text_color: tuple = (255, 255, 255),
    font_size: int = 42
) -> Image.Image:
    """Buat gambar dengan teks terpusat dan background."""
    img = create_background_image(width, height, bg_color)
    draw = ImageDraw.Draw(img)

    # Coba load font yang bagus
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    font = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    max_text_width = int(width * 0.85)
    lines = wrap_text(text, font, max_text_width)

    # Hitung tinggi total teks
    line_heights = []
    for line in lines:
        bbox = font.getbbox(line)
        line_heights.append(bbox[3] - bbox[1])
    total_text_height = sum(line_heights) + (len(lines) - 1) * 12

    y = (height - total_text_height) // 2

    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2
        # Shadow
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 180))
        draw.text((x, y), line, font=font, fill=text_color)
        y += line_heights[i] + 12

    return img

async def generate_speech(text: str, voice: str, output_path: str, rate: str = "+0%"):
    """Generate audio dengan edge-tts."""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)

def get_audio_duration(audio_path: str) -> float:
    """Ambil durasi audio."""
    with AudioFileClip(audio_path) as clip:
        return clip.duration

# ==================== UI ====================
st.markdown('<p class="main-header">🎬 Text ke Video Natural</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Ubah teks menjadi video dengan narasi suara natural • Dukungan penuh Bahasa Indonesia</p>',
    unsafe_allow_html=True
)

col1, col2 = st.columns([2, 1])

with col1:
    text_input = st.text_area(
        "Masukkan teks / naskah",
        height=220,
        placeholder="Contoh: Selamat datang di aplikasi text ke video. "
                    "Aplikasi ini mendukung bahasa Indonesia secara penuh. "
                    "Anda bisa memilih format video dan suara narator.",
        help="Teks akan dipecah menjadi beberapa scene berdasarkan kalimat."
    )

with col2:
    st.subheader("Pengaturan")

    format_option = st.selectbox(
        "Format Video",
        options=["Landscape (16:9)", "Portrait (9:16)", "Square (1:1)"],
        index=0
    )

    voice_option = st.selectbox(
        "Suara Narator",
        options=[
            "id-ID-GadisNeural (Perempuan)",
            "id-ID-ArdiNeural (Laki-laki)",
            "jv-ID-SitiNeural (Jawa - Perempuan)",
            "jv-ID-DimasNeural (Jawa - Laki-laki)",
            "su-ID-TutiNeural (Sunda - Perempuan)",
            "su-ID-JajangNeural (Sunda - Laki-laki)",
        ],
        index=0
    )

    speed = st.select_slider(
        "Kecepatan Bicara",
        options=["-20%", "-10%", "+0%", "+10%", "+20%"],
        value="+0%"
    )

    bg_style = st.selectbox(
        "Gaya Background",
        options=["Gelap (Default)", "Biru Laut", "Hijau Hutan", "Ungu Soft", "Abu Profesional"],
        index=0
    )

    st.markdown("---")
    st.subheader("Musik Latar")

    enable_music = st.checkbox("Aktifkan musik latar", value=False)

    music_file = None
    music_volume = 0.25
    if enable_music:
        music_file = st.file_uploader(
            "Upload file musik (MP3 / WAV / M4A)",
            type=["mp3", "wav", "m4a", "ogg"],
            help="Musik akan di-loop otomatis jika lebih pendek dari video."
        )
        music_volume = st.slider(
            "Volume musik (relatif terhadap narasi)",
            min_value=0.05,
            max_value=0.60,
            value=0.25,
            step=0.05,
            help="Disarankan 0.15–0.30 agar narasi tetap jelas."
        )

# Mapping format
format_map = {
    "Landscape (16:9)": (1280, 720),
    "Portrait (9:16)": (720, 1280),
    "Square (1:1)": (1080, 1080),
}
width, height = format_map[format_option]

# Mapping warna background
bg_colors = {
    "Gelap (Default)": (26, 26, 46),
    "Biru Laut": (15, 32, 64),
    "Hijau Hutan": (20, 40, 30),
    "Ungu Soft": (40, 25, 55),
    "Abu Profesional": (35, 35, 40),
}
bg_color = bg_colors[bg_style]

# Mapping voice
voice_map = {
    "id-ID-GadisNeural (Perempuan)": "id-ID-GadisNeural",
    "id-ID-ArdiNeural (Laki-laki)": "id-ID-ArdiNeural",
    "jv-ID-SitiNeural (Jawa - Perempuan)": "jv-ID-SitiNeural",
    "jv-ID-DimasNeural (Jawa - Laki-laki)": "jv-ID-DimasNeural",
    "su-ID-TutiNeural (Sunda - Perempuan)": "su-ID-TutiNeural",
    "su-ID-JajangNeural (Sunda - Laki-laki)": "su-ID-JajangNeural",
}
selected_voice = voice_map[voice_option]

st.markdown("---")

generate_btn = st.button("🚀 Buat Video", type="primary", use_container_width=True)

if generate_btn:
    if not text_input or not text_input.strip():
        st.error("Silakan masukkan teks terlebih dahulu.")
    else:
        with st.spinner("Sedang membuat video... Mohon tunggu sebentar."):
            try:
                sentences = split_into_sentences(text_input)
                if not sentences:
                    sentences = [text_input.strip()]

                # Temporary directory
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_path = Path(tmpdir)
                    clips = []
                    audio_paths = []

                    progress = st.progress(0)
                    status = st.empty()

                    for i, sentence in enumerate(sentences):
                        status.text(f"Memproses scene {i+1}/{len(sentences)}: {sentence[:50]}...")
                        progress.progress((i) / len(sentences))

                        # Generate audio per kalimat
                        audio_file = tmp_path / f"audio_{i}.mp3"
                        asyncio.run(
                            generate_speech(sentence, selected_voice, str(audio_file), rate=speed)
                        )
                        audio_paths.append(audio_file)

                        duration = get_audio_duration(str(audio_file))
                        # Minimal 2 detik, maksimal sesuai audio + sedikit padding
                        duration = max(duration + 0.3, 2.0)

                        # Buat gambar teks
                        img = create_text_image(
                            sentence,
                            width,
                            height,
                            bg_color=bg_color,
                            font_size=48 if width >= 1080 else 36
                        )
                        img_path = tmp_path / f"img_{i}.png"
                        img.save(img_path)

                        # Buat clip
                        img_clip = ImageClip(str(img_path)).with_duration(duration)
                        audio_clip = AudioFileClip(str(audio_file))
                        video_clip = img_clip.with_audio(audio_clip)
                        clips.append(video_clip)

                    progress.progress(0.85)
                    status.text("Menggabungkan semua scene...")

                    final_clip = concatenate_videoclips(clips, method="compose")

                    # ===== Musik Latar =====
                    music_clip = None
                    if enable_music and music_file is not None:
                        status.text("Menambahkan musik latar...")
                        progress.progress(0.90)

                        # Simpan file musik upload
                        music_ext = Path(music_file.name).suffix.lower() or ".mp3"
                        music_path = tmp_path / f"bg_music{music_ext}"
                        with open(music_path, "wb") as f:
                            f.write(music_file.getbuffer())

                        original_music = AudioFileClip(str(music_path))
                        video_duration = final_clip.duration

                        # Loop musik jika lebih pendek dari video
                        if original_music.duration < video_duration:
                            music_clip = original_music.with_effects([
                                AudioLoop(duration=video_duration)
                            ])
                        else:
                            # Potong musik sesuai durasi video
                            music_clip = original_music.subclipped(0, video_duration)

                        # Turunkan volume musik
                        music_clip = music_clip.with_effects([
                            MultiplyVolume(music_volume)
                        ])

                        # Gabungkan audio narasi + musik
                        original_audio = final_clip.audio
                        mixed_audio = CompositeAudioClip([original_audio, music_clip])
                        final_clip = final_clip.with_audio(mixed_audio)

                    progress.progress(0.95)
                    status.text("Merender video final...")

                    output_path = tmp_path / "output_video.mp4"
                    final_clip.write_videofile(
                        str(output_path),
                        fps=24,
                        codec="libx264",
                        audio_codec="aac",
                        preset="medium",
                        threads=2,
                        logger=None
                    )

                    # Baca hasil
                    with open(output_path, "rb") as f:
                        video_bytes = f.read()

                    progress.progress(1.0)
                    status.text("Selesai!")

                    st.success("✅ Video berhasil dibuat!")
                    st.video(video_bytes)

                    st.download_button(
                        label="⬇️ Unduh Video MP4",
                        data=video_bytes,
                        file_name="text_to_video.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )

                    # Info
                    music_info = " • Musik latar aktif" if (enable_music and music_file is not None) else ""
                    st.info(
                        f"**Detail:** {len(sentences)} scene • "
                        f"{width}x{height} • "
                        f"Durasi ±{final_clip.duration:.1f} detik • "
                        f"Suara: {voice_option}{music_info}"
                    )

                    # Cleanup clips
                    final_clip.close()
                    for c in clips:
                        c.close()
                    if music_clip is not None:
                        try:
                            music_clip.close()
                        except Exception:
                            pass

            except Exception as e:
                st.error(f"Terjadi kesalahan: {str(e)}")
                st.exception(e)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888; font-size: 0.9rem;">
        Dibuat dengan ❤️ • Edge-TTS (Microsoft Neural Voices) + MoviePy<br>
        Mendukung Bahasa Indonesia, Jawa, dan Sunda
    </div>
    """,
    unsafe_allow_html=True
)
