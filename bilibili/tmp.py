import os
import glob

if __name__ == '__main__':
    dirs = os.listdir()
    dirs = [directory for directory in dirs if os.path.isdir(directory) and directory != "__pycache__" and directory+".mp4" in dirs]
    for directory in dirs:
        mp4s = glob.glob(os.path.join(directory, '*.mp4'))
        mp3s = glob.glob(os.path.join(directory, '*.mp3'))
        if len(mp4s) == 0 and len(mp3s) == 0:
            pass
        else:
            assert len(mp4s) == 1, f"文件夹 {directory} 下的mp4文件数量不等于1"
            assert len(mp3s) == 1, f"文件夹 {directory} 下的mp3文件数量不等于1"
            mp4 = mp4s[0]
            mp3 = mp3s[0]
            os.remove(mp4)
            os.remove(mp3)
            print(f"已删除 {mp4} 和 {mp3}")
