import os
import sys
import json
import subprocess
import re

ADB_PATH = "adb"

def run_adb(args):
    cmd = [ADB_PATH] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"ADB command failed: {' '.join(cmd)}\nError: {result.stderr}")
    return result.stdout

def format_duration(ms):
    if not ms:
        return "00:00"
    seconds = int(ms / 1000)
    minutes = int(seconds / 60)
    seconds = seconds % 60
    hours = int(minutes / 60)
    minutes = minutes % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

def main():
    cache_file = "videos_list.json"
    if not os.path.exists(cache_file):
        print(f"Error: {cache_file} not found. Please run extractor.py first.")
        sys.exit(1)
        
    with open(cache_file, "r", encoding="utf-8") as f:
        videos = json.load(f)
        
    metadata_dir = "./metadata"
    os.makedirs(metadata_dir, exist_ok=True)
    
    print(f"Backing up metadata for {len(videos)} videos...")
    rich_metadata = []
    
    for idx, video in enumerate(videos):
        bvid = video.get("bvid", "")
        cid = video.get("cid", "")
        title = video.get("title", "")
        subtitle = video.get("subtitle", "")
        entry_path = video.get("entry_path", "")
        index_num = video.get("index", idx + 1)
        
        sanitized_name = re.sub(r'[\\/*?:"<>| ]', "_", f"{title}_{subtitle}")
        local_entry_path = os.path.join(metadata_dir, f"{index_num:03d}_{sanitized_name}_entry.json")
        
        print(f"[{index_num}/{len(videos)}] Pulling metadata for: {title}")
        
        try:
            # Pull the entry.json file from the phone
            run_adb(["pull", entry_path, local_entry_path])
            
            # Read and parse the local copy
            with open(local_entry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            owner_name = data.get("owner_name", "未知作者")
            owner_id = data.get("owner_id", "")
            danmaku_count = data.get("danmaku_count", 0)
            duration_ms = data.get("total_time_milli", 0)
            duration_str = format_duration(duration_ms)
            cover_url = data.get("cover", "")
            
            page_data = data.get("page_data", {})
            width = page_data.get("width", 0)
            height = page_data.get("height", 0)
            resolution = f"{width}x{height}" if width and height else "未知"
            quality = data.get("quality_pithy_description", "")
            if not quality:
                quality = video.get("quality", "")
                
            gdrive_link = f"https://www.bilibili.com/video/{bvid}/" if bvid else ""
            
            rich_metadata.append({
                "index": index_num,
                "title": title,
                "subtitle": subtitle,
                "bvid": bvid,
                "author": owner_name,
                "author_id": owner_id,
                "url": gdrive_link,
                "resolution": resolution,
                "quality": quality,
                "duration": duration_str,
                "danmaku_count": danmaku_count,
                "cover": cover_url,
                "size_mb": video.get("total_bytes", 0) / (1024 * 1024),
                "extracted": video.get("extracted", False)
            })
            
        except Exception as e:
            print(f"  Warning: Failed to process metadata for index {index_num}: {e}")
            # Fallback using existing cache data
            rich_metadata.append({
                "index": index_num,
                "title": title,
                "subtitle": subtitle,
                "bvid": bvid,
                "author": "未知",
                "author_id": "",
                "url": f"https://www.bilibili.com/video/{bvid}/" if bvid else "",
                "resolution": "未知",
                "quality": video.get("quality", ""),
                "duration": "未知",
                "danmaku_count": 0,
                "cover": "",
                "size_mb": video.get("total_bytes", 0) / (1024 * 1024),
                "extracted": video.get("extracted", False)
            })

    # Save compiled rich metadata summary
    summary_file = "metadata_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(rich_metadata, f, ensure_ascii=False, indent=2)
    print(f"\nSaved metadata summary to: {summary_file}")
    
    # Generate a beautiful Markdown catalog
    catalog_file = "video_catalog.md"
    with open(catalog_file, "w", encoding="utf-8") as f:
        f.write("# Bilibili Offline Videos Catalog\n\n")
        f.write(f"This catalog lists all **{len(rich_metadata)}** offline videos scanned from your phone.\n\n")
        f.write("| Index | Title & Episode | Author | Quality | Resolution | Duration | Size | Link | Status |\n")
        f.write("| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        
        for item in rich_metadata:
            title_display = f"**{item['title']}**"
            if item['subtitle'] and item['subtitle'] != item['title']:
                title_display += f"<br>*{item['subtitle']}*"
                
            link_display = f"[Detail Page]({item['url']})" if item['url'] else "-"
            status_display = "✅ 已提取" if item['extracted'] else "❌ 未提取"
            size_display = f"{item['size_mb']:.1f} MB"
            
            f.write(f"| {item['index']} | {title_display} | {item['author']} | {item['quality']} | {item['resolution']} | {item['duration']} | {size_display} | {link_display} | {status_display} |\n")
            
    print(f"Generated Markdown catalog at: {catalog_file}")
    
    # Print total backup size
    total_backup_bytes = 0
    for root, dirs, files in os.walk(metadata_dir):
        for file in files:
            total_backup_bytes += os.path.getsize(os.path.join(root, file))
            
    print(f"Total backup folder size: {total_backup_bytes / 1024:.2f} KB")

if __name__ == "__main__":
    main()
