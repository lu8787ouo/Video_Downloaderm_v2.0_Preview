'''
ver2.0
'''

import customtkinter as ctk
from customtkinter import CTkImage
from tkinter import filedialog, messagebox
from PIL import Image, ImageOps
import requests
import threading
import io
import os
from CTkTable import CTkTable
from logging_config import setup_logger, log_and_show_error
from Page1 import get_video_info, download_video_audio
from Page2 import parse_playlist, download_video_audio_playlist
from Page3 import convert_video, convert_audio, get_media_duration, time_to_seconds
from config_manager import load_config, save_config
from rich import print
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess

# ------------------------------
# 初始化 Logger
# ------------------------------
logger = setup_logger(__name__)

# ------------------------------
# 語言設定資料
# ------------------------------     
LANGUAGES = {
    "zh": {  # 繁體中文
        # Setting window
        "setting_title": "設定",
        "theme_label": "主題",
        "language_label": "選擇語言",
        "resolution_label": "視窗大小",
        # HomePage
        "title_label": "Video DownloadErm",
        # Page1
        "page1_title": "單影片下載",
        "url_entry_placeholder": "請輸入 YouTube 影片網址",
        "submit_button": "提交",
        "download_path_label": "下載位置:",
        "browse_button": "瀏覽",
        "downloader_label": "下載器選擇",
        "download_sub_checkbox": "下載字幕",
        "no_ad_label": "廣告放置區，但是沒有廣告 (歡迎自訂廣告)",
        "progress_ready": "準備就緒",
        "download_button": "下載影片",
        # Page2
        "page2_title": "清單下載",
        "playlist_url_label": "請輸入 YouTube 播放清單網址:",
        "select_all": "全選",
        "delete_selected": "刪除選取列",
        "video_title": "影片名稱",
        "resolution": "解析度",
        "format": "格式",
        "url": "影片網址",
        # Page3
        "page3_title": "影音轉檔器",
        "select_files_label": "選擇檔案",
        "browse_button": "瀏覽",
        "converted_files_label": "轉檔後檔案",
        "open_button": "開啟",
        "start_time_label": "開始時間:",
        "end_time_label": "結束時間:",
        "video_radio": "影片",
        "audio_radio": "音訊",
        "resolution_label": "解析度",
        "target_format_label": "目標格式",
        "video_transcoder_label": "影片轉碼器",
        "audio_transcoder_label": "音訊轉碼器",
        "convert_button": "轉檔",
        "progress_ready": "準備就緒",
        # Pages 4
        "page4_title": "測試",
        # Pages 2~4
        "page2_label": "頁面 2",
        "page3_label": "頁面 3",
        "page4_label": "頁面 4",
        "back_home_button": "返回主頁",
    },
    "en": {  # 英文
        # Setting window
        "setting_title": "Setting",
        "theme_label": "Theme",
        "language_label": "Language",
        "resolution_label": "Window Size",
        # HomePage
        "title_label": "Video DownloadErm",
        # Page1
        "page1_title": "Video Download",
        "url_entry_placeholder": "Enter YouTube video URL",
        "submit_button": "Submit",
        "download_path_label": "Download path:",
        "browse_button": "Browse",
        "downloader_label": "Downloader",
        "download_sub_checkbox": "Download Subtitles",
        "no_ad_label": "Ad space (no ad here)",
        "progress_ready": "Ready",
        "download_button": "Download",
        # Page2
        "page2_title": "Playlist Download",
        "playlist_url_label": "Enter YouTube Playlist URL:",
        "select_all": "Select All",
        "delete_selected": "Delete Selected",
        "video_title": "Video Title",
        "resolution": "Resolution",
        "format": "Format",
        "url": "Video URL",
        # Pages 3
        "page3_title": "Media Converter",
        "select_files_label": "Select Files",
        "browse_button": "Browse",
        "converted_files_label": "Converted Files",
        "open_button": "Open",
        "start_time_label": "Start Time:",
        "end_time_label": "End Time:",
        "video_radio": "Video",
        "audio_radio": "Audio",
        "resolution_label": "Resolution",
        "target_format_label": "Target Format",
        "video_transcoder_label": "Video Transcoder",
        "audio_transcoder_label": "Audio Transcoder",
        "convert_button": "Convert",
        "progress_ready": "Ready",
        # Pages 4
        "page4_title": "test",
        # Pages 2~4
        "page2_label": "Page 2",
        "page3_label": "Page 3",
        "page4_label": "Page 4",
        "back_home_button": "Back to Home",
    }
}

LANGUAGE_OPTIONS = {
    "zh": "中文",
    "en": "English"
}

# ------------------------------
# 設定視窗
# ------------------------------
class Setting(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title(LANGUAGES[self.master.current_language]["setting_title"])
        self.geometry("300x450")
        self.resizable(False, False)
        
        self.grid_columnconfigure((0,1), weight=1)
        self.grid_rowconfigure((0, 1, 2, 3), weight=1)
        
        self.theme_label = ctk.CTkLabel(self, text=LANGUAGES[self.master.current_language]["theme_label"])
        self.theme_label.grid(row=0, column=0, pady=10, sticky="ew")
        self.theme_combobox = ctk.CTkComboBox(self, values=["Light", "Dark"], command=self.change_theme)
        self.theme_combobox.grid(row=0, column=1, pady=10, sticky="ew")
        self.theme_combobox.set(self.master.config.get("theme", "Dark")) # 預設值
        
        self.language_label = ctk.CTkLabel(self, text=LANGUAGES[self.master.current_language]["language_label"])
        self.language_label.grid(row=1, column=0, pady=10, sticky="ew")
        self.language_combobox = ctk.CTkComboBox(self, values=["中文", "English"], command=self.change_language)
        self.language_combobox.grid(row=1, column=1, pady=10, sticky="ew")
        self.language_combobox.set(LANGUAGE_OPTIONS[self.master.config.get("language", "zh")])
        
        self.resolution_label = ctk.CTkLabel(self, text=LANGUAGES[self.master.current_language]["resolution_label"])
        self.resolution_label.grid(row=2, column=0, pady=10, sticky="ew")
        self.resolution_combobox = ctk.CTkComboBox(self, values=["1920x1080", "1280x720"], command=self.change_resolution)
        self.resolution_combobox.grid(row=2, column=1, pady=10, sticky="ew")
        self.resolution_combobox.set(self.master.config.get("resolution", "1280x720")) # 預設值

        self.ad_label = ctk.CTkLabel(self, text=LANGUAGES[self.master.current_language].get("ad_label", "廣告圖片設定"))
        self.ad_label.grid(row=3, column=0, pady=10, sticky="ew")
        self.ad_button = ctk.CTkButton(self, text=LANGUAGES[self.master.current_language].get("ad_button", "匯入圖片"), command=self.import_ad_image)
        self.ad_button.grid(row=3, column=1, padx=10, pady=2, sticky="w")
    
    def change_theme(self, choice):
        ctk.set_appearance_mode(choice)
        self.master.config["theme"] = choice
        save_config(self.master.config)
        self.master.update_theme()
        self.update_text()

    def change_language(self, choice):
        if choice == "中文":
            self.master.current_language = "zh"
        else:
            self.master.current_language = "en"
        self.master.config["language"] = self.master.current_language
        save_config(self.master.config)
        self.master.update_language()
        self.update_text()

    def change_resolution(self, choice):
        self.master.geometry(choice)
        self.master.config["resolution"] = choice
        save_config(self.master.config)

    def import_ad_image(self):
        # 讓使用者選擇圖片檔案，限定 jpg、jpeg、png 與 gif 格式
        file_path = filedialog.askopenfilename(
            title="選擇廣告圖片",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.gif")]
        )
        if file_path:
            # 儲存選擇的圖片路徑到 config 中
            self.master.config["ad_image"] = file_path
            # 儲存設定到 JSON 檔案（假設 save_config 已定義）
            save_config(self.master.config)
            # 更新廣告區畫面（會根據圖片自動等比例縮放）
            self.master.frames[Page1].update_ad_area()

    def update_text(self):
        self.title(LANGUAGES[self.master.current_language]["setting_title"])
        self.theme_label.configure(text=LANGUAGES[self.master.current_language]["theme_label"])
        self.language_label.configure(text=LANGUAGES[self.master.current_language]["language_label"])
        self.resolution_label.configure(text=LANGUAGES[self.master.current_language]["resolution_label"])


# ------------------------------
# 主視窗
# ------------------------------

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        # 讀取設定檔
        self.config = load_config()
        # 從設定檔中取得設定，若無則採用預設值
        self.current_language = self.config.get("language", "zh")
        self.current_theme = self.config.get("theme", "Dark")
        resolution = self.config.get("resolution", "1280x720")
        self.download_path = self.config.get("download_path", os.getcwd())

        ctk.set_appearance_mode(self.current_theme)
        self.title("Video DownloadErm")
        icon_path = os.path.join(os.path.dirname(__file__), 'icon/icon.ico')
        self.iconbitmap(icon_path)
        self.geometry(resolution)
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frames = {}
        for Page in (HomePage, Page1, Page2, Page3, Page4):
            page = Page(self)
            self.frames[Page] = page
            page.grid(row=0, column=0, sticky="nsew")

        self.show_frame(HomePage)
        self.setting_window = None

    def show_frame(self, page):
        frame = self.frames[page]
        frame.tkraise()
    
    def open_Setting(self):
        if self.setting_window is None or not self.setting_window.winfo_exists():
            self.setting_window = Setting(self)  # create window if its None or destroyed
            self.after(300, lambda: self.setting_window.focus()) # focus the window
        else:
            self.setting_window.focus()  # if window exists focus it

    def update_theme(self):
        """
        被 Setting 視窗呼叫，用來更新整個主視窗以及所有 Page 裏頭的文字顏色。
        """
        if self.setting_window is not None and self.setting_window.winfo_exists():
            self.setting_window.update_text()

        # 再來更新每一個 Page 的文字
        for page_class, page_obj in self.frames.items():
            page_obj.update_text()
    
    def update_language(self):
        """
        被 Setting 視窗呼叫，用來更新整個主視窗以及所有 Page 裏頭的文字。
        """
        # 先更新 Setting 視窗本身 (如果存在)
        if self.setting_window is not None and self.setting_window.winfo_exists():
            self.setting_window.update_text()

        # 再來更新每一個 Page 的文字
        for page_class, page_obj in self.frames.items():
            page_obj.update_text()

class HomePage(ctk.CTkFrame):  # 主页
    def __init__(self, master):
        super().__init__(master)

        self.grid_columnconfigure((0,1), weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=3)
        self.grid_rowconfigure((2,3), weight=3)

        edit_icon = ctk.CTkButton(self, text="\U00002699", width=50, command=master.open_Setting, fg_color="transparent", hover_color=("black"), border_width=0)
        edit_icon.grid(row=0, column=1, padx=5, sticky="e")

        # 這些文字將在 update_text() 時再行設定
        self.logo_label = ctk.CTkLabel(self, font=("Arial", 28))
        self.logo_label.grid(row=1, column=0, pady=5, columnspan=2, sticky="nsew")

        self.btn1 = ctk.CTkButton(
            self,
            command=lambda: master.show_frame(Page1),
            corner_radius=12,  # 圓角
            fg_color=("#4a90e2", "#1c4966"),  # 明暗主題雙色
            hover_color=("#367abd", "#2b7a99"),  # 滑鼠懸停色
            font=("Arial", 16)
        )
        self.btn1.grid(row=2, column=0, padx=20, pady=5)

        self.btn2 = ctk.CTkButton(
            self, 
            command=lambda: master.show_frame(Page2),
            corner_radius=12,  # 圓角
            fg_color=("#4a90e2", "#1c4966"),  # 明暗主題雙色
            hover_color=("#367abd", "#2b7a99"),  # 滑鼠懸停色
            font=("Arial", 16)
        )
        self.btn2.grid(row=2, column=1, padx=20, pady=5)

        self.btn3 = ctk.CTkButton(
            self, 
            command=lambda: master.show_frame(Page3),
            corner_radius=12,  # 圓角
            fg_color=("#4a90e2", "#1c4966"),  # 明暗主題雙色
            hover_color=("#367abd", "#2b7a99"),  # 滑鼠懸停色
            font=("Arial", 16)
        )
        self.btn3.grid(row=3, column=0, padx=20, pady=5)

        self.btn4 = ctk.CTkButton(
            self, 
            command=lambda: master.show_frame(Page4),
            corner_radius=12,  # 圓角
            fg_color=("#4a90e2", "#1c4966"),  # 明暗主題雙色
            hover_color=("#367abd", "#2b7a99"),  # 滑鼠懸停色
            font=("Arial", 16)
        )
        self.btn4.grid(row=3, column=1, padx=20, pady=5)

        # 初始化
        self.update_logo_area()
        self.update_text()

    def update_logo_area(self):
        """依據 config 中廣告圖片的設定更新廣告區"""
        icon_path = os.path.join(os.path.dirname(__file__), 'icon/icon_r.png')
        if icon_path and os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                # 使用 ImageOps.contain 使圖片在範圍內等比例縮放
                img = ImageOps.contain(img, (360, 240))
                # 以縮放後的尺寸建立 CTkImage
                self.logo_image = CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                self.logo_label.configure(image=self.logo_image, text="", compound="left", padx=15)
            except Exception as e:
                log_and_show_error(f"Logo image load failed: {e}", self.master)
                self.logo_label.configure(text=LANGUAGES[self.master.current_language]["title_label"], image=None)
        else:
            # 無圖片則顯示預設文字
            self.logo_label.configure(text=LANGUAGES[self.master.current_language]["title_label"], image=None)

    def update_text(self):
        lang = self.master.current_language
        self.update_logo_area()
        self.logo_label.configure(text=LANGUAGES[lang]['title_label'])
        self.btn1.configure(text=f"🎬 {LANGUAGES[lang]['page1_title']}")
        self.btn2.configure(text=f"📋 {LANGUAGES[lang]['page2_title']}")
        self.btn3.configure(text=f"🎞️ {LANGUAGES[lang]['page3_title']}")
        self.btn4.configure(text=f"📄 {LANGUAGES[lang]['page4_title']}")

class Page1(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        self.download_path = self.master.config.get("download_path") or os.getcwd()
        self.video_url = ""
        
        # 設定 Grid 權重
        self.grid_columnconfigure(0, weight=7)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1) 
        self.grid_rowconfigure(1, weight=2) 
        self.grid_rowconfigure(2, weight=5)
        self.grid_rowconfigure(3, weight=2)

        text_color = "black" if self.master.config.get("theme", "Dark") == "Light" else "white"

        # ====== 頁面頂部 ======
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.grid(row=0, column=0, sticky="nsew", columnspan=2, padx=5)
        self.frame_top.grid_rowconfigure(0, weight=1)
        self.frame_top.grid_columnconfigure((0,2), weight=1)
        self.frame_top.grid_columnconfigure(1, weight=8)

        self.back_icon = ctk.CTkButton(
            self.frame_top, 
            text="\U00002190", 
            width=50, 
            command=lambda: master.show_frame(HomePage),
            fg_color="transparent",
            text_color=text_color, 
            border_width=0, 
            border_spacing=0, 
            corner_radius=2
        )
        self.back_icon.grid(row=0, column=0, padx=5, sticky="w")

        self.page_title = ctk.CTkLabel(self.frame_top)
        self.page_title.grid(row=0, column=1, padx=5, sticky="ew")

        self.edit_icon = ctk.CTkButton(
            self.frame_top, 
            text="\U00002699", 
            width=50, 
            command=master.open_Setting,
            fg_color="transparent", 
            text_color=text_color,
            border_width=0, 
            border_spacing=0, 
            corner_radius=2
        )
        self.edit_icon.grid(row=0, column=2, padx=5, sticky="e")
        
        # ====== 左側 Frame（影片資訊 & 下載選項）======
        self.frame_left = ctk.CTkFrame(self)
        self.frame_left.grid(row=1, column=0, sticky="nsew", rowspan=2, padx=5, pady=5)
        self.frame_left.grid_rowconfigure(0, weight=4)
        self.frame_left.grid_rowconfigure((1,2,3), weight=2)
        self.frame_left.grid_columnconfigure(0, weight=2)
        self.frame_left.grid_columnconfigure(1, weight=5)
        self.frame_left.grid_columnconfigure(2, weight=3)
        
        self.thumbnail_label = ctk.CTkLabel(self.frame_left, text="", width=400, height=300)
        self.thumbnail_label.grid(row=0, column=0, columnspan=3, pady=3)
        
        self.video_title_label = ctk.CTkLabel(self.frame_left, wraplength=400, text="")
        self.video_title_label.grid(row=1, column=0, columnspan=3, pady=1)
        
        self.resolution_combobox = ctk.CTkComboBox(self.frame_left, values=["No resolutions"])
        self.resolution_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        self.format_var = ctk.StringVar(value="mp4")
        self.radio_mp4 = ctk.CTkRadioButton(self.frame_left, text="MP4", variable=self.format_var, value="mp4")
        self.radio_mp3 = ctk.CTkRadioButton(self.frame_left, text="MP3", variable=self.format_var, value="mp3")
        self.radio_mp4.grid(row=2, column=2, padx=30, pady=5, sticky="w")
        self.radio_mp3.grid(row=3, column=2, padx=30, pady=5, sticky="w")
        
        self.subtitle_combobox = ctk.CTkComboBox(self.frame_left, values=["No subtitle"])
        self.subtitle_combobox.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.subtitle_combobox.grid_remove()  # 隱藏字幕選項
        
        # ====== 右側 Frame（URL 輸入 & 下載位置）======
        # 上半部分
        self.frame_first_right = ctk.CTkFrame(self)
        self.frame_first_right.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self.frame_first_right.grid_rowconfigure((0,1,2), weight=1)
        self.frame_first_right.grid_columnconfigure(0, weight=8)
        self.frame_first_right.grid_columnconfigure(1, weight=2)
        
        self.url_entry = ctk.CTkEntry(self.frame_first_right)
        self.url_entry.grid(row=0, column=0, padx=10, pady=2, sticky="ew")
        
        self.submit_button = ctk.CTkButton(self.frame_first_right, command=self.fetch_video_info)
        self.submit_button.grid(row=0, column=1, padx=10, pady=2, sticky="w")
        
        self.download_path_textbox = ctk.CTkTextbox(self.frame_first_right, height=30, activate_scrollbars=False)
        self.download_path_textbox.configure(state="disabled")
        self.download_path_textbox.grid(row=1, column=0, padx=10, pady=2, sticky="ew")
        
        self.change_path_button = ctk.CTkButton(self.frame_first_right, command=self.change_download_path)
        self.change_path_button.grid(row=1, column=1, padx=10, pady=2, sticky="w")

        self.downloader_label = ctk.CTkLabel(self.frame_first_right)
        self.downloader_label.grid(row=2, column=0, padx=10, pady=2, sticky="w")

        self.downloader_combobox = ctk.CTkComboBox(self.frame_first_right, values=["pytubefix","yt_dlp"])
        self.downloader_combobox.grid(row=2, column=0, padx=0, pady=2)

        self.download_sub_var = ctk.BooleanVar(value=False)
        self.download_sub_checkbox = ctk.CTkCheckBox(
            self.frame_first_right, 
            variable=self.download_sub_var, 
            command=self.toggle_subtitle_combobox
        )
        self.download_sub_checkbox.grid(row=2, column=1, padx=10, pady=2, sticky="w")

        # ====== 右下 Frame（廣告區）======
        self.frame_second_right = ctk.CTkFrame(self)
        self.frame_second_right.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)
        self.frame_second_right.grid_propagate(False)  # 固定 frame 尺寸
        self.frame_second_right.grid_rowconfigure(0, weight=1)
        self.frame_second_right.grid_columnconfigure(0, weight=1)

        self.ad_label = ctk.CTkLabel(self.frame_second_right, text=LANGUAGES[self.master.current_language]["no_ad_label"])
        self.ad_label.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # ====== 底部 Frame ======
        self.frame_bottom = ctk.CTkFrame(self)
        self.frame_bottom.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.frame_bottom.grid_rowconfigure(0, weight=4)
        self.frame_bottom.grid_rowconfigure(1, weight=6)
        self.frame_bottom.grid_columnconfigure(0, weight=7)
        self.frame_bottom.grid_columnconfigure(1, weight=3)

        self.progress_bar_label = ctk.CTkLabel(self.frame_bottom)
        self.progress_bar_label.grid(row=0, column=0, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(self.frame_bottom)
        self.progress_bar.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.progress_bar.set(0)

        self.download_button = ctk.CTkButton(self.frame_bottom, command=self.download_video)
        self.download_button.grid(row=1, column=1, pady=5)
        
        self.update_text() # 初始化文字
        self.update_ad_area() # 初始化廣告區
        
    def toggle_subtitle_combobox(self):
        if self.download_sub_var.get():
            self.subtitle_combobox.grid()  # 顯示字幕下拉選單
        else:
            self.subtitle_combobox.grid_remove()  # 隱藏字幕下拉選單

    def fetch_video_info(self):
        """獲取影片資訊並更新 UI"""
        url = self.url_entry.get()
        if not url:
            return
        
        self.video_url = url
        title, thumbnail_url, resolutions, subtitles = get_video_info(url, self.downloader_combobox.get(), self.format_var.get())
        
        self.video_title_label.configure(text=title)
        self.resolution_combobox.configure(values=resolutions)
        if resolutions:
            self.resolution_combobox.set(resolutions[0])
        else:
            self.resolution_combobox.set("No resolutions")

        # 更新字幕選項：若無字幕僅顯示 "No subtitle"，有的則加入各語系選項
        self.subtitle_combobox.configure(values=subtitles)
        self.subtitle_combobox.set(subtitles[0])
        
        # 更新封面圖
        response = requests.get(thumbnail_url)
        img_data = Image.open(io.BytesIO(response.content))
        self.thumbnail_image = CTkImage(light_image=img_data, dark_image=img_data, size=(400, 300))  # 這樣就能適應高DPI螢幕
        self.thumbnail_label.configure(image=self.thumbnail_image, text="")

    def update_progress(self, progress):
        lang = self.master.current_language
        if progress != -1:
            percent = int(progress * 100)
            # 使用 after 確保 GUI 更新在主執行緒中執行
            self.master.after(0, lambda: self.progress_bar.set(progress))
            if lang == "en":
                self.master.after(0, lambda: self.progress_bar_label.configure(text=f"Processing: {percent}%"))
            elif lang == "zh":
                self.master.after(0, lambda: self.progress_bar_label.configure(text=f"處理中: {percent}%"))
        else:
            self.master.after(100, lambda: self.progress_bar.set(progress))
            if lang == "en":
                self.master.after(0, lambda: self.progress_bar_label.configure(text="Processing completed"))
            elif lang == "zh": 
                self.master.after(0, lambda: self.progress_bar_label.configure(text="處理完成"))

    def download_video(self):
        """開始下載影片，使用 threading 執行下載任務"""
        self.download_button.configure(state="disabled")
        resolution = self.resolution_combobox.get()
        downloader = self.downloader_combobox.get()
        file_format = self.format_var.get()
        download_subtitles = self.download_sub_var.get()
        subtitle_lang = self.subtitle_combobox.get()

        def download_task():
            # 呼叫 yt_dlp 的 Python API 進行下載
            output_file = download_video_audio(
                self.video_url, resolution, self.download_path,
                downloader, file_format, download_subtitles,
                subtitle_lang, self.update_progress
            )
            logger.info(f"Download Completed: {output_file}")

            # 回到主執行緒後重新啟用下載按鈕
            self.master.after(0, lambda: self.download_button.configure(state="normal"))

        # 建立並啟動下載執行緒
        download_thread = threading.Thread(target=download_task)
        download_thread.start()

    def change_download_path(self):
        """變更下載位置"""
        lang = self.master.current_language
        path = filedialog.askdirectory()
        if path:
            self.download_path = path
            self.master.config["download_path"] = path
            save_config(self.master.config)

            self.download_path_textbox.configure(state="normal")
            self.download_path_textbox.delete("0.0", "end")
            if lang == "en":
                self.download_path_textbox.insert("0.0", f"Download path: {self.download_path}")
            elif lang == "zh":
                self.download_path_textbox.insert("0.0", f"下載位置: {self.download_path}")
            self.download_path_textbox.configure(state="disabled")

    def update_ad_area(self):
        """依據 config 中廣告圖片的設定更新廣告區"""
        ad_image_path = self.master.config.get("ad_image", "")
        if ad_image_path and os.path.exists(ad_image_path):
            try:
                img = Image.open(ad_image_path)
                # 使用 ImageOps.contain 使圖片在範圍內等比例縮放
                img = ImageOps.contain(img, (640, 480))
                # 以縮放後的尺寸建立 CTkImage
                self.ad_image = CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                # 顯示圖片，隱藏文字
                self.ad_label.configure(image=self.ad_image, text="")
            except Exception as e:
                log_and_show_error(f"AD image load failed: {e}", self.master)
                self.ad_label.configure(text=LANGUAGES[self.master.current_language]["no_ad_label"], image=None)
        else:
            # 無圖片則顯示預設文字
            self.ad_label.configure(text=LANGUAGES[self.master.current_language]["no_ad_label"], image=None)

    def update_text(self):
        """切換語言後，更新本頁所有文字。"""
        lang = self.master.current_language
        self.page_title.configure(text=LANGUAGES[lang]["page1_title"])
        self.url_entry.configure(placeholder_text=LANGUAGES[lang]["url_entry_placeholder"])
        self.submit_button.configure(text=LANGUAGES[lang]["submit_button"])
        
        # 下載路徑 textbox
        self.download_path_textbox.configure(state="normal")
        self.download_path_textbox.delete("0.0", "end")
        self.download_path_textbox.insert("0.0", f"{LANGUAGES[lang]['download_path_label']} {self.download_path}")
        self.download_path_textbox.configure(state="disabled")

        self.change_path_button.configure(text=LANGUAGES[lang]["browse_button"])
        self.downloader_label.configure(text=LANGUAGES[lang]["downloader_label"])
        self.download_sub_checkbox.configure(text=LANGUAGES[lang]["download_sub_checkbox"])
        self.update_ad_area()
        self.progress_bar_label.configure(text=LANGUAGES[lang]["progress_ready"])
        self.download_button.configure(text=LANGUAGES[lang]["download_button"])

        """切換theme後，更新本頁所有文字。"""
        text_color = "black" if self.master.config.get("theme", "Dark") == "Light" else "white"
        self.back_icon.configure(text_color=text_color)
        self.edit_icon.configure(text_color=text_color)
        self.page_title.configure(text_color=text_color)

class Page2(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.download_path = self.master.config.get("download_path") or os.getcwd()
        self.video_url = ""
        
        # 播放清單資料，內部儲存，每筆為 dict
        self.playlist_items = []

        # 設定 Grid 權重
        self.grid_columnconfigure(0, weight=7)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1) 
        self.grid_rowconfigure(1, weight=2) 
        self.grid_rowconfigure(2, weight=5)
        self.grid_rowconfigure(3, weight=2)

        text_color = "black" if self.master.config.get("theme", "Dark") == "Light" else "white"

        # ====== 頁面頂部 ======
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.frame_top.grid_rowconfigure(0, weight=1)
        self.frame_top.grid_columnconfigure((0,2), weight=1)
        self.frame_top.grid_columnconfigure(1, weight=8)
        
        self.back_btn = ctk.CTkButton(
            self.frame_top, 
            text="\U00002190", 
            width=50, 
            command=lambda: master.show_frame(HomePage),
            fg_color="transparent",
            text_color=text_color, 
            border_width=0, 
            border_spacing=0, 
            corner_radius=2
        )
        self.back_btn.grid(row=0, column=0, padx=5, sticky="w")
        
        self.page_title = ctk.CTkLabel(self.frame_top)
        self.page_title.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.edit_btn = ctk.CTkButton(
            self.frame_top, 
            text="\U00002699", 
            width=50, 
            command=master.open_Setting,
            fg_color="transparent", 
            text_color=text_color,
            border_width=0, 
            border_spacing=0, 
            corner_radius=2
        )
        self.edit_btn.grid(row=0, column=2, padx=5, sticky="e")
        
        # ====== 左側 Frame（播放清單表格）======
        self.frame_left_first = ctk.CTkFrame(self)
        self.frame_left_first.grid(row=1, column=0, sticky="nsew", rowspan=2, padx=5, pady=5)
        self.frame_left_first.grid_rowconfigure(0, weight=9)
        self.frame_left_first.grid_rowconfigure(1, weight=1)
        self.frame_left_first.grid_columnconfigure((0,1,2,3,4,5), weight=1)

        self.table_scroll = ctk.CTkScrollableFrame(self.frame_left_first)
        self.table_scroll.grid(row=0, column=0, columnspan=6, sticky="nsew")

        initial_data = [["Video Title", "Resolution", "Format", "URL"]]
        self.table = CTkTable(
            master=self.table_scroll,
            row=len(initial_data),
            column=len(initial_data[0]),
            values=initial_data,
            # header_color="gray25",
            hover_color="skyblue",
            corner_radius=0,
            command=self.on_cell_click
        )
        self.table.pack(padx=10, pady=10, fill="both", expand=True)


        self.select_all_btn = ctk.CTkButton(self.frame_left_first, text="全選", command=self.select_all_rows)
        self.select_all_btn.grid(row=1, column=0, sticky="w", padx=5, pady=1)

        self.delete_btn = ctk.CTkButton(self.frame_left_first, text="刪除選取列", command=self.delete_selected_rows)
        self.delete_btn.grid(row=1, column=1, sticky="w", padx=5, pady=1)
        
        self.total_label = ctk.CTkLabel(self.frame_left_first, text="共 0 筆")
        self.total_label.grid(row=1, column=5, sticky="e", padx=5, pady=1)
        
        # ====== 右上 Frame（URL 輸入 & 下載位置）======
        self.frame_first_right = ctk.CTkFrame(self)
        self.frame_first_right.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self.frame_first_right.grid_rowconfigure((0,1,2,3), weight=1)
        self.frame_first_right.grid_columnconfigure(0, weight=8)
        self.frame_first_right.grid_columnconfigure(1, weight=2)

        self.url_entry = ctk.CTkEntry(self.frame_first_right, placeholder_text="輸入播放清單 URL")
        self.url_entry.grid(row=0, column=0, padx=10, pady=2, sticky="ew")

        self.submit_btn = ctk.CTkButton(self.frame_first_right, text="提交", command=self.add_playlist_item)
        self.submit_btn.grid(row=0, column=1, padx=10, pady=2, sticky="w")

        self.download_path_textbox = ctk.CTkTextbox(self.frame_first_right, height=30, activate_scrollbars=False)
        self.download_path_textbox.configure(state="disabled")
        self.download_path_textbox.grid(row=1, column=0, padx=10, pady=2, sticky="ew")
        
        self.change_path_button = ctk.CTkButton(self.frame_first_right, command=self.change_download_path)
        self.change_path_button.grid(row=1, column=1, padx=10, pady=2, sticky="w")

        self.downloader_combobox = ctk.CTkComboBox(self.frame_first_right, values=["pytubefix","yt_dlp"])
        self.downloader_combobox.grid(row=2, column=0, padx=10, pady=2, sticky="ew")
        
        self.resolution_combobox = ctk.CTkComboBox(self.frame_first_right)
        self.resolution_combobox.grid(row=3, column=0, padx=10, pady=2, sticky="ew")
        
        self.format_var = ctk.StringVar(value="mp4")
        self.mp4_radio = ctk.CTkRadioButton(self.frame_first_right, text="MP4", variable=self.format_var, value="mp4")
        self.mp3_radio = ctk.CTkRadioButton(self.frame_first_right, text="MP3", variable=self.format_var, value="mp3")
        self.mp4_radio.grid(row=2, column=1, padx=10, pady=2)
        self.mp3_radio.grid(row=3, column=1, padx=10, pady=2)

        # 監聽 self.format_var 的變化，當格式改變時自動更新 resolution_combobox 的選項
        self.format_var.trace_add('write', lambda *args: self.update_resolution_options())

        # ====== 右下 Frame（廣告區）======
        self.frame_second_right = ctk.CTkFrame(self)
        self.frame_second_right.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)
        self.frame_second_right.grid_propagate(False)  # 固定 frame 尺寸
        self.frame_second_right.grid_rowconfigure(0, weight=1)
        self.frame_second_right.grid_columnconfigure(0, weight=1)

        self.ad_label = ctk.CTkLabel(self.frame_second_right, text=LANGUAGES[self.master.current_language]["no_ad_label"])
        self.ad_label.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        # ====== 底部 Frame ======
        self.frame_bottom = ctk.CTkFrame(self)
        self.frame_bottom.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.frame_bottom.grid_rowconfigure(0, weight=4)
        self.frame_bottom.grid_rowconfigure(1, weight=6)
        self.frame_bottom.grid_columnconfigure(0, weight=7)
        self.frame_bottom.grid_columnconfigure(1, weight=3)

        self.progress_bar_label = ctk.CTkLabel(self.frame_bottom)
        self.progress_bar_label.grid(row=0, column=0, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(self.frame_bottom)
        self.progress_bar.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.progress_bar.set(0)

        self.download_button = ctk.CTkButton(self.frame_bottom, command=self.download_playlist)
        self.download_button.grid(row=1, column=1, pady=5)

        self.update_text() # 初始化文字
        self.update_resolution_options() # 初始化解析度選項
        self.update_ad_area() # 初始化廣告區
        
    def set_fixed_column_widths(self, widths):
        """
        設定表格每一欄的寬度。
        widths: 一個列表，每個元素代表對應欄的固定寬度（像素）。
        例如: [300, 100, 80, 400]
        """
        for (row, col), cell in self.table.frame.items():
            if col in widths:
                # 設定固定寬度，同時設定 wraplength 避免文字溢出
                cell.configure(width=widths[col])

    def update_table_header(self):
        lang = self.master.current_language
        # 根據語系設定表頭
        header = [
            LANGUAGES[lang]["video_title"],
            LANGUAGES[lang]["resolution"],
            LANGUAGES[lang]["format"],
            LANGUAGES[lang]["url"]
        ]
        # 根據主題決定表頭背景色，這裡以 Light 主題用淺灰、Dark 主題用深灰為例
        header_color = "gray90" if self.master.config.get("theme", "Dark") == "Light" else "gray25"
        # 更新表頭每個 cell 的文字與背景色
        for col in range(len(header)):
            if (0, col) in self.table.frame:
                self.table.frame[(0, col)].configure(text=header[col], fg_color=header_color)
        self.set_fixed_column_widths([400, 200, 100, 100])

    def update_total_label(self):
        lang = self.master.current_language
        total = len(self.playlist_items)
        if lang == "en":
            self.total_label.configure(text=f"Total {total} items")
        elif lang == "zh":
            self.total_label.configure(text=f"共 {total} 筆")

    def update_resolution_options(self):
        if self.format_var.get() == "mp3":
            # 當選擇 mp3 時，提供預設的音訊品質選項
            new_options = ["320kbps", "256kbps", "192kbps", "128kbps", "64kbps"]
            self.resolution_combobox.configure(values=new_options)
            # 例如預設使用最高品質
            self.resolution_combobox.set("320kbps")
        else:
            # 當選擇 mp4 時，使用影片解析度選項
            new_options = ["4320x2160", "3840x2160", "2560x1440", "1920x1080", "1280x720", "854x480",
                           "640x360", "426x240", "256x144"]
            self.resolution_combobox.configure(values=new_options)
            self.resolution_combobox.set("4320x2160")

    def add_playlist_item(self):
        """解析播放清單 URL，並將解析到的影片資料插入表格與內部清單中，使用線程執行並禁用提交按鈕"""
        self.submit_btn.configure(state="disabled")
        url = self.url_entry.get().strip()
        if not url:
            self.submit_btn.configure(state="normal")
            return
        # 檢查是否為播放清單 URL
        if "list=" not in url:
            log_and_show_error("Invalid playlist URL", self.master)
            self.submit_btn.configure(state="normal")
            return

        def task():
            items = parse_playlist(url, self.resolution_combobox.get(), self.downloader_combobox.get(), self.format_var.get())
            if not items:
                log_and_show_error("Failed to parse playlist or no videos found!", self.master)
                # 回到主執行緒重新啟用提交按鈕
                self.master.after(0, lambda: self.submit_btn.configure(state="normal"))
                return
            # 將解析到的資料加入內部清單
            for item in items:
                self.playlist_items.append(item)
            # 在主執行緒中更新 UI（因為 Tkinter 介面更新必須在主執行緒中進行）
            def update_ui():
                for item in items:
                    self.table.add_row([item["title"], item["resolution"], item["format"], item["url"]])
                self.update_total_label()
                self.update_table_header()
                self.submit_btn.configure(state="normal")
            self.master.after(0, update_ui)

        threading.Thread(target=task).start()


    def get_selected_rows(self):
        selected_rows = []
        for i in range(self.table.rows):
            # 依照你的設計，這邊只要檢查每行的第 1 欄是否 == hover_color 即可
            if self.table.frame[i, 1].cget("fg_color") == self.table.hover_color:
                selected_rows.append(i)
        return selected_rows

    def select_all_rows(self):
        """
        遍歷表格中除第一列（表頭）以外的所有列，呼叫 select_row() 使其選取
        """
        selected_rows = self.get_selected_rows()
        if len(selected_rows) == self.table.rows - 1:
            # 如果所有列都已選取，則取消選取所有列
            for row in range(1, self.table.rows):
                self.table.deselect_row(row)
        else:
            # 假設 self.table.rows 回傳表格總列數，且第0列為表頭
            for row in range(1, self.table.rows):
                self.table.select_row(row)

    def delete_selected_rows(self):
        """刪除表格中選取的列，並從內部清單中移除"""
        selected = self.get_selected_rows()  # 假設此方法回傳選取列索引列表
        for index in sorted(selected, reverse=True):
            self.table.delete_row(index)
            del self.playlist_items[index-1]
        self.update_total_label()

    def on_cell_click(self, cell_data):
        """
        當使用者點擊儲存格時呼叫。
        cell_data 格式：
        {
            "row": <列號>,
            "column": <欄號>,
            "value": <該儲存格文字內容>,
            "args": <其他設定參數>
        }
        """
        row_index = cell_data["row"]
        if row_index == 0:
            # 如果點擊的是表頭，則不做任何事
            return
        # 檢查該 row 是否已經被選取：只要比對第二欄的 fg_color 是不是 hover_color
        is_selected = (self.table.frame[row_index, 1].cget("fg_color") == self.table.hover_color)

        if is_selected:
            # 如果已選取，則切換成「取消」
            self.table.deselect_row(row_index)
        else:
            # 如果還沒被選取，就「選取」
            self.table.select_row(row_index)

        # 顯示目前已被選取的所有行
        selected_rows = self.get_selected_rows()

    def change_download_path(self):
        """變更下載位置"""
        lang = self.master.current_language
        path = filedialog.askdirectory()
        if path:
            self.download_path = path
            self.master.config["download_path"] = path
            save_config(self.master.config)

            self.download_path_textbox.configure(state="normal")
            self.download_path_textbox.delete("0.0", "end")
            if lang == "en":
                self.download_path_textbox.insert("0.0", f"Download path: {self.download_path}")
            elif lang == "zh":
                self.download_path_textbox.insert("0.0", f"下載位置: {self.download_path}")
            self.download_path_textbox.configure(state="disabled")

    def update_progress(self, progress):
        lang = self.master.current_language
        if progress != -1:
            percent = int(progress * 100)
            # 使用 after 確保 GUI 更新在主執行緒中執行
            self.master.after(0, lambda: self.progress_bar.set(progress))
            if lang == "en":
                self.master.after(0, lambda: self.progress_bar_label.configure(text=f"Processing: {percent}%"))
            elif lang == "zh":
                self.master.after(0, lambda: self.progress_bar_label.configure(text=f"處理中: {percent}%"))
        else:
            self.master.after(100, lambda: self.progress_bar.set(progress))
            if lang == "en":
                self.master.after(0, lambda: self.progress_bar_label.configure(text="Processing completed"))
            elif lang == "zh": 
                self.master.after(0, lambda: self.progress_bar_label.configure(text="處理完成"))
    
    def download_playlist(self):
        """
        使用 ThreadPoolExecutor 控制同時線程數（例如 5 個）來多線程下載播放清單中所有影片，
        並根據已完成影片數更新進度條。整個流程放入獨立線程中以免阻塞主線程。
        """
        self.download_button.configure(state="disabled")
        total = len(self.playlist_items)
        if total == 0:
            self.download_button.configure(state="normal")
            return

        def download_item(item, idx):
            output_file = download_video_audio_playlist(
                item["url"],
                item["resolution"],
                self.master.download_path,
                self.downloader_combobox.get(),
                item["format"]
            )
            return idx, output_file

        def thread_func():
            completed = 0
            max_threads = 4  # 同時最多執行 4 個下載任務
            self.master.after(0, lambda: self.update_progress(0))
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = [executor.submit(download_item, item, idx)
                        for idx, item in enumerate(self.playlist_items)]
                for future in as_completed(futures):
                    try:
                        idx, output_file = future.result()
                    except Exception as e:
                        log_and_show_error(f"Download failed: {e}", self.master)
                        continue
                    completed += 1
                    progress = completed / total
                    # 更新進度條必須在主線程中執行
                    self.master.after(0, lambda: self.update_progress(progress))
                    logger.info(f"Video {idx} downloaded: {output_file}")
            # 所有任務完成後，回到主線程中重新啟用按鈕與設定進度條
            self.master.after(0, lambda: self.download_button.configure(state="normal"))
            self.master.after(0, lambda: self.update_progress(-1))
            logger.info("All videos downloaded")

        # 將整個 ThreadPoolExecutor 流程放到獨立線程中執行，避免阻塞主線程
        threading.Thread(target=thread_func).start()


    def update_ad_area(self):
        """依據 config 中廣告圖片的設定更新廣告區"""
        ad_image_path = self.master.config.get("ad_image", "")
        if ad_image_path and os.path.exists(ad_image_path):
            try:
                img = Image.open(ad_image_path)
                # 使用 ImageOps.contain 使圖片在範圍內等比例縮放
                img = ImageOps.contain(img, (640, 480))
                # 以縮放後的尺寸建立 CTkImage
                self.ad_image = CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                # 顯示圖片，隱藏文字
                self.ad_label.configure(image=self.ad_image, text="")
            except Exception as e:
                log_and_show_error(f"AD image load failed: {e}", self.master)
                self.ad_label.configure(text=LANGUAGES[self.master.current_language]["no_ad_label"], image=None)
        else:
            # 無圖片則顯示預設文字
            self.ad_label.configure(text=LANGUAGES[self.master.current_language]["no_ad_label"], image=None)

    def update_text(self):
        lang = self.master.current_language
        self.page_title.configure(text=LANGUAGES[lang]["page2_title"])

        self.update_table_header()
        self.select_all_btn.configure(text=LANGUAGES[lang]["select_all"])
        self.delete_btn.configure(text=LANGUAGES[lang]["delete_selected"])
        self.update_total_label()

        self.url_entry.configure(placeholder_text=LANGUAGES[lang]["playlist_url_label"])
        self.submit_btn.configure(text=LANGUAGES[lang]["submit_button"])
        self.download_path_textbox.configure(state="normal")
        self.download_path_textbox.delete("0.0", "end")
        self.download_path_textbox.insert("0.0", f"{LANGUAGES[lang]['download_path_label']} {self.download_path}")
        self.download_path_textbox.configure(state="disabled")
        self.change_path_button.configure(text=LANGUAGES[lang]["browse_button"])
        
        self.update_ad_area()
        
        self.progress_bar_label.configure(text=LANGUAGES[lang]["progress_ready"])
        self.download_button.configure(text=LANGUAGES[lang]["download_button"])
        
        text_color = "black" if self.master.config.get("theme", "Dark") == "Light" else "white"
        self.back_btn.configure(text_color=text_color)
        self.edit_btn.configure(text_color=text_color)
        self.page_title.configure(text_color=text_color)

class Page3(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        
        # 設定區域佈局
        self.grid_rowconfigure(0, weight=1)   # 頂部工具列
        self.grid_rowconfigure(1, weight=8)   # 主區域（左側：檔案選擇；右側：轉換參數）
        self.grid_rowconfigure(2, weight=1)   # 底部進度區
        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=4)

        text_color = "black" if self.master.config.get("theme", "Dark") == "Light" else "white"
        
        # ---------- 頂部工具列 ----------
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.grid(row=0, column=0, sticky="nsew", columnspan=2, padx=5)
        self.frame_top.grid_rowconfigure(0, weight=1)
        self.frame_top.grid_columnconfigure((0,2), weight=1)
        self.frame_top.grid_columnconfigure(1, weight=8)

        self.back_icon = ctk.CTkButton(
            self.frame_top, 
            text="\U00002190", 
            width=50, 
            command=lambda: master.show_frame(HomePage),
            fg_color="transparent",
            text_color=text_color, 
            border_width=0, 
            border_spacing=0, 
            corner_radius=2
        )
        self.back_icon.grid(row=0, column=0, padx=5, sticky="w")

        self.page_title = ctk.CTkLabel(self.frame_top)
        self.page_title.grid(row=0, column=1, padx=5, sticky="ew")

        self.edit_icon = ctk.CTkButton(
            self.frame_top, 
            text="\U00002699", 
            width=50, 
            command=master.open_Setting,
            fg_color="transparent", 
            text_color=text_color,
            border_width=0, 
            border_spacing=0, 
            corner_radius=2
        )
        self.edit_icon.grid(row=0, column=2, padx=5, sticky="e")

        # ---------- 主區域 ----------
        self.frame_main = ctk.CTkFrame(self)
        self.frame_main.grid(row=1, column=0, sticky="nsew", padx=10, pady=10, columnspan=2)
        self.frame_main.grid_rowconfigure((0,1), weight=1)
        self.frame_main.grid_columnconfigure(0, weight=4)
        self.frame_main.grid_columnconfigure(1, weight=6)

        # ---------- 左上：檔案選擇與顯示 ----------
        self.frame_left = ctk.CTkFrame(self.frame_main)
        self.frame_left.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.frame_left.grid_columnconfigure(0, weight=3)
        self.frame_left.grid_columnconfigure(1, weight=3)
        self.frame_left.grid_columnconfigure(2, weight=4)

        self.file_label = ctk.CTkLabel(self.frame_left, text="Select file:")
        self.file_label.grid(row=0, column=0, padx=5, pady=5, columnspan=2, sticky="w")

        self.selected_file = ctk.StringVar(value="")
        self.file_display = ctk.CTkEntry(self.frame_left, textvariable=self.selected_file, state="disabled")
        self.file_display.grid(row=1, column=0, padx=5, pady=5, columnspan=2, sticky="ew")

        self.file_button = ctk.CTkButton(self.frame_left, text="Browse", command=self.browse_file)
        self.file_button.grid(row=1, column=2, padx=5, pady=5, sticky="w")

        self.converted_file_label = ctk.CTkLabel(self.frame_left, text="Converted file:")
        self.converted_file_label.grid(row=2, column=0, padx=5, pady=5, columnspan=2, sticky="w")

        self.converted_file_display = ctk.CTkEntry(self.frame_left, state="disabled")
        self.converted_file_display.grid(row=3, column=0, padx=5, pady=5, columnspan=2, sticky="ew")

        self.converted_file_button = ctk.CTkButton(self.frame_left, text="Open", command=self.open_converted_file)
        self.converted_file_button.grid(row=3, column=2, padx=5, pady=5, columnspan=2, sticky="w")

        # 新增起始與結束時間輸入
        self.start_time_var = ctk.StringVar(value="00:00:00")
        self.end_time_var = ctk.StringVar(value="")  # 待檔案選擇後更新

        self.start_time_label = ctk.CTkLabel(self.frame_left, text="Start Time:")
        self.start_time_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")

        self.start_time_entry = ctk.CTkEntry(self.frame_left, textvariable=self.start_time_var)
        self.start_time_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        self.end_time_label = ctk.CTkLabel(self.frame_left, text="End Time:")
        self.end_time_label.grid(row=5, column=0, padx=5, pady=5, sticky="w")
        
        self.end_time_entry = ctk.CTkEntry(self.frame_left, textvariable=self.end_time_var)
        self.end_time_entry.grid(row=5, column=1, padx=5, pady=5, sticky="ew")

        # ---------- 左下：轉換參數設定區 ----------
        self.frame_left_second = ctk.CTkFrame(self.frame_main)
        self.frame_left_second.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.frame_left_second.grid_columnconfigure(0, weight=1)
        self.frame_left_second.grid_columnconfigure(1, weight=1)

        # 轉換器類型選擇
        self.converter_type = ctk.StringVar(value="video")
        self.video_radio = ctk.CTkRadioButton(self.frame_left_second, text="Video Converter", variable=self.converter_type, value="video", command=self.update_parameters)
        self.audio_radio = ctk.CTkRadioButton(self.frame_left_second, text="Audio Converter", variable=self.converter_type, value="audio", command=self.update_parameters)
        self.video_radio.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.audio_radio.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # 參數設定：根據類型顯示不同的參數
        self.param_label = ctk.CTkLabel(self.frame_left_second, text="Resolution:")
        self.param_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.param_combobox = ctk.CTkComboBox(self.frame_left_second, values=[])
        self.param_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # 目標格式設定
        self.target_format_label = ctk.CTkLabel(self.frame_left_second, text="Target Format:")
        self.target_format_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.target_format_combobox = ctk.CTkComboBox(self.frame_left_second, values=[])
        self.target_format_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        # 綁定目標格式選擇事件，用於更新 audio 的 bitrate 選項
        self.target_format_combobox.bind("<<ComboboxSelected>>", self.on_audio_format_change)
        
        # 新增轉碼器選項（僅在 video 模式顯示）
        self.video_transcoder_label = ctk.CTkLabel(self.frame_left_second, text="Video Transcoder:")
        self.video_transcoder_combobox = ctk.CTkComboBox(self.frame_left_second, values=["Default", "libx264", "libx265"])
        self.audio_transcoder_label = ctk.CTkLabel(self.frame_left_second, text="Audio Transcoder:")
        self.audio_transcoder_combobox = ctk.CTkComboBox(self.frame_left_second, values=["Default", "aac", "mp3"])

        # 初始更新參數（依 converter_type）
        self.update_parameters()

        # ---------- 右側: 廣告區 ----------
        self.frame_right = ctk.CTkFrame(self.frame_main)
        self.frame_right.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=5, pady=5)
        self.frame_right.grid_propagate(False)  # 固定 frame 尺寸
        self.frame_right.grid_rowconfigure(0, weight=1)
        self.frame_right.grid_columnconfigure(0, weight=1)

        self.ad_label = ctk.CTkLabel(self.frame_right, text=LANGUAGES[self.master.current_language]["no_ad_label"])
        self.ad_label.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # ---------- 底部進度區 ----------
        self.frame_bottom = ctk.CTkFrame(self)
        self.frame_bottom.grid_rowconfigure(0, weight=4)
        self.frame_bottom.grid_rowconfigure(1, weight=6)
        self.frame_bottom.grid_columnconfigure(0, weight=7)
        self.frame_bottom.grid_columnconfigure(1, weight=3)

        self.progress_label = ctk.CTkLabel(self.frame_bottom, text="Idle")
        self.progress_label.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(self.frame_bottom)
        self.progress_bar.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.progress_bar.set(0)

        self.frame_bottom.grid(row=2, column=0, sticky="nsew", padx=10, pady=10, columnspan=2)
        self.convert_button = ctk.CTkButton(self.frame_bottom, text="Convert", command=self.start_conversion)
        self.convert_button.grid(row=1, column=1, padx=5, pady=5)

        self.update_text() # 初始化文字
        self.update_ad_area() # 初始化廣告區

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.webm *.mkv *.mov"), ("Audio Files", "*.mp3 *.wav *.flac *.ogg")]
        )
        if file_path:
            self.selected_file.set(file_path)
            self.end_time_var.set(get_media_duration(file_path))
    
    def open_converted_file(self):
        file_path = self.converted_file_display.get()
        if file_path:
            # 開啟轉換檔案所在的資料夾
            os.startfile(os.path.dirname(file_path))

    def update_parameters(self):
        """根據 converter_type 更新參數與目標格式設定"""
        if self.converter_type.get() == "video":
            self.param_label.configure(text="Resolution:")
            self.param_combobox.configure(values=["Original resolution", "4320x2160", "3840x2160", "2560x1440", "1920x1080", "1280x720", "854x480", "640x360", "426x240", "256x144"])
            self.param_combobox.set("Original resolution")
            self.target_format_label.configure(text="Target Format:")
            self.target_format_combobox.configure(values=["mp4", "webm", "mkv", "mov"])
            self.target_format_combobox.set("mp4")
            # 設定 target_format_combobox 的 callback，依據選擇動態更新轉碼器選項
            self.target_format_combobox.configure(command=self.on_video_format_change)
            # 顯示轉碼器選項並預設更新
            self.video_transcoder_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
            self.video_transcoder_combobox.grid(row=3, column=1, padx=5, pady=5, sticky="w")
            self.audio_transcoder_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")
            self.audio_transcoder_combobox.grid(row=4, column=1, padx=5, pady=5, sticky="w")
            self.on_video_format_change(None)
        else:
            self.param_label.configure(text="Bitrate:")
            self.target_format_label.configure(text="Target Format:")
            self.target_format_combobox.configure(values=["mp3", "wav", "flac", "ogg"])
            self.target_format_combobox.set("mp3")
            # 設定 target_format_combobox 的 callback，更新 audio bitrate 選項
            self.target_format_combobox.configure(command=self.on_audio_format_change)
            self.on_audio_format_change(None)
            # 隱藏轉碼器選項
            self.video_transcoder_label.grid_remove()
            self.video_transcoder_combobox.grid_remove()
            self.audio_transcoder_label.grid_remove()
            self.audio_transcoder_combobox.grid_remove()

    def on_video_format_change(self, value):
        """根據 video 目標格式動態更新視訊與音訊轉碼器選項"""
        target_format = self.target_format_combobox.get().lower()
        video_opts = {
            "mp4": ["Default", "libx264", "libx265"],
            "webm": ["Default", "libvpx", "libvpx-vp9"],
            "mkv": ["Default", "libx264", "libx265"],
            "mov": ["Default", "prores", "libx264"]
        }
        audio_opts = {
            "mp4": ["Default", "aac", "mp3"],
            "webm": ["Default", "opus", "libvorbis"],
            "mkv": ["Default", "aac", "mp3"],
            "mov": ["Default", "aac", "mp3"]
        }
        v_options = video_opts.get(target_format, ["Default"])
        a_options = audio_opts.get(target_format, ["Default"])
        self.video_transcoder_combobox.configure(values=v_options)
        self.audio_transcoder_combobox.configure(values=a_options)
        self.video_transcoder_combobox.set(v_options[0])
        self.audio_transcoder_combobox.set(a_options[0])

    def on_audio_format_change(self, value):
        """依據音訊目標格式更新 bitrate 參數選項"""
        target_format = self.target_format_combobox.get().lower()
        if target_format == "wav":
            self.param_combobox.configure(values=["20kHz","44.1kHz", "48kHz", "96kHz"])
            self.param_combobox.set("44.1kHz")
        elif target_format == "flac":
            self.param_combobox.configure(values=["320kbps"])
            self.param_combobox.set("320kbps")
        else:
            self.param_combobox.configure(values=["64kbps", "128kbps", "192kbps", "320kbps"])
            self.param_combobox.set("128kbps")

    def update_progress(self, progress):
        lang= self.master.current_language 
        if progress != -1:
            percent = int(progress * 100)
            # 使用 after 確保 GUI 更新在主執行緒中執行
            self.master.after(0, lambda: self.progress_bar.set(progress))
            self.master.after(0, lambda: self.progress_label.configure(text=f"Converting {percent}%"))
        else:
            self.master.after(100, lambda: self.progress_bar.set(progress))
            if lang == "en":
                self.master.after(0, lambda: self.progress_label.configure(text="Converting completed"))
            elif lang == "zh": 
                self.master.after(0, lambda: self.progress_label.configure(text="轉換完成"))

    def start_conversion(self):
        file_path = self.selected_file.get()
        if not file_path:
            log_and_show_error("No file selected!", self.master)
            return
        conv_type = self.converter_type.get()
        param = self.param_combobox.get()
        target_format = self.target_format_combobox.get()
        start_time = self.start_time_var.get()
        end_time = self.end_time_var.get()
        self.convert_button.configure(state="disabled")
        self.progress_label.configure(text="Converting...")

        def conversion_task():
            if end_time and end_time.strip():
                    start_sec = time_to_seconds(start_time) if start_time and start_time != "00:00:00" else 0
                    end_sec = time_to_seconds(end_time)
                    conversion_duration = end_sec - start_sec if end_sec > start_sec else 0
            else:
                duration_str = get_media_duration(file_path)
                conversion_duration = time_to_seconds(duration_str) if duration_str else 0

            if conv_type == "video":
                video_transcoder = self.video_transcoder_combobox.get()
                audio_transcoder = self.audio_transcoder_combobox.get()
                output = convert_video(
                file_path, param, target_format, start_time, conversion_duration,
                video_transcoder, audio_transcoder, self.update_progress
            )
            else:
                output = convert_audio(file_path, param, target_format, start_time, conversion_duration, self.update_progress)
           
            # 使用 after 確保 GUI 更新在主執行緒中執行 
            self.master.after(0, lambda: self.converted_file_display.configure(state="normal"))
            self.master.after(0, lambda: self.converted_file_display.delete(0, "end"))
            self.master.after(0, lambda: self.converted_file_display.insert(0, output))
            self.master.after(0, lambda: self.converted_file_display.configure(state="disabled"))
            self.master.after(0, lambda: self.convert_button.configure(state="normal"))
            self.master.after(0, lambda: self.progress_label.configure(text="Conversion complete"))
        threading.Thread(target=conversion_task).start()

        # 重製進度條
        self.progress_bar.set(0.0)

    def update_ad_area(self):
        """依據 config 中廣告圖片的設定更新廣告區"""
        ad_image_path = self.master.config.get("ad_image", "")
        if ad_image_path and os.path.exists(ad_image_path):
            try:
                img = Image.open(ad_image_path)
                # 使用 ImageOps.contain 使圖片在範圍內等比例縮放
                img = ImageOps.contain(img, (640, 480))
                # 以縮放後的尺寸建立 CTkImage
                self.ad_image = CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                # 顯示圖片，隱藏文字
                self.ad_label.configure(image=self.ad_image, text="")
            except Exception as e:
                log_and_show_error(f"AD image load failed: {e}", self.master)
                self.ad_label.configure(text=LANGUAGES[self.master.current_language]["no_ad_label"], image=None)
        else:
            # 無圖片則顯示預設文字
            self.ad_label.configure(text=LANGUAGES[self.master.current_language]["no_ad_label"], image=None)

    def update_text(self):
        lang = self.master.current_language
        self.page_title.configure(text=LANGUAGES[lang]["page3_title"])
        self.file_label.configure(text=LANGUAGES[lang]["select_files_label"])
        self.file_button.configure(text=LANGUAGES[lang]["browse_button"])
        self.converted_file_label.configure(text=LANGUAGES[lang]["converted_files_label"])
        self.converted_file_button.configure(text=LANGUAGES[lang]["open_button"])
        self.start_time_label.configure(text=LANGUAGES[lang]["start_time_label"])
        self.end_time_label.configure(text=LANGUAGES[lang]["end_time_label"])
        self.video_radio.configure(text=LANGUAGES[lang]["video_radio"])
        self.audio_radio.configure(text=LANGUAGES[lang]["audio_radio"])
        self.param_label.configure(text=LANGUAGES[lang]["resolution_label"])
        self.target_format_label.configure(text=LANGUAGES[lang]["target_format_label"])
        self.video_transcoder_label.configure(text=LANGUAGES[lang]["video_transcoder_label"])
        self.audio_transcoder_label.configure(text=LANGUAGES[lang]["audio_transcoder_label"])
        self.convert_button.configure(text=LANGUAGES[lang]["convert_button"])
        self.progress_label.configure(text=LANGUAGES[lang]["progress_ready"])

        self.update_ad_area()

class Page4(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.label = ctk.CTkLabel(self, font=("Arial", 20))
        self.label.grid(row=0, column=0, pady=20)

        self.back_btn = ctk.CTkButton(self, command=lambda: master.show_frame(HomePage))
        self.back_btn.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.update_text()

    def update_text(self):
        lang = self.master.current_language
        self.label.configure(text=LANGUAGES[lang]["page4_label"])
        self.back_btn.configure(text=LANGUAGES[lang]["back_home_button"])


if __name__ == "__main__":
    # ctk.set_default_color_theme("green")  # 主題色
    app = MainApp()
    app.mainloop()
