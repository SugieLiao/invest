#!/usr/bin/env python3
"""
视频抽帧工具 — 严格按 stream.frames / fps 计算时长，顺序解码每90秒一帧。
用法: python3 extract_frames.py <video_path> <output_dir> [interval_seconds]
"""
import sys
import os
import av

def extract_frames(video_path, output_dir, interval=90):
    os.makedirs(output_dir, exist_ok=True)
    container = av.open(video_path)
    stream = container.streams.video[0]

    # ⚠️ 必须用 frames / fps 计算时长，禁止用 stream.duration
    total_frames = stream.frames
    fps = float(stream.average_rate)
    duration_sec = total_frames / fps
    print(f"[INFO] total_frames={total_frames}, fps={fps:.3f}, duration={duration_sec:.1f}s ({duration_sec/60:.1f}min)")

    target_times = []
    t = 0
    while t < duration_sec:
        target_times.append(t)
        t += interval
    # 确保最后一帧接近结尾
    if target_times[-1] < duration_sec - interval * 0.5:
        target_times.append(duration_sec - 1)

    print(f"[INFO] extracting {len(target_times)} frames at {interval}s intervals")

    frame_idx = 0
    target_idx = 0
    saved = 0
    last_pts = None

    for frame in container.decode(stream):
        if target_idx >= len(target_times):
            break
        current_time = frame.pts * float(stream.time_base)
        last_pts = current_time

        if current_time >= target_times[target_idx]:
            img = frame.to_image()
            # 文件名: frame_序号_时间秒.jpg
            fname = f"frame_{saved:04d}_{int(current_time):06d}.jpg"
            fpath = os.path.join(output_dir, fname)
            img.save(fpath, "JPEG", quality=85)
            saved += 1
            target_idx += 1
            if saved % 10 == 0:
                print(f"  [PROGRESS] {saved}/{len(target_times)} frames, t={current_time:.0f}s")

        frame_idx += 1

    container.close()

    # ⚠️ 验证最后一帧时间戳接近视频总时长
    if last_pts is not None:
        gap = duration_sec - last_pts
        print(f"[VERIFY] last_frame_ts={last_pts:.1f}s, duration={duration_sec:.1f}s, gap={gap:.1f}s")
        if gap > interval * 2:
            print(f"[WARNING] 最后一帧与视频末尾差距过大({gap:.0f}s)，可能抽帧不完整！")
        else:
            print(f"[OK] 最后一帧时间戳验证通过")
    print(f"[DONE] saved {saved} frames to {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 extract_frames.py <video_path> <output_dir> [interval]")
        sys.exit(1)
    video = sys.argv[1]
    outdir = sys.argv[2]
    interval = int(sys.argv[3]) if len(sys.argv) > 3 else 90
    extract_frames(video, outdir, interval)
