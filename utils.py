import tempfile
import hashlib

import edge_tts


def md5_encrypt(str):
    m = hashlib.md5()
    m.update(str.encode('utf-8'))
    return m.hexdigest()


async def tts(sentence: str, voice: str) -> str:
    """
    生成朗读sentence的音频文件
    :param sentence: 需要朗读的内容
    :param voice: 朗读的声音
    :return: 生成的文件名
    """
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
        voice = edge_tts.Communicate(text=sentence, voice=voice, rate='-4%', volume='+0%')
        await voice.save(fp.name)
        return fp.name
