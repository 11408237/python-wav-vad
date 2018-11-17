'''
Requirements:
+ pyaudio - `pip install pyaudio`
+ py-webrtcvad - `pip install webrtcvad`
'''
import webrtcvad
import collections
import sys
import signal
import pyaudio
import os

from array import array
from struct import pack
import wave
import time
import numpy as np

# FORMAT = pyaudio.paInt16
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK_DURATION_MS = 30       # supports 10, 20 and 30 (ms)
PADDING_DURATION_MS = 1500   # 1 sec jugement
CHUNK_SIZE = int(RATE * CHUNK_DURATION_MS / 1000)  # chunk to read
CHUNK_BYTES = CHUNK_SIZE * 2  # 16bit = 2 bytes, PCM
NUM_PADDING_CHUNKS = int(PADDING_DURATION_MS / CHUNK_DURATION_MS)
# NUM_WINDOW_CHUNKS = int(240 / CHUNK_DURATION_MS)
NUM_WINDOW_CHUNKS = int(400 / CHUNK_DURATION_MS)  # 400 ms/ 30ms  ge
NUM_WINDOW_CHUNKS_END = NUM_WINDOW_CHUNKS * 2

LEVEL = 100  # 声音保存的阈值
COUNT_NUM = 10  # NUM_SAMPLES个取样之内出现COUNT_NUM个大于LEVEL的取样则记录声音
SAVE_LENGTH = 8  # 声音记录的最小长度：SAVE_LENGTH * NUM_SAMPLES 个取样

START_OFFSET = int(NUM_WINDOW_CHUNKS * CHUNK_DURATION_MS * 0.5 * RATE)

got_a_sentence = False
leave = False

def handle_int(sig, chunk):
    global leave, got_a_sentence
    leave = True
    got_a_sentence = True

def record_to_file(path, data, sample_width):
    "Records from the microphone and outputs the resulting data to 'path'"
    # sample_width, data = record()
    data = pack('<' + ('h' * len(data)), *data)
    wf = wave.open(path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(sample_width)
    wf.setframerate(RATE)
    wf.writeframes(data)
    wf.close()


def normalize(snd_data):
    "Average the volume out"
    MAXIMUM = 32767  # 16384
    if max(abs(i) for i in snd_data) != 0:
        times = float(MAXIMUM) / max(abs(i) for i in snd_data)
        r = array('h')
        for i in snd_data:
            r.append(int(i * times))
        return r
    else:
        return None

def record():
    # os.close(sys.stderr.fileno())

    vad = webrtcvad.Vad(1)

    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT,
                     channels=CHANNELS,
                     rate=RATE,
                     input=True,
                     start=False,
                     # input_device_index=2,
                     frames_per_buffer=CHUNK_SIZE)
    global  leave,got_a_sentence

    got_a_sentence = False
    leave = False
    signal.signal(signal.SIGINT, handle_int)
    nowTime = time.strftime('%Y%m%d%H%M%S', time.localtime())

    # dirPath= "recording/"
    dirPath = os.path.split(os.path.realpath(__file__))[0] + "/recording/"

    fileName = dirPath  + nowTime + ".wav"

    if(not os.path.exists(dirPath)):
        os.mkdir(dirPath)

    while not leave:
        ring_buffer = collections.deque(maxlen=NUM_PADDING_CHUNKS)
        triggered = False
        voiced_frames = []
        ring_buffer_flags = [0] * NUM_WINDOW_CHUNKS
        ring_buffer_index = 0

        ring_buffer_flags_end = [0] * NUM_WINDOW_CHUNKS_END
        ring_buffer_index_end = 0
        buffer_in = ''
        # WangS
        raw_data = array('h')
        index = 0
        start_point = 0
        StartTime = time.time()
        print("* recording: ")
        stream.start_stream()
        # 静音处理标志位
        MUTE_FLAGS = False
        while not got_a_sentence and not leave:
            chunk = stream.read(CHUNK_SIZE)
            # add WangS
            raw_data.extend(array('h', chunk))
            index += CHUNK_SIZE
            TimeUse = time.time() - StartTime

            save_count = 0
            # 将读入的数据转换为数组
            audio_data = np.fromstring(chunk, dtype=np.short)
            # 计算大于LEVEL的取样的个数
            large_sample_count = np.sum(audio_data > LEVEL)
            # print(np.max(audio_data))
            # 如果个数大于COUNT_NUM，则至少保存SAVE_LENGTH个块
            if large_sample_count > COUNT_NUM:
                save_count = SAVE_LENGTH
            else:
                save_count -= 1
            if save_count > 0:
            # 如果计算得到的数据大于 COUNT_NUM 则将音频样本送入 is_speech 进行 vad 分析
                active = vad.is_speech(chunk, RATE)

                sys.stdout.write('#' if active else '_')
                ring_buffer_flags[ring_buffer_index] = 1 if active else 0
                ring_buffer_index += 1
                ring_buffer_index %= NUM_WINDOW_CHUNKS

                ring_buffer_flags_end[ring_buffer_index_end] = 1 if active else 0
                ring_buffer_index_end += 1
                ring_buffer_index_end %= NUM_WINDOW_CHUNKS_END

                # start point detection
                if not triggered:
                    ring_buffer.append(chunk)
                    num_voiced = sum(ring_buffer_flags)
                    if num_voiced > 0.8 * NUM_WINDOW_CHUNKS:
                        sys.stdout.write(' Open ')
                        triggered = True
                        start_point = index - CHUNK_SIZE * 20  # start point
                        # voiced_frames.extend(ring_buffer)
                        ring_buffer.clear()
                # end point detection
                else:
                    # 将静音处理置位为1
                    MUTE_FLAGS = True
                    # voiced_frames.append(chunk)
                    ring_buffer.append(chunk)
                    num_unvoiced = NUM_WINDOW_CHUNKS_END - sum(ring_buffer_flags_end)
                    if num_unvoiced > 0.80 * NUM_WINDOW_CHUNKS_END or TimeUse > 10:
                        sys.stdout.write(' Close with record.')
                        triggered = False
                        got_a_sentence = True
            elif MUTE_FLAGS:
                # 当录音已经启动,并且当话音已经说完,然后进行静音的等待处理
                ring_buffer_flags_end[ring_buffer_index_end] = 0
                ring_buffer_index_end += 1
                ring_buffer_index_end %= NUM_WINDOW_CHUNKS_END

                ring_buffer.append(chunk)
                num_unvoiced = NUM_WINDOW_CHUNKS_END - sum(ring_buffer_flags_end)
                if num_unvoiced > 0.80 * NUM_WINDOW_CHUNKS_END or TimeUse > 10:
                    sys.stdout.write(' Close with vad.')
                    triggered = False
                    got_a_sentence = True

            # 停止录音标志位，录音一旦超过10秒钟就直接停止,目的保护录音文件不要太大
            if TimeUse > 10:
                sys.stdout.write(' Close with TimeUse. ')
                triggered = False
                got_a_sentence = True

            sys.stdout.flush()

        sys.stdout.write('\n')
        # data = b''.join(voiced_frames)

        stream.stop_stream()
        print("* done recording")
        got_a_sentence = False

        # write to file
        raw_data.reverse()
        for index in range(start_point):
            raw_data.pop()
        raw_data.reverse()
        raw_data = normalize(raw_data)
        if raw_data != None:
            record_to_file(fileName, raw_data, 2)
        else:
            print('##########\nERROR:No input voiced.\nPlease check the recording hardware.\n##########')
        leave = True

    stream.close()
    return  fileName







