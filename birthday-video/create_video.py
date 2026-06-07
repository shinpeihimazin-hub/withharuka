#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, glob, random
import numpy as np
import librosa
from scipy.ndimage import uniform_filter1d
from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip,
    concatenate_videoclips, CompositeVideoClip
)
from PIL import Image

# ========== CONFIG（ここだけ変える） ==========
PHOTOS_DIR      = "photos"              # 写真フォルダ
AUDIO_FILE      = "feel_special.mp3"   # 音源ファイル
FINAL_CLIP_FILE = "final_video.mp4"    # ラストの動画（2人で笑ってるやつ）
OUTPUT_FILE     = "birthday.mp4"       # 出力ファイル名

AUDIO_START_SEC        = 52    # Feel Special の何秒目から使うか（52 = サビ直前）
PHOTO_SECTION_DURATION = 50    # 写真パートの秒数
FINAL_CLIP_DURATION    = 10    # ラスト動画を何秒使うか（長ければ自動トリム）

VIDEO_W = 1920
VIDEO_H = 1080
FPS     = 30

SLOW_DURATION = 4.0   # Aメロ：1枚あたりの表示秒数
FAST_DURATION = 0.5   # サビ  ：1枚あたりの表示秒数
CROSSFADE_DUR = 0.4   # スロー写真のクロスフェード秒数
# =============================================


def load_photos(folder, max_count=100):
    exts = ["*.jpg", "*.jpeg", "*.JPG", "*.JPEG", "*.png", "*.PNG"]
    files = []
    for e in exts:
        files.extend(glob.glob(os.path.join(folder, e)))
    if not files:
        print(f"ERROR: {folder} フォルダに画像が見つかりません")
        sys.exit(1)
    random.shuffle(files)
    chosen = files[:max_count]
    print(f"  {len(chosen)} 枚の写真を使用します")
    return chosen


def get_energy_curve(audio_path, start, duration):
    print("  音楽を解析中...")
    y, sr = librosa.load(audio_path, offset=start, duration=duration, sr=22050)
    hop = 512
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    rms_norm = (rms - rms.min()) / (rms.max() - rms.min() + 1e-8)
    rms_smooth = uniform_filter1d(rms_norm, size=30)
    return times, rms_smooth


def build_schedule(times, energy, total_dur, threshold=0.55):
    schedule = []
    t = 0.0
    while t < total_dur - 0.1:
        idx = min(int(np.searchsorted(times, t)), len(energy) - 1)
        is_fast = bool(energy[idx] > threshold)
        dur = FAST_DURATION if is_fast else SLOW_DURATION
        dur = min(dur, total_dur - t)
        if dur < 0.1:
            break
        schedule.append((dur, is_fast))
        t += dur
    return schedule


def fit_image(path, w, h):
    img = Image.open(path).convert("RGB")
    iw, ih = img.size
    ratio = w / h
    if iw / ih > ratio:
        new_w = int(ih * ratio)
        img = img.crop(((iw - new_w) // 2, 0, (iw - new_w) // 2 + new_w, ih))
    else:
        new_h = int(iw / ratio)
        img = img.crop((0, (ih - new_h) // 2, iw, (ih - new_h) // 2 + new_h))
    return np.array(img.resize((w, h), Image.LANCZOS))


def make_slow_clip(path, duration, zoom_in):
    arr = fit_image(path, VIDEO_W, VIDEO_H)
    clip = ImageClip(arr).set_duration(duration)
    zoom = 0.08
    if zoom_in:
        clip = clip.resize(lambda t: 1 + zoom * (t / duration))
    else:
        clip = clip.resize(lambda t: 1 + zoom * (1 - t / duration))
    clip = clip.set_position("center")
    return CompositeVideoClip([clip], size=(VIDEO_W, VIDEO_H)).set_duration(duration)


def make_fast_clip(path, duration):
    arr = fit_image(path, VIDEO_W, VIDEO_H)
    return ImageClip(arr).set_duration(duration)


def main():
    print("=== Birthday Video Creator ===\n")

    print("[1/5] 写真を読み込み中...")
    photos = load_photos(PHOTOS_DIR)

    print("[2/5] 音楽を分析中...")
    times, energy = get_energy_curve(AUDIO_FILE, AUDIO_START_SEC, PHOTO_SECTION_DURATION)

    print("[3/5] 緩急スケジュールを計算中...")
    schedule = build_schedule(times, energy, PHOTO_SECTION_DURATION)
    n_slow = sum(1 for _, fast in schedule if not fast)
    n_fast = sum(1 for _, fast in schedule if fast)
    print(f"  Aメロ（ゆっくり）: 約 {n_slow} 枚")
    print(f"  サビ（速い）    : 約 {n_fast} 枚")

    photos = photos[:len(schedule)]
    if len(photos) < len(schedule):
        schedule = schedule[:len(photos)]

    print("[4/5] 写真クリップを作成中（数分かかります）...")
    clips = []
    zoom_in = True
    for i, ((dur, is_fast), photo) in enumerate(zip(schedule, photos)):
        print(f"  {i + 1}/{len(schedule)}  {os.path.basename(photo)}", end="\r")
        try:
            if is_fast:
                clip = make_fast_clip(photo, dur)
            else:
                clip = make_slow_clip(photo, dur, zoom_in)
                zoom_in = not zoom_in
            clips.append(clip)
        except Exception as e:
            print(f"\n  スキップ: {os.path.basename(photo)} ({e})")
    print()

    faded = []
    for i, clip in enumerate(clips):
        if i > 0 and not is_fast and clip.duration > 1.0:
            clip = clip.crossfadein(CROSSFADE_DUR)
        faded.append(clip)

    photo_part = concatenate_videoclips(faded, method="compose", padding=-CROSSFADE_DUR)

    print("[5/5] ラスト動画を追加中...")
    final_raw = VideoFileClip(FINAL_CLIP_FILE)
    use_dur = min(FINAL_CLIP_DURATION, final_raw.duration)
    final_clip = (final_raw
                  .subclip(0, use_dur)
                  .resize((VIDEO_W, VIDEO_H))
                  .fadein(1.5))

    full_video = concatenate_videoclips([photo_part, final_clip], method="compose")

    audio_end = AUDIO_START_SEC + full_video.duration
    audio = (AudioFileClip(AUDIO_FILE)
             .subclip(AUDIO_START_SEC, audio_end)
             .audio_fadeout(2.5))
    full_video = full_video.set_audio(audio)

    print(f"\n書き出し中: {OUTPUT_FILE}  （一番時間がかかります）")
    full_video.write_videofile(
        OUTPUT_FILE,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
        ffmpeg_params=["-crf", "18"],
    )
    print(f"\n完成！ → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
