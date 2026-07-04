import os
import sys
import json
import subprocess
import shutil
import re
import argparse

ADB_PATH = "adb"  # Standard adb path

class BiliExtractor:
    def __init__(self, output_dir="./output"):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.temp_dir = os.path.abspath("./temp")
        os.makedirs(self.temp_dir, exist_ok=True)

    def mark_extracted_in_cache(self, bvid, cid, file_exists, output_file):
        cache_file = "videos_list.json"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    videos = json.load(f)
                
                changed = False
                for v in videos:
                    if v["bvid"] == bvid and v["cid"] == cid:
                        v["extracted"] = True
                        v["local_path"] = output_file if file_exists else None
                        changed = True
                
                if changed:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(videos, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Warning: Failed to update cache file status: {e}")
        
    def run_adb(self, args):
        cmd = [ADB_PATH] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ADB command failed: {' '.join(cmd)}\nError: {result.stderr}")
        return result.stdout

    def scan_devices(self):
        output = self.run_adb(["devices"])
        lines = output.strip().split("\n")
        devices = []
        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                devices.append((parts[0], parts[1]))
        return devices

    def scan_phone_cache(self):
        print("Scanning phone for Bilibili cache directories...")
        find_cmd = ["shell", "find /sdcard/Android/data/tv.danmaku.bili/download/ -name entry.json"]
        try:
            entry_files = self.run_adb(find_cmd).strip().split("\n")
        except Exception as e:
            print(f"Error scanning phone directories: {e}")
            return []
            
        entry_files = [f.strip() for f in entry_files if f.strip()]
        print(f"Found {len(entry_files)} offline cache entries on the phone.")
        
        videos = []
        # Sort files to maintain consistent ordering
        entry_files.sort()
        
        for index, entry_path in enumerate(entry_files):
            try:
                # Read entry.json content
                content = self.run_adb(["shell", f"cat '{entry_path}'"]).strip()
                if not content:
                    continue
                data = json.loads(content)
                
                # Determine directories
                part_dir = os.path.dirname(entry_path)
                
                # Let's list subdirectories of part_dir to find the quality folder (it's numeric)
                list_subdirs = self.run_adb(["shell", f"ls -d '{part_dir}'/*"]).strip().split("\n")
                quality_dir = None
                for subdir in list_subdirs:
                    subdir = subdir.strip()
                    basename = os.path.basename(subdir)
                    if basename.isdigit():
                        quality_dir = subdir
                        break
                
                title = data.get("title", "Unknown Title")
                subtitle = data.get("page_data", {}).get("download_subtitle", "")
                if not subtitle:
                    subtitle = data.get("page_data", {}).get("part", "")
                    
                bvid = data.get("bvid", "")
                avid = data.get("avid", "")
                cid = data.get("page_data", {}).get("cid", "")
                video_quality = data.get("quality_pithy_description", "")
                total_bytes = data.get("total_bytes", 0)
                
                videos.append({
                    "index": index + 1,
                    "title": title,
                    "subtitle": subtitle,
                    "bvid": bvid,
                    "avid": avid,
                    "cid": cid,
                    "quality": video_quality,
                    "total_bytes": total_bytes,
                    "part_dir": part_dir,
                    "quality_dir": quality_dir,
                    "entry_path": entry_path
                })
            except Exception as e:
                # Ignore individual scan errors
                continue
                
        return videos

    def clean_m4s_header(self, input_path, output_path):
        """
        Bilibili's .m4s streams can sometimes be prepended with a 9-byte header.
        We detect and strip it.
        """
        with open(input_path, "rb") as f:
            header = f.read(32)
            if len(header) < 16:
                # File is too small, just copy it
                f.seek(0)
                with open(output_path, "wb") as out:
                    out.write(f.read())
                return
            
            # Check if ftyp is at offset 4 (standard MP4)
            if header[4:8] == b"ftyp":
                strip_offset = 0
            # Check if ftyp is at offset 13 (9-byte Bilibili header)
            elif header[13:17] == b"ftyp":
                strip_offset = 9
            else:
                # Fallback: search for ftyp
                ftyp_idx = header.find(b"ftyp")
                if ftyp_idx != -1 and ftyp_idx >= 4:
                    strip_offset = ftyp_idx - 4
                else:
                    strip_offset = 0
            
            f.seek(strip_offset)
            with open(output_path, "wb") as out:
                shutil.copyfileobj(f, out)

    def extract_and_convert(self, video):
        sanitized_title = re.sub(r'[\\/*?:"<>| ]', "_", f"{video['title']}_{video['subtitle']}")
        output_file = os.path.join(self.output_dir, f"{sanitized_title}.mp4")
        
        print(f"\nProcessing: {video['title']} - {video['subtitle']}")
        print(f"BVID: {video['bvid']} | Quality: {video['quality']}")
        
        q_dir = video["quality_dir"]
        if not q_dir:
            print("Error: Could not locate quality folder containing media files on phone.")
            return False
            
        local_video_m4s = os.path.join(self.temp_dir, "video_raw.m4s")
        local_audio_m4s = os.path.join(self.temp_dir, "audio_raw.m4s")
        clean_video_m4s = os.path.join(self.temp_dir, "video_clean.m4s")
        clean_audio_m4s = os.path.join(self.temp_dir, "audio_clean.m4s")
        
        # Pull files from phone
        print("Pulling video stream from phone...")
        try:
            self.run_adb(["pull", f"{q_dir}/video.m4s", local_video_m4s])
        except Exception as e:
            print(f"Error pulling video stream: {e}")
            return False
            
        print("Pulling audio stream from phone...")
        try:
            self.run_adb(["pull", f"{q_dir}/audio.m4s", local_audio_m4s])
        except Exception as e:
            print(f"Error pulling audio stream: {e}")
            return False
            
        # Clean headers
        print("Cleaning custom headers...")
        self.clean_m4s_header(local_video_m4s, clean_video_m4s)
        self.clean_m4s_header(local_audio_m4s, clean_audio_m4s)
        
        # Merge using FFmpeg
        print("Merging streams using FFmpeg...")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", clean_video_m4s,
            "-i", clean_audio_m4s,
            "-codec", "copy",
            output_file
        ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg merge failed:\n{result.stderr}")
            return False
            
        print(f"Successfully created: {output_file}")
        
        # Record completed extraction in videos_list.json
        self.mark_extracted_in_cache(video['bvid'], video['cid'], True, output_file)
        
        # Cleanup temp files
        for f in [local_video_m4s, local_audio_m4s, clean_video_m4s, clean_audio_m4s]:
            if os.path.exists(f):
                os.remove(f)
                
        return output_file

def main():
    parser = argparse.ArgumentParser(description="Extract and convert Bilibili offline cached videos from Android phone.")
    parser.add_argument("--scan", action="store_true", help="Force rescan of the phone's cache.")
    parser.add_argument("--list", action="store_true", help="List all found cached videos.")
    parser.add_argument("--index", type=int, help="Extract and convert a specific video by its list index.")
    parser.add_argument("--all", action="store_true", help="Extract and convert all found videos.")
    parser.add_argument("--extract-safe", action="store_true", help="Extract videos while maintaining safe free disk space.")
    parser.add_argument("--search", type=str, help="Search for videos by title.")
    args = parser.parse_args()

    extractor = BiliExtractor()
    
    # Check device connection
    devices = extractor.scan_devices()
    if not devices:
        print("Error: No Android devices found. Make sure your phone is connected and USB debugging is enabled.")
        sys.exit(1)
        
    videos = []
    cache_file = "videos_list.json"
    
    # Load old cache for status carry-over
    old_extracted_keys = set()
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                old_videos = json.load(f)
                for v in old_videos:
                    if v.get("extracted"):
                        old_extracted_keys.add(f"{v['bvid']}_{v['cid']}")
        except Exception:
            pass

    # Scan phone if requested, or if cache doesn't exist
    if args.scan or not os.path.exists(cache_file):
        videos = extractor.scan_phone_cache()
    else:
        with open(cache_file, "r", encoding="utf-8") as f:
            videos = json.load(f)
            
    # Update extracted status dynamically based on file existence or carry-over status
    for v in videos:
        sanitized_title = re.sub(r'[\\/*?:"<>| ]', "_", f"{v['title']}_{v['subtitle']}")
        output_file = os.path.join(extractor.output_dir, f"{sanitized_title}.mp4")
        key = f"{v['bvid']}_{v['cid']}"
        v["extracted"] = os.path.exists(output_file) or key in old_extracted_keys
        v["local_path"] = output_file if os.path.exists(output_file) else None
        
    # Write updated list back to cache
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)
            
    if not videos:
        print("No videos found.")
        sys.exit(0)
        
    if args.list:
        print("\n--- CACHED VIDEOS ---")
        extracted_count = 0
        for v in videos:
            status = "[已提取]" if v["extracted"] else "[未提取]"
            if v["extracted"]:
                extracted_count += 1
            size_mb = v['total_bytes'] / (1024 * 1024)
            print(f"[{v['index']}] {status} {v['title']} - {v['subtitle']} ({v['quality']}, {size_mb:.1f} MB)")
        print(f"\nSummary: Total: {len(videos)}, Extracted: {extracted_count}, Remaining: {len(videos) - extracted_count}")
            
    elif args.search:
        print(f"\n--- SEARCH RESULTS FOR '{args.search}' ---")
        found = False
        for v in videos:
            if args.search.lower() in v['title'].lower() or args.search.lower() in v['subtitle'].lower():
                status = "[已提取]" if v["extracted"] else "[未提取]"
                size_mb = v['total_bytes'] / (1024 * 1024)
                print(f"[{v['index']}] {status} {v['title']} - {v['subtitle']} ({v['quality']}, {size_mb:.1f} MB)")
                found = True
        if not found:
            print("No matching videos found.")
            
    elif args.index:
        # Find video by index
        video = next((v for v in videos if v["index"] == args.index), None)
        if not video:
            print(f"Error: Video index {args.index} not found.")
            sys.exit(1)
        extractor.extract_and_convert(video)
        
    elif args.extract_safe:
        # Check free space
        # Target reserve is 5GB (5000 * 1024 * 1024 bytes)
        safe_reserve = 5 * 1024 * 1024 * 1024 
        print(f"Starting safe extraction. Will maintain at least {safe_reserve / (1024**3):.1f} GB of free disk space.")
        
        success_count = 0
        skipped_count = 0
        
        for video in videos:
            # Check if already exists
            sanitized_title = re.sub(r'[\\/*?:"<>| ]', "_", f"{video['title']}_{video['subtitle']}")
            output_file = os.path.join(extractor.output_dir, f"{sanitized_title}.mp4")
            if os.path.exists(output_file) or video.get("extracted"):
                skipped_count += 1
                if os.path.exists(output_file) and not video.get("extracted"):
                    extractor.mark_extracted_in_cache(video['bvid'], video['cid'], True, output_file)
                continue
                
            # Get current free space
            free_bytes = shutil.disk_usage(extractor.output_dir).free
            video_size = video["total_bytes"]
            
            # We need:
            # - video_size (approx) for final file
            # - video_size * 2 for temp raw files + clean files
            # Total temp space during merge is about 3 * video_size.
            # But once done, the net space used is video_size.
            # So we check if: free_bytes - 3 * video_size > safe_reserve
            required_space = 3 * video_size
            if free_bytes - required_space < safe_reserve:
                print(f"\n[Warning] Stopping extraction to maintain safe disk space.")
                print(f"Current free space: {free_bytes / (1024**3):.2f} GB")
                print(f"Required space for next video: {required_space / (1024**3):.2f} GB")
                print(f"Safe reserve: {safe_reserve / (1024**3):.2f} GB")
                break
                
            res = extractor.extract_and_convert(video)
            if res:
                success_count += 1
                
        print(f"\nSafe processing finished. Extracted: {success_count}, Already existed: {skipped_count}.")

    elif args.all:
        print(f"Starting batch extraction of {len(videos)} videos...")
        success_count = 0
        for video in videos:
            res = extractor.extract_and_convert(video)
            if res:
                success_count += 1
        print(f"\nBatch processing finished. Successfully extracted {success_count} / {len(videos)} videos.")
        
    else:
        # Default behavior: list the first 10 videos and print help
        print(f"\nFound {len(videos)} videos. Showing first 10:")
        for v in videos[:10]:
            size_mb = v['total_bytes'] / (1024 * 1024)
            print(f"[{v['index']}] {v['title']} - {v['subtitle']} ({v['quality']}, {size_mb:.1f} MB)")
        if len(videos) > 10:
            print(f"... and {len(videos) - 10} more.")
        print("\nUse --help to see all command options (e.g., --index <num> to extract a video).")

if __name__ == "__main__":
    main()
