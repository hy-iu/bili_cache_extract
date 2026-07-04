# bili_cache_extract

提取 Bilibili（哔哩哔哩）离线缓存的视频，支持两种使用场景：
- **场景一**：直接处理已拷贝/导出到电脑上的缓存文件夹（原有脚本）
- **场景二**：通过 ADB 从已连接的安卓手机远程提取（新增脚本）

---

## 场景一：处理电脑本地的 Bilibili 缓存

> 适用于已将手机缓存文件夹复制到电脑，或使用 PC 版 Bilibili 客户端下载的情况。

Bilibili 缓存的每个视频通常放在独立的子文件夹中，包含 `video.m4s`（视频轨）和 `audio.m4s`（音频轨）两个文件，需要合并后才能正常播放。

### 环境依赖

需要 [Python 环境](https://www.python.org/)

### 方式 A：使用 `test.py`（基于 moviepy）

进入缓存目录，放入 `test.py`，安装依赖：

```shell
pip install tqdm moviepy
```

运行：

```shell
python ./test.py
```

脚本会自动处理当前目录下的所有子文件夹，将每个视频的音视频轨合并输出为与文件夹同名的 `.mp4` 文件。

### 方式 B：使用 `ffmpeg_merge.py`（基于 FFmpeg，更快）

需要先安装 FFmpeg：

```shell
# macOS
brew install ffmpeg
# Windows：请前往 https://ffmpeg.org/ 下载并配置 PATH
```

进入缓存目录，运行：

```shell
python ./ffmpeg_merge.py
```

与 `test.py` 相比，此脚本使用 FFmpeg 直接合并，速度更快，且遇到 m4s 数量不为 2 的文件夹时会跳过而不是报错终止。

---

## 场景二：通过 ADB 从安卓手机远程提取（推荐）

> 适用于不想手动导出文件夹、希望直接通过数据线从手机批量提取的情况。

新增的 `extractor.py` 和 `backup_metadata.py` 脚本无需手动复制缓存文件夹，可以直接通过 USB 数据线连接手机后自动完成扫描、提取与合并。

### 环境依赖

1. **Python 3**
2. **ADB (Android Debug Bridge)**：
   ```bash
   brew install --cask android-platform-tools
   ```
3. **FFmpeg**：
   ```bash
   brew install ffmpeg
   ```

### 手机端准备工作

1. **开启开发者模式**：进入 **设置 -> 关于手机**，连续快速点击 **版本号** 7 次，输入锁屏密码后提示"已处于开发者模式"。
2. **启用 USB 调试**：进入 **设置 -> 系统和更新 -> 开发人员选项**，开启 **USB 调试**。
3. **MTP 传输模式**：将手机用数据线连上电脑，在通知栏将 USB 连接模式切换为 **"传输文件" (MTP)**。
4. **授权调试**：手机屏幕弹出 **"是否允许 USB 调试？"**，勾选"始终允许"后点确定。

> **Huawei 手机特别说明**：如果安装了 HiSuite，请在 **设置 -> 安全** 中关闭"允许 HiSuite 通过 HDB 连接本机"，否则 HiSuite 会抢占 ADB 连接。

### 工具使用

#### `extractor.py`：视频提取与合并

```bash
# 扫描手机缓存并列出前 10 个视频（首次运行会自动生成本地索引缓存）
python3 extractor.py

# 列出所有视频及提取状态（[已提取] / [未提取]）
python3 extractor.py --list

# 安全批量提取（推荐：自动保留至少 5GB 磁盘余量，空间不足时自动停止）
python3 extractor.py --extract-safe

# 按序号提取单个视频
python3 extractor.py --index 152

# 按关键词搜索视频
python3 extractor.py --search "关键词"

# 强制重新扫描手机（如手机上下载了新内容）
python3 extractor.py --scan --list
```

> **状态持久化**：提取状态记录在 `videos_list.json` 中。即使删除本地已提取的 `.mp4` 文件腾出空间，再次运行时也不会重复提取。

#### `backup_metadata.py`：元数据备份与索引手册生成

```bash
python3 backup_metadata.py
```

运行后生成：
- `metadata/`：每个视频缓存对应的原始 JSON 属性文件
- `video_catalog.md`：包含作者、分辨率、时长及**可直接跳转至 B 站原页面链接**的视频目录表格
- `metadata_summary.json`：全部视频属性的结构化 JSON 汇总

---

## 技术原理

Bilibili 安卓离线缓存格式有两个特点：

1. **音画分离**：视频轨存储在 `video.m4s`（无声音），音频轨存储在 `audio.m4s`（无画面），需要合并才能正常播放。
2. **9 字节文件头干扰**：部分 `.m4s` 文件头部被写入了 9 字节的 `000000000` 干扰字符，普通播放器会报错损坏。所有脚本均会自动检测并去除这一干扰字节，还原为标准 MP4 流。
