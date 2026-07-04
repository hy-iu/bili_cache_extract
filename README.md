# Bilibili Offline Cache Extractor & Cataloger (bili_cache_extract)

这是一个用于从已连接的安卓手机中读取、提取、解码并合成哔哩哔哩（Bilibili）离线缓存视频的工具集。

## 新增工具介绍

1. **`extractor.py`**：高级视频提取与合并脚本。
   * 支持从手机自动拉取音频轨和视频轨。
   * 自动剥离 B 站特有的 9 字节加密文件头，将其无损合并为标准的 `.mp4` 格式。
   * **安全磁盘空间检查**：自动检测您电脑的剩余空间并预留至少 5GB 安全余量，防止撑爆电脑磁盘。
   * **状态持久化**：提取状态记录在本地，即使删除了已提取的 `.mp4` 文件释放空间，再次运行时也绝对不会重复提取！
2. **`backup_metadata.py`**：元数据备份与目录手册生成脚本。
   * 备份手机中缓存视频的全部属性。
   * 自动生成包含视频作者、分辨率、时长、弹幕数及**直接跳转到 B 站原网页**链接的视频索引手册 `video_catalog.md`。

---

## 环境准备

1. 安装 **Python 3**
2. 安装 **ADB (Android Debug Bridge)**：
   ```bash
   brew install --cask android-platform-tools
   ```
3. 安装 **FFmpeg**：
   ```bash
   brew install ffmpeg
   ```

---

## 使用说明

请在终端项目路径下运行以下命令：

### 1. 提取视频 (`extractor.py`)

* **扫描并列出前 10 个视频**（第一次运行会自动在本地生成 `videos_list.json` 元数据索引缓存）：
  ```bash
  python3 extractor.py
  ```
* **查看全部视频列表与提取状态**（`[已提取]` / `[未提取]`）：
  ```bash
  python3 extractor.py --list
  ```
* **安全批量提取**（推荐！自动根据电脑磁盘空闲空间进行提取，留足 5GB 系统安全余量）：
  ```bash
  python3 extractor.py --extract-safe
  ```
* **按序号提取单个视频**：
  ```bash
  python3 extractor.py --index 152
  ```
* **按关键词搜索**：
  ```bash
  python3 extractor.py --search "关键词"
  ```
* **强制重新扫描手机缓存**（如果您在手机里下载了新视频）：
  ```bash
  python3 extractor.py --scan --list
  ```

### 2. 备份元数据并生成手册 (`backup_metadata.py`)

运行以下命令：
```bash
python3 backup_metadata.py
```
运行完成后，会为您生成：
* **`metadata/` 文件夹**：存放了 200 个缓存的原始 JSON 文件。
* **`video_catalog.md`**：自动生成的排版精美的 Markdown 视频列表，包含 UP主姓名、分辨率、时长，以及可以直接点击跳转到 B 站原网页的跳转链接。
* **`metadata_summary.json`**：所有视频属性的完整结构化 JSON 汇总。
