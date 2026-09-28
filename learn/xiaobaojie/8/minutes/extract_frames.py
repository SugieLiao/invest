#!/usr/bin/env python3
"""Extract frames every 90 seconds from video using PyAV.
Uses stream.frames / stream.fps to compute duration (NOT stream.duration).
"""
import av
import os

VIDEO = "/Users/sugieliao/Documents/98视频课程提取池/08.20250831直播宏观框架课第八期货币政策汇率(1).mp4"
OUT_DIR = "/Users/sugieliao/WorkBuddy/invest/learn/xiaobaojie/8/assets/slides"
TIMESTAMP_FILE = "/Users/sugieliao/WorkBuddy/invest/learn/xiaobaojie/8/minutes/frame_timestamps.txt"

os.makedirs(OUT_DIR, exist_ok=True)

container = av.open(VIDEO)
stream = container.streams.video[0]

# Compute total duration from frames / fps (NOT stream.duration)
fps = float(stream.average_rate)
total_frames = stream.frames
total_duration = total_frames / fps
print(f"Video: {total_frames} frames, fps={fps:.3f}, total_duration={total_duration:.1f}s ({total_duration/60:.1f} min)")

# Target interval: 90 seconds
INTERVAL = 90.0
next_target = 0.0  # seconds
frame_num = 0
saved = []
slides = []

for frame in container.decode(video=0):
    # frame.time is in seconds
    t = float(frame.time)
    if t >= next_target:
        frame_num += 1
        idx = frame_num
        out_path = os.path.join(OUT_DIR, f"slide_{idx:02d}.jpeg")
        frame.to_image().save(out_path, quality=85)
        saved.append(out_path)
        slides.append((idx, t))
        print(f"  saved slide_{idx:02d}.jpeg at t={t:.1f}s ({t/60:.1f} min)")
        next_target += INTERVAL

# Check if last frame is close to end (within 90s), if not, extract last frame
if slides:
    last_t = slides[-1][1]
    if total_duration - last_t > 90:
        frame_num += 1
        idx = frame_num
        out_path = os.path.join(OUT_DIR, f"slide_{idx:02d}.jpeg")
        # seek to near end
        container.seek(int((total_duration - 2) * 1_000_000), stream=stream)  # microseconds
        last_frame = None
        for f in container.decode(video=0):
            last_frame = f
        if last_frame is not None:
            last_frame.to_image().save(out_path, quality=85)
            slides.append((idx, float(last_frame.time)))
            print(f"  [tail] saved slide_{idx:02d}.jpeg at t={float(last_frame.time):.1f}s")

container.close()

# Write timestamps file
with open(TIMESTAMP_FILE, 'w') as f:
    f.write(f"Video duration: {total_duration:.1f}s ({total_duration/60:.1f} min)\n")
    f.write(f"Total frames extracted: {len(slides)}\n")
    f.write("Format: slide_index\ttime_seconds\ttime_mm:ss\n")
    for idx, t in slides:
        mm = int(t // 60)
        ss = int(t % 60)
        f.write(f"slide_{idx:02d}\t{t:.1f}\t{mm:02d}:{ss:02d}\n")

print(f"\nDone. Extracted {len(slides)} slides to {OUT_DIR}")
print(f"Timestamps saved to {TIMESTAMP_FILE}")
print(f"Video duration: {total_duration/60:.1f} min")
