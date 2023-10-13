import os
import json
import time
import asyncio

import edge_tts
import gradio as gr

from utils import tts, md5_encrypt
from video_adapt_subtitle import video_adapt_subtitle

with open('config.json', 'r', encoding="utf-8") as f:
    config = json.load(f)


def get_voices():
    voices = []
    for voice in asyncio.run(edge_tts.list_voices()):
        voices.append(voice['ShortName'])
    return voices


voices_list = get_voices()


def convert_video(video_path, srt, voice, output_dir, speed=1.2, segments=-1):
    print(f"开始转换：{video_path}")
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    fname = os.path.basename(video_path)
    fname = fname.replace(".", f"-{md5_encrypt(str(time.time()))}.")
    output_path = os.path.join(output_dir, fname)
    video_adapt_subtitle(video_path, srt.name, voice, output_path, speed, segments)
    print(f"转换完成：{output_dir}")
    return output_path


def batch_convert_video(video_dir, srt_dir, voice, output_dir):
    outputs = []
    video_files = [os.path.join(video_dir, f) for f in os.listdir(video_dir) if f.endswith(".mp4")]
    srt_files = [os.path.join(srt_dir, f) for f in os.listdir(srt_dir) if f.endswith(".srt")]
    assert len(video_files) == len(srt_files)
    for video_path, srt_path in zip(video_files, srt_files):
        outputs.append(convert_video(video_path, srt_path, voice, output_dir))
    md = ""
    for i in outputs:
        md = "\n- " + i
    return md


def generate_voice(text, voice):
    return asyncio.run(tts(text, voice))


with gr.Blocks() as demo:
    gr.Markdown("将视频与传入的srt匹配")
    with gr.Tab("单个视频转换"):
        with gr.Row():
            # 上传视频
            video_input = gr.Video(source="upload"),
            # 上传字幕文件
            with gr.Column():
                srt_input = gr.File(file_types=['srt', 'txt'])
                segments_input = gr.Number(label="转换多少句台词，默认-1为全部", value=-1, minimum=-1)
            # 选择发音
            with gr.Column():
                voices_input = gr.Dropdown(choices=voices_list, value=config['default_voice'], label="请选择声音")
                text_input = gr.Textbox(value="这是一个测试句子，用来测试的，你听听怎么样")
                voice_generate = gr.Button("生成声音片段")
                audio_output = gr.Audio(label="Output")
        with gr.Row():
            speed_slider = gr.Slider(minimum=0.8, maximum=2, label="倍速，推荐1.25", value=1.25)
            convert_btn = gr.Button("转换")
        # 选择保存路径
        save_input = gr.Textbox(label="保存路径，视频会保存为“原视频名+随机字符.mp4”", value=config['save_dir'])
        video_output = gr.Video(label="结果")

    with gr.Tab("批量转换"):
        with gr.Row():
            batch_video_input = gr.Textbox(label="视频路径", value=config['batch_video_dir'])
            batch_srt_input = gr.Textbox(label="srt路径", value=config['batch_sr_dir'])
            success_output = gr.Markdown()
        batch_convert_btn = gr.Button("批量转换")

    voice_generate.click(generate_voice, inputs=[text_input, voices_input], outputs=audio_output)
    convert_btn.click(
        convert_video,
        inputs=[video_input[0], srt_input, voices_input, save_input, speed_slider, segments_input],
        outputs=video_output
    )
    batch_convert_btn.click(batch_convert_video, inputs=[batch_video_input, batch_srt_input], outputs=success_output)

demo.launch(inbrowser=True)
