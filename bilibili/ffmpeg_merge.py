import os
import glob
from tqdm import tqdm
import subprocess
import shutil

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

def merge_mp4_mp3(mp4_path, mp3_path, output_path):
    # 使用ffmpeg直接合并音视频
    cmd = [
        "ffmpeg",
        "-y",  # 覆盖输出文件
        "-i", mp4_path,
        "-i", mp3_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-strict", "experimental",
        "-map", "0:v:0",
        "-map", "1:a:0",
        output_path
    ]
    subprocess.run(cmd, check=True)

def process(directory):
    m4s_files = glob.glob(os.path.join(directory, '*.m4s'))
    # assert len(m4s_files) == 2, f"文件夹 {directory} 下的m4s文件数量不等于2"
    if len(m4s_files) != 2:
        print(f"文件夹 {directory} 下的m4s文件数量不等于2，跳过处理")
        return
    m4s_files = sorted(m4s_files, key=lambda x: os.path.getsize(x))
    mp3 = process_m4s_file(m4s_files[0], ".mp3")
    mp4 = process_m4s_file(m4s_files[1], ".mp4")
    output_file = f"{directory}.mp4"
    merge_mp4_mp3(mp4, mp3, output_file)
    os.remove(mp3)
    os.remove(mp4)
    
if __name__ == '__main__':
    dirs = os.listdir()
    dirs = [directory for directory in dirs if os.path.isdir(directory) and directory != "__pycache__" and directory+".mp4" not in dirs]
    root = os.getcwd()
    for directory in tqdm(dirs):
        process(os.path.join(root, directory))
