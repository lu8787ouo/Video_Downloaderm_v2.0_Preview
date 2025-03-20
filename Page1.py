import os
import re
import time
import functools
import subprocess
from logging_config import setup_logger, log_and_show_error
from pytubefix import YouTube
import yt_dlp
from rich import print

# ------------------------------
# 初始化 Logger
# ------------------------------
logger = setup_logger(__name__)

def timeit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        logger.info(f"{func.__name__} executed in {elapsed:.4f} seconds")
        return result
    return wrapper

def sanitize_filename(filename):
    """
    將檔案名稱中 Windows 不允許的字元替換為底線，
    並移除控制字元或非可見字元。
    """
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'[\x00-\x1f\x80-\x9f]', '', filename)
    return filename

def generate_new_filename(download_path, filename):
    """
    檢查 download_path 中是否已存在相同檔名，若存在則在檔名後方加上 (1), (2) 等標記。
    """
    filename = sanitize_filename(filename)
    base, ext = os.path.splitext(filename)
    new_filename = filename
    counter = 1
    while os.path.exists(os.path.join(download_path, new_filename)):
        new_filename = f"{base} ({counter}){ext}"
        counter += 1
    return new_filename

def resolution_sort_key(res, downloader):
    """自訂排序邏輯，讓解析度由高到低排列"""
    if downloader == 'pytubefix':
        return int(res.replace("p", "")) if res else 0  # 轉換成數字排序
    elif downloader == 'yt_dlp':
        if res.lower() == "audio only":
            return -1  # 過濾掉 audio only
        try:
            width, height = map(int, res.split('x'))
            return width * height  # 根據解析度大小排序
        except ValueError:
            return 0  # 若解析度格式異常，則視為最小

@timeit
def get_video_info(url, downloader, file_format="mp4"):
    """取得影片資訊，包括標題、可用畫質、封面圖 URL、可用字幕"""
    title = "Unknown Title"  # 預設值
    subtitles = ["No subtitle"]  # 預設值
    if downloader == 'pytubefix':
        logger.info("Using pytubefix get info")
        yt_obj = YouTube(url)
        title = yt_obj.title
        thumbnail_url = yt_obj.thumbnail_url

        available_subs = yt_obj.captions
        if available_subs:
            subs_list = [cap.code if hasattr(cap, "code") else str(cap) for cap in available_subs.keys()]
            subtitles = ["No subtitle"] + subs_list

        if file_format == "mp4":
            resolutions = list(set([
                stream.resolution for stream in yt_obj.streams.filter(adaptive=True)
                if stream.resolution
            ]))
            resolutions.sort(key=lambda res: int(res.replace("p", "")) if res and res.replace("p", "").isdigit() else 0,
                             reverse=True)
        else: # mp3 模式：直接提供模板選項
            resolutions = ["64kbps","128kbps", "192kbps", "256kbps", "320kbps"]
            resolutions.sort(key=lambda s: int(s.replace("kbps", "")), reverse=True)
    elif downloader == 'yt_dlp':
        logger.info("Using yt_dlp get info")
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            # 讓 yt_dlp 下載字幕資訊
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitlesformat': 'srt',
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        title = info.get('title', 'Unknown Title')
        thumbnail_url = info.get('thumbnail')
        if file_format == "mp4":
            resolutions = list(set([
                stream['resolution'] for stream in info.get('formats', []) if stream.get('resolution')
            ]))
            resolutions.sort(key=lambda res: resolution_sort_key(res, downloader), reverse=True)
        else:  # mp3 模式，取得音訊位元率
            resolutions = ["64kbps","128kbps", "192kbps", "256kbps", "320kbps"]
            resolutions.sort(key=lambda s: int(s.replace("kbps", "")) if s and s.replace("kbps", "").isdigit() else 0, reverse=True)

        # 檢查影片是否有字幕資訊
        if info.get("subtitles"):
            available_subs = list(info["subtitles"].keys())
            subtitles = ["No subtitle"] + available_subs
        elif info.get("automatic_captions"):
            available_subs = list(info["automatic_captions"].keys())
            subtitles = ["No subtitle"] + available_subs

    return title, thumbnail_url, resolutions, subtitles

@timeit
def download_video_audio(url, resolution, download_path, downloader, file_format, download_subtitles, subtitle_lang, progress_callback=None):
    if downloader == 'pytubefix':
        logger.info("Using pytubefix to download video")

        def on_progress(stream, chunk, bytes_remaining):
                total = stream.filesize
                downloaded = total - bytes_remaining
                fraction = downloaded / total if total else 0
                overall = fraction * 0.6
                if progress_callback:
                    progress_callback(overall)

        yt_obj = YouTube(url, on_progress_callback=on_progress)
        safe_title = sanitize_filename(yt_obj.title)

        if file_format == 'mp4':
            # 根據使用者指定解析度篩選影片串流（只取影片）
            video_candidates = list(yt_obj.streams.filter(only_video=True, res=resolution))
            if not video_candidates:
                raise ValueError("找不到符合解析度的影片串流！")
            video_stream = video_candidates[0]
            # 判斷影片串流的副檔名
            video_ext = video_stream.subtype if hasattr(video_stream, "subtype") else video_stream.mime_type.split('/')[-1]
            
            # 從所有音訊串流中挑選音質最高的
            audio_candidates = list(yt_obj.streams.filter(only_audio=True))
            if not audio_candidates:
                raise ValueError("找不到對應的音訊串流！")
            def get_abr(stream):
                try:
                    return stream.abr if hasattr(stream, "abr") and stream.abr else 0
                except:
                    return 0
            audio_candidates.sort(key=get_abr, reverse=True)
            audio_stream = audio_candidates[0]
            # 判斷音訊串流的副檔名
            audio_ext = audio_stream.subtype if hasattr(audio_stream, "subtype") else audio_stream.mime_type.split('/')[-1]

            # 定義暫存檔名（依各自副檔名命名）
            video_temp_name = "video_temp." + video_ext
            audio_temp_name = "audio_temp." + audio_ext
            video_path = os.path.join(download_path, video_temp_name)
            audio_path = os.path.join(download_path, audio_temp_name)

            filename = safe_title + ".mp4"
            unique_filename = generate_new_filename(download_path, filename)
            output_path = os.path.join(download_path, unique_filename)

            logger.info("Downloading video...")
            video_stream.download(output_path=download_path, filename=video_temp_name)

            logger.info("Downloading audio...")
            audio_stream.download(output_path=download_path, filename=audio_temp_name)

            logger.info("Merging video and audio...")
            merge_video_audio(video_path, audio_path, output_path, progress_callback)
            
            logger.info("Cleaning up temporary files...")
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
        elif file_format == 'mp3':
             # 嘗試解析用戶選擇的位元率，例如 "320kbps"
            try:
                selected_bitrate = int(resolution.replace("kbps", ""))
            except Exception as e:
                selected_bitrate = None
            
            audio_candidates = list(yt_obj.streams.filter(only_audio=True))
            if not audio_candidates:
                raise ValueError("找不到對應的音訊串流！")
            matching_stream = None
            if selected_bitrate is not None:
                for stream in audio_candidates:
                    if hasattr(stream, "abr") and stream.abr == selected_bitrate:
                        matching_stream = stream
                        break
            # 若找不到精確匹配，則取音質最佳的
            if not matching_stream:
                def get_abr(stream):
                    try:
                        return stream.abr if hasattr(stream, "abr") and stream.abr else 0
                    except:
                        return 0
                audio_candidates.sort(key=get_abr, reverse=True)
                matching_stream = audio_candidates[0]
            # 判斷音訊串流的副檔名
            audio_ext = matching_stream.subtype if hasattr(matching_stream, "subtype") else matching_stream.mime_type.split('/')[-1]
            
            audio_temp_name = "audio_temp." + audio_ext
            audio_path = os.path.join(download_path, audio_temp_name)
            filename = safe_title + ".mp3"
            unique_filename = generate_new_filename(download_path, filename)
            output_path = os.path.join(download_path, unique_filename)

            logger.info("Downloading audio...")        
            if progress_callback: progress_callback(0.0)
            matching_stream.download(output_path=download_path, filename=audio_temp_name)
            
            logger.info("Converting audio format...")
            if progress_callback: progress_callback(0.6)
            ffmpeg_path = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'bin', 'ffmpeg.exe')
            ffmpeg_command = [
                ffmpeg_path, '-i', audio_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '2', output_path
            ]
            process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, encoding='utf-8', errors='replace',
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            for line in process.stderr:
                # 解析進度更新 progress_bar（根據需求調整）
                pass
            process.wait()
            if os.path.exists(audio_path):
                os.remove(audio_path)
        
        # 若使用者勾選下載字幕且選擇了非 "No subtitle" 語言，則處理字幕下載
        if download_subtitles and subtitle_lang != "No subtitle":
            try:
                selected_caption = None
                selected_caption = yt_obj.captions[subtitle_lang]
                if selected_caption:
                    subtitle_output_path = os.path.join(download_path, safe_title + f"_{subtitle_lang}.srt")
                    selected_caption.save_captions(subtitle_output_path)
                    logger.info(f"Succeeded to download subtitle: {subtitle_output_path}")
                else:
                    log_and_show_error("Cannot find the specified language subtitle")
            except Exception as e:
                log_and_show_error(f"Subtitle download failed: {e}")

        # 處理完成
        if progress_callback: progress_callback(-1)
        return output_path

    elif downloader == 'yt_dlp':
        logger.info("Using yt_dlp to download video")
        if file_format == 'mp4':
            # 從解析度字串中取得寬高，例如 "1920x1080"
            try:
                width_str, height_str = resolution.split('x')
                width = int(width_str)
                height = int(height_str)
                # 當高度為 720，且寬度接近 1280，則修正為 1280
                if height == 720 and abs(width - 1280) <= 20:
                    width = 1280
            except Exception as e:
                raise ValueError("解析解析度失敗，請檢查格式是否正確(例如 '1920x1080')") from e
            # 將下載檔案暫存為固定名稱，例如 temp_download.mp4
            temp_template = os.path.join(download_path, "temp_download.%(ext)s")
            ydl_opts = {
                'format': f'bestvideo[ext=webm][width={width}][height={height}]+bestaudio[ext=webm]/best[ext=webm]',
                'outtmpl': temp_template,
                'noplaylist': True,
                'merge_output_format': 'mp4',
                'postprocessor_args': ['-c:a', 'aac'],  # 強制使用 aac 音訊編碼
            }
        elif file_format == 'mp3':
            temp_template = os.path.join(download_path, "temp_download.%(ext)s")
            # 嘗試解析用戶選擇的位元率
            selected_bitrate = None
            try:
                selected_bitrate = int(resolution.replace("kbps", "").strip())
            except Exception:
                pass
            if selected_bitrate is not None:
                format_str = f"bestaudio[abr={selected_bitrate}]/bestaudio/best"
                preferred_quality = str(selected_bitrate)
            else:
                format_str = "bestaudio/best"
                preferred_quality = str(selected_bitrate)
            ydl_opts = {
                'format': format_str,
                'outtmpl': temp_template,
                'noplaylist': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': preferred_quality,
                }],
            }
        # 若勾選下載字幕且選擇了特定語言，加入 yt_dlp 下載字幕的選項
        if download_subtitles and subtitle_lang != "No subtitle":
            ydl_opts["subtitlesformat"] = 'srt'
            ydl_opts["writesubtitles"] = True
            ydl_opts["writeautomaticsub"] = True
            ydl_opts["subtitleslangs"] = [subtitle_lang]
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                current = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes_estimate') or d.get('total_bytes') or 1
                fraction = current / total if total else 0
                if progress_callback:
                    progress_callback(fraction * 0.6)
            elif d['status'] == 'finished':
                if progress_callback:
                    progress_callback(0.99)
        ydl_opts['progress_hooks'] = [progress_hook]
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        if file_format == 'mp4':
            output_ext = 'mp4'
        else:
            output_ext = 'mp3'
        # 取得 yt_dlp 回傳的影片標題
        raw_title = info['title']
        # 利用自訂函式先清理標題，再產生唯一檔案名稱
        safe_title = sanitize_filename(raw_title)
        filename = safe_title + f".{output_ext}"
        unique_filename = generate_new_filename(download_path, filename)
        final_filepath = os.path.join(download_path, unique_filename)
        # 取得暫存檔案的完整路徑
        temp_filepath = os.path.join(download_path, f"temp_download.{output_ext}")
        # 重新命名暫存檔案
        os.rename(temp_filepath, final_filepath)
        
        # 處理完成
        if progress_callback: progress_callback(-1)
        return final_filepath

@timeit
def merge_video_audio(video_path, audio_path, output_path, progress_callback=None):
    """使用 FFmpeg 合併影片和音訊"""
    ffmpeg_path = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'bin', 'ffmpeg.exe')  # 指定 ffmpeg 的完整路徑
    ffmpeg_command = [
        ffmpeg_path, '-i', video_path, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', output_path
    ]
    
    process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
    
    total_duration = None
    # 用正規表達式匹配 "Duration: HH:MM:SS.xx"
    duration_pattern = re.compile(r'Duration: (\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)')
    # 用正規表達式匹配 "time=HH:MM:SS.xx"
    time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)')

    for line in process.stderr:
        # 先解析總長度
        if total_duration is None:
            duration_match = duration_pattern.search(line)
            if duration_match:
                hours, minutes, seconds = duration_match.groups()
                total_duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        # 若已取得總長度，解析當前處理進度
        time_match = time_pattern.search(line)
        if time_match and total_duration:
            hours, minutes, seconds = time_match.groups()
            time_in_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            # 合併階段佔總進度的 40%，從 60% 到 100%
            progress = 0.6 + (time_in_seconds / total_duration) * 0.4
            progress = min(progress, 1.0)
            if progress_callback:
                progress_callback(progress)
    
    process.wait()
    if progress_callback:
        progress_callback(0.99)
    logger.info("Merging video and audio completed")
