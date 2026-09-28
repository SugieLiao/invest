#!/usr/bin/env python3
"""Extract MP3 audio from video using PyAV."""
import av
import os

VIDEO = "/Users/sugieliao/Documents/98视频课程提取池/08.20250831直播宏观框架课第八期货币政策汇率(1).mp4"
OUT = "/Users/sugieliao/WorkBuddy/invest/learn/xiaobaojie/8/minutes/audio.mp3"

os.makedirs(os.path.dirname(OUT), exist_ok=True)

container = av.open(VIDEO)
audio_stream = next(s for s in container.streams if s.type == 'audio')
print(f"Audio stream: channels={audio_stream.channels}, rate={audio_stream.rate}, codec={audio_stream.codec_context.name}")

output = av.open(OUT, 'w')
out_stream = output.add_stream('libmp3lame', rate=44100)

resampler = av.AudioResampler(format='s16', layout='stereo', rate=44100)

frame_count = 0
for frame in container.decode(audio=0):
    resampled = resampler.resample(frame)
    for rf in resampled:
        for packet in out_stream.encode(rf):
            output.mux(packet)
    frame_count += 1
    if frame_count % 10000 == 0:
        print(f"  decoded {frame_count} frames...")

# flush resampler
for rf in resampler.resample(None):
    for packet in out_stream.encode(rf):
        output.mux(packet)

# flush encoder
for packet in out_stream.encode(None):
    output.mux(packet)

output.close()
container.close()

size = os.path.getsize(OUT)
print(f"Done. Output: {OUT}")
print(f"Size: {size/1024/1024:.1f} MB, frames: {frame_count}")
