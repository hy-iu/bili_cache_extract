import os
import glob
from tqdm import tqdm
from moviepy.editor import VideoFileClip, AudioFileClip


def process_m4s_file(file_path, suffix=".mp4"):
    with open(file_path, 'rb') as file:
        first_nine_chars = file.read(9)
        if first_nine_chars == b'000000000':
            remaining_content = file.read()
            content = remaining_content
            # 将修改后的内容写回文件
            with open(file_path[:-4] + suffix, 'wb') as new_file:
                new_file.write(content)
        else:
            print(f"文件 {file_path} 不是一个有效的m4s文件")
    return file_path[:-4] + suffix

def process(directory):
    m4s_files = glob.glob(os.path.join(directory, '*.m4s'))
    assert len(m4s_files) == 2, f"文件夹 {directory} 下的m4s文件数量不等于2"
    # sort by file size
    m4s_files = sorted(m4s_files, key=lambda x: os.path.getsize(x))
    mp3 = process_m4s_file(m4s_files[0], ".mp3")
    mp4 = process_m4s_file(m4s_files[1], ".mp4")
    video = VideoFileClip(mp4)
    audio = AudioFileClip(mp3)
    video = video.set_audio(audio)
    video.write_videofile(f"{directory}.mp4")

if __name__ == '__main__':
    directorys = os.listdir()
    directorys = [directory for directory in directorys if os.path.isdir(directory) and directory != "__pycache__" and directory+".mp4" not in directorys]
    root = os.getcwd()
    for directory in tqdm(directorys):
        process(os.path.join(root, directory))
