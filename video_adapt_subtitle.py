# encoding=utf-8
import argparse
import asyncio
import time
from datetime import datetime
from moviepy.editor import *
import numpy as np
from moviepy.audio.AudioClip import AudioArrayClip
from pydub import AudioSegment
from pydub.silence import split_on_silence
from utils import tts, md5_encrypt
from tqdm import tqdm
from functools import reduce

parser = argparse.ArgumentParser(
    prog='README.md',
    description="根据字幕文件生成语音，生成的语音通常与视频无法对上，该程序可以调整视频速度，使视频与字幕对应起来",
    epilog='Text at the bottom of help'
)


def total_seconds(dt: datetime) -> float:
    """
    计算dt的总秒数，不考虑年月日
    :param dt: 要计算的datetime对象
    :return: 总秒数，包含毫秒
    """
    return round(dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1000000, 3)


def calculate_duration(start: datetime, end: datetime) -> float:
    """
    :param start: 开始时间
    :param end: 结束时间
    :return: 持续秒数
    """
    return total_seconds(end) - total_seconds(start)


def delete_silent(audio: AudioClip | AudioSegment, chunk_size=1000) -> AudioClip | AudioSegment:
    """
    删除静音片段
    :param audio:
    :param chunk_size:
    :return:
    """
    if isinstance(audio, AudioClip):
        none_silent_chunks = []
        for chunk in audio.iter_chunks(chunksize=chunk_size):
            if not np.all(chunk == 0):
                none_silent_chunks.append(AudioArrayClip(chunk, audio.fps))
        audio = concatenate_audioclips(none_silent_chunks)
    elif isinstance(audio, AudioSegment):
        chunks = split_on_silence(audio, min_silence_len=350)
        if chunks:
            audio = reduce(lambda a, b: a + b, chunks)
    return audio


def convert_stime_to_datetime(stime: str) -> datetime:
    """
    :param stime: 00:00:00,000 格式的时间字符串
    :return: datetime对象
    """
    hours, minutes, seconds, milliseconds = map(int, stime.replace(',', ':').split(':'))
    return datetime(1970, 1, 1, hours, minutes, seconds, milliseconds * 1000)


def video_adapt_subtitle(video_path: str, srt_path: str, voice: str, output: str, speed=1.2):
    audio_clips = []
    video_clips = []
    preview_end = convert_stime_to_datetime("00:00:00,000")  # 上一个片段的end时间
    original_video = VideoFileClip(video_path).without_audio()

    # 拆分每句台词
    with open(srt_path, encoding="utf-8") as srt:
        lines = srt.read().strip().split("\n")
        # 每四行为一个台词的信息
        subtitles = [lines[i:i + 4] for i in range(0, len(lines), 4)]
    progress_bar = tqdm(total=len(subtitles))
    for subtitle in subtitles[:20]:
        # 获取当前台词的开始和结束时间
        start, end = list(map(convert_stime_to_datetime, subtitle[1].split(" --> ")))
        # 计算未读台词的时长
        silent_duration = calculate_duration(preview_end, start)
        # 生成静音视频和截取静音片段
        if silent_duration > 0.002:
            silent_audio = AudioSegment.silent(duration=silent_duration) * 1000
            print("静音：", silent_audio.duration_seconds, "ms")
            silent_video = original_video.subclip(total_seconds(preview_end), total_seconds(start))
            audio_clips.append(silent_audio)
            video_clips.append(silent_video)
        preview_end = end
        subtitle_duration = calculate_duration(start, end)
        # 生成语音
        audio_filename = asyncio.run(tts(subtitle[2].strip(), voice))
        audio_clip = AudioSegment.from_file(audio_filename)
        audio_clip = delete_silent(audio_clip)
        # 修改视频速度
        video_clip = original_video.subclip(total_seconds(start), total_seconds(end))
        video_rate = audio_clip.duration_seconds / subtitle_duration
        speed_up_clip = video_clip.speedx(1 / video_rate)
        audio_clips.append(audio_clip)
        video_clips.append(speed_up_clip)
        progress_bar.update(1)
    # 保存音频
    combined = AudioSegment.empty()
    for audio in audio_clips:
        try:
            if audio.frame_count() < 500:
                continue
            combined += audio
        except Exception as e:
            pass
    tmp_name = md5_encrypt(f"{time.time()}")
    audio_tmp_name = f'audio-{tmp_name}.mp3'
    video_tmp_name = f'video-{tmp_name}.mp4'
    combined.export(audio_tmp_name, format="mp3")
    final_video = concatenate_videoclips(video_clips)
    final_video = final_video.set_audio(AudioFileClip(audio_tmp_name))
    final_video.write_videofile(video_tmp_name)
    # 加速视频
    cmd = f'ffmpeg -i {video_tmp_name} -filter_complex "[0:v]setpts={1 / speed}*PTS[v];[0:a]atempo={speed}[a]" -map "[v]" -map "[a]" {output}'
    os.system(cmd)
    # 删除临时文件
    os.remove(audio_tmp_name)
    os.remove(video_tmp_name)


def main():
    parser.add_argument("-i", "--video_path", default="./samples/video01.mp4")
    parser.add_argument("-s", "--srt_path", default="./samples/video01_en.srt")
    parser.add_argument("-v", "--voice", default="en-AU-NatashaNeural")
    parser.add_argument("-x", "--speed", default=1.2)
    parser.add_argument("-o", "--output", default="output.mp4")
    args = parser.parse_args()
    video_path, srt_path, voice, speed, output = args.video_path, args.srt_path, args.voice, args.speed, args.output
    video_adapt_subtitle(video_path, srt_path, voice, speed, output)


if __name__ == '__main__':
    main()
