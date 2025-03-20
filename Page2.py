import os
import re
import time
import functools
import subprocess
from pytubefix import YouTube, Playlist
from logging_config import setup_logger, log_and_show_error
import yt_dlp
import uuid
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

@timeit
def parse_playlist(url, resolution, downloader, file_format="mp4"):
    """
    解析播放清單 URL，若不是播放清單則印出錯誤並回傳空列表；
    否則回傳列表，每筆為影片資料字典，包含 "title", "resolution", "format", "url"。
    若 downloader 為 "yt_dlp"，使用 yt_dlp 解析；若為 "pytubefix"，使用 pytubefix 解析。
    """
    if "list=" not in url:
        return []
    
    playlist = []
    
    if downloader == "yt_dlp":
        logger.info("Using yt_dlp to parse playlist...")
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,  # 取得完整資訊
            'skip_download': True,
            'noplaylist': False,    # 強制解析播放清單
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if "entries" not in info:
            log_and_show_error("No playlist entries found!")
            return []
        for entry in info['entries']:
            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
            playlist.append({
                "title": entry.get("title", "Unknown"),
                "resolution": resolution,
                "format": file_format,
                "url": video_url
            })
        return playlist
    elif downloader == "pytubefix":
        logger.info("Using pytubefix to parse playlist...")
        try:
            pl = Playlist(url)
        except Exception as e:
            log_and_show_error(f"Failed to parse playlist (pytubefix): {e}")
            return []
        # 假設 pl.video_urls 回傳所有影片 URL
        for video_url in pl.video_urls:
            try:
                yt_obj = YouTube(video_url)
                title = yt_obj.title
            except Exception as e:
                title = "Unknown"
            playlist.append({
                "title": title,
                "resolution": resolution,
                "format": file_format,
                "url": video_url
            })
        return playlist
    else:
        log_and_show_error("Unknown downloader")
        return []

@timeit
def download_video_audio_playlist(url, resolution, download_path, downloader, file_format):
    temp_id = uuid.uuid4().hex
    if downloader == 'pytubefix':
        logger.info("Using pytubefix to download video...")
        yt_obj = YouTube(url)
        safe_title = sanitize_filename(yt_obj.title)

        if file_format == 'mp4':
            filename = safe_title + ".mp4"
            unique_filename = generate_new_filename(download_path, filename)
            output_path = os.path.join(download_path, unique_filename)
            
            # 將 "1920x1080" 轉換為 "1080p" 供 pytubefix 使用
            if "x" in resolution:
                _, height_str = resolution.split('x')
                new_res = height_str + "p"
            else:
                new_res = resolution

            # 先嘗試選取 mp4 格式的影片串流，再回退到 webm
            video_stream = yt_obj.streams.filter(res=new_res, only_video=True, file_extension='mp4').first()
            video_stream_format = 'mp4'
            if not video_stream:
                video_stream = yt_obj.streams.filter(res=new_res, only_video=True, file_extension='webm').first()
                video_stream_format = 'webm'
                if not video_stream:
                    resolutions = list(set([stream.resolution for stream in yt_obj.streams.filter(adaptive=True, only_video=True) if stream.resolution]))
                    resolutions.sort(key=lambda res: int(res.replace("p", "")) if res and res.replace("p", "").isdigit() else 0, reverse=True)
                    if resolutions:
                        video_stream = yt_obj.streams.filter(res=resolutions[0], only_video=True, file_extension='mp4').first()
                        video_stream_format = 'mp4'
                        if not video_stream:
                            video_stream = yt_obj.streams.filter(res=resolutions[0], only_video=True, file_extension='webm').first()
                            video_stream_format = 'webm'
            # 選取最佳音訊串流：先嘗試 mp4，再回退至 webm
            audio_stream = yt_obj.streams.filter(only_audio=True, file_extension='mp4').order_by('abr').desc().first()
            audio_stream_format = 'mp4'
            if not audio_stream:
                audio_stream = yt_obj.streams.filter(only_audio=True, file_extension='webm').order_by('abr').desc().first()
                audio_stream_format = 'webm'

            if not video_stream or not audio_stream:
                raise ValueError(f"{temp_id} 找不到對應的影片或音訊流！")
            
            # 根據串流格式決定暫存檔案名稱
            video_temp_filename = f"video_{temp_id}.{video_stream_format}"
            audio_temp_filename = f"audio_{temp_id}.{audio_stream_format}"
            video_temp_path = os.path.join(download_path, video_temp_filename)
            audio_temp_path = os.path.join(download_path, audio_temp_filename)

            logger.info(f"{temp_id} 正在下載影片...")
            video_stream.download(output_path=download_path, filename=video_temp_filename)
            logger.info(f"{temp_id} 正在下載音訊...")
            audio_stream.download(output_path=download_path, filename=audio_temp_filename)
            logger.info(f"{temp_id} 正在合併影片與音訊...")
            merge_video_audio(video_temp_path, audio_temp_path, output_path)

            logger.info(f"{temp_id} 清理暫存檔案...")
            if os.path.exists(video_temp_path):
                os.remove(video_temp_path)
            if os.path.exists(audio_temp_path):
                os.remove(audio_temp_path)
            return output_path
            
        elif file_format == 'mp3':
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

            # 準備檔名與輸出路徑
            filename = safe_title + ".mp3"
            unique_filename = generate_new_filename(download_path, filename)
            unique_filename = generate_new_filename(download_path, filename)
            output_path = os.path.join(download_path, unique_filename)

            audio_stream_format = matching_stream.subtype if hasattr(matching_stream, "subtype") else matching_stream.mime_type.split('/')[-1]
            audio_temp_filename = f"audio_{temp_id}.{audio_stream_format}"
            audio_temp_path = os.path.join(download_path, audio_temp_filename)
            

            logger.info("正在下載音訊...")
            matching_stream.download(output_path=download_path, filename=audio_temp_filename)
            
            logger.info("正在轉換音訊格式...")
            ffmpeg_path = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'bin', 'ffmpeg.exe')
            ffmpeg_command = [
                ffmpeg_path, '-i', audio_temp_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '2', output_path
            ]
            process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, encoding='utf-8', errors='replace',
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            process.wait()
            if os.path.exists(audio_temp_path):
                os.remove(audio_temp_path) 
            return output_path

    elif downloader == 'yt_dlp':
        logger.info("Using yt_dlp to download video...")
        if file_format == 'mp4':
            try:
                width_str, height_str = resolution.split('x')
                width = int(width_str)
                height = int(height_str)
                # 當高度為 720，且寬度接近 1280，則修正為 1280
                if height == 720 and abs(width - 1280) <= 20:
                    width = 1280
            except Exception as e:
                raise ValueError("解析解析度失敗，請檢查格式是否正確(例如 '1920x1080')") from e
            
            # 先取得影片格式資訊，不下載影片
            with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True, 'noplaylist': True}) as ydl:
                info_pre = ydl.extract_info(url, download=False)
            available_resolutions = {stream.get('resolution') for stream in info_pre.get('formats', []) if stream.get('resolution')}
            if resolution in available_resolutions:
                format_str = f'bestvideo[ext=webm][width={width}][height={height}]+bestaudio[ext=webm]/best[ext=webm]'
            else:
                format_str = "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]"

            temp_template = os.path.join(download_path, f"temp_download_{temp_id}.%(ext)s")
            ydl_opts = {
                'format': format_str,
                'outtmpl': temp_template,
                'noplaylist': True,
                'merge_output_format': 'mp4',
                'postprocessor_args': ['-c:a', 'aac'],  # 強制使用 aac 音訊編碼
            }
        elif file_format == 'mp3':
            temp_template = os.path.join(download_path, f"temp_download_{temp_id}.%(ext)s")
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
        temp_filepath = os.path.join(download_path, f"temp_download_{temp_id}.{output_ext}")
        # 重新命名暫存檔案
        os.rename(temp_filepath, final_filepath)
        
        return final_filepath
    
@timeit
def merge_video_audio(video_path, audio_path, output_path):
    """使用 FFmpeg 合併影片和音訊"""
    ffmpeg_path = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'bin', 'ffmpeg.exe')  # 指定 ffmpeg 的完整路徑
    ffmpeg_command = [
        ffmpeg_path, '-i', video_path, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', output_path
    ]
    
    process = subprocess.Popen(
    ffmpeg_command,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=subprocess.CREATE_NO_WINDOW
    )
    process.wait()
    logger.info(f"合併完成！")