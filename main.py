import os
import re
import shutil
import zipfile
import tempfile
import xml.etree.ElementTree as ET
from PIL import Image

# Kivy Framework Imports
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform

# Request Android Permissions at Runtime
if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

# =========================================================
#             BACKEND CORE LOGIC (Optimized for GUI)
# =========================================================

ET.register_namespace('', 'http://www.idpf.org/2007/opf')
ET.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')

KINDLE_PROFILES = {
    "1": {"name": "Kindle Paperwhite / Oasis", "width": 1072, "height": 1448},
    "2": {"name": "Kindle Basic 10th Gen", "width": 600, "height": 800},
    "3": {"name": "Kindle Basic 8th/7th Gen", "width": 600, "height": 800},
    "4": {"name": "Kindle Paperwhite 1st/2nd Gen", "width": 758, "height": 1024},
    "5": {"name": "Kindle Scribe", "width": 1860, "height": 2480}
}

def set_epub_language_to_en(extract_dir):
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if file.lower().endswith('.opf'):
                opf_path = os.path.join(root, file)
                try:
                    with open(opf_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    new_content = re.sub(r'<dc:language>.*?</dc:language>', '<dc:language>en</dc:language>', content, flags=re.DOTALL)
                    with open(opf_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                except Exception as e:
                    print(f"Warning: {e}")

def find_cover_image_path(extract_dir):
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if file.lower().endswith('.opf'):
                opf_path = os.path.join(root, file)
                try:
                    tree = ET.parse(opf_path)
                    root_node = tree.getroot()
                    ns = {'opf': 'http://www.idpf.org/2007/opf'}
                    meta = root_node.find('.//opf:metadata', ns)
                    if meta is not None:
                        cover_meta = meta.find('.//opf:meta[@name="cover"]', ns)
                        if cover_meta is not None:
                            cover_id = cover_meta.get('content')
                            manifest = root_node.find('.//opf:manifest', ns)
                            item = manifest.find(f'.//opf:item[@id="{cover_id}"]', ns)
                            if item is not None:
                                return os.path.join(os.path.dirname(opf_path), item.get('href')), opf_path
                except: pass
    return None, None

def run_extract_cover(input_epub):
    extract_dir = os.path.join(tempfile.gettempdir(), "temp_epub_extract_cover")
    if os.path.exists(extract_dir): shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    try:
        with zipfile.ZipFile(input_epub, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        declared_cover_path, _ = find_cover_image_path(extract_dir)
        if declared_cover_path and os.path.exists(declared_cover_path):
            _, ext = os.path.splitext(declared_cover_path)
            output_cover_path = input_epub.replace(".epub", f"_cover{ext}")
            shutil.copy(declared_cover_path, output_cover_path)
            return f"Success! Cover extracted to:\n{os.path.basename(output_cover_path)}"
        return "Error: No declared cover image found inside this EPUB."
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        shutil.rmtree(extract_dir)

def run_process_epub(input_epub, mode, profile_key=None, replacement_cover=None):
    extract_dir = os.path.join(tempfile.gettempdir(), "temp_epub_process")
    if os.path.exists(extract_dir): shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    
    output_epub = input_epub.replace(".epub", "_optimized.epub")
    
    try:
        with zipfile.ZipFile(input_epub, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        if mode == "3":
            set_epub_language_to_en(extract_dir)

        declared_cover_path, opf_path = find_cover_image_path(extract_dir)
        
        if mode == "1" and replacement_cover:
            if declared_cover_path:
                shutil.copy(replacement_cover, declared_cover_path)
            else:
                shutil.copy(replacement_cover, os.path.join(extract_dir, "cover.jpg"))

        if mode in ["1", "2"] and profile_key:
            target_w = KINDLE_PROFILES[profile_key]['width']
            target_h = KINDLE_PROFILES[profile_key]['height']
            valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')
            
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(valid_extensions):
                        path = os.path.join(root, file)
                        is_cover = (declared_cover_path and os.path.normpath(path) == os.path.normpath(declared_cover_path))
                        try:
                            with Image.open(path) as img:
                                img = img.convert('L')
                                if is_cover:
                                    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                                else:
                                    img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
                                img.save(path, format=img.format, quality=80, optimize=True)
                        except: pass

        with zipfile.ZipFile(output_epub, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), extract_dir))
        return f"Success! Output saved to:\n{os.path.basename(output_epub)}"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        shutil.rmtree(extract_dir)

# =========================================================
#             KIVY USER INTERFACE SCREENS
# =========================================================

class MainMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        layout.add_widget(Label(text="KINDLE EPUB OPTIMIZER", font_size='24sp', size_hint_y=0.2))
        
        btn1 = Button(text="1. Change Cover Photo", size_hint_y=0.15)
        btn1.bind(on_press=lambda x: self.go_to_file_select("1"))
        
        btn2 = Button(text="2. Optimize Images Only", size_hint_y=0.15)
        btn2.bind(on_press=lambda x: self.go_to_file_select("2"))
        
        btn3 = Button(text="3. Set Language to 'en'", size_hint_y=0.15)
        btn3.bind(on_press=lambda x: self.go_to_file_select("3"))
        
        btn4 = Button(text="4. Extract Cover Photo", size_hint_y=0.15)
        btn4.bind(on_press=lambda x: self.go_to_file_select("4"))
        
        layout.add_widget(btn1)
        layout.add_widget(btn2)
        layout.add_widget(btn3)
        layout.add_widget(btn4)
        self.add_widget(layout)

    def go_to_file_select(self, mode):
        self.manager.current_mode = mode
        if mode == "1":
            self.manager.get_screen('file_select').label.text = "Select your target EPUB file:"
        elif mode == "4":
            self.manager.get_screen('file_select').label.text = "Select EPUB to extract cover from:"
        else:
            self.manager.get_screen('file_select').label.text = "Select EPUB file:"
        self.manager.current = 'file_select'

class FileSelectScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.label = Label(text="Select a file", size_hint_y=0.1)
        
        start_path = '/sdcard/Download' if os.path.exists('/sdcard/Download') else os.path.expanduser('~')
        self.file_chooser = FileChooserIconView(path=start_path, filters=['*.epub', '*.EPUB'])
        
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=0.15, spacing=10)
        back_btn = Button(text="Back")
        back_btn.bind(on_press=self.go_back)
        
        next_btn = Button(text="Select File")
        next_btn.bind(on_press=self.confirm_selection)
        
        btn_layout.add_widget(back_btn)
        btn_layout.add_widget(next_btn)
        
        self.layout.add_widget(self.label)
        self.layout.add_widget(self.file_chooser)
        self.layout.add_widget(btn_layout)
        self.add_widget(self.layout)

    def go_back(self, instance):
        self.manager.current = 'main_menu'

    def confirm_selection(self, instance):
        selection = self.file_chooser.selection
        if not selection:
            self.label.text = "Please touch and highlight a file first!"
            return
        
        self.manager.selected_epub = selection[0]
        mode = self.manager.current_mode
        
        if mode == "4":
            result = run_extract_cover(self.manager.selected_epub)
            self.manager.get_screen('status').status_label.text = result
            self.manager.current = 'status'
        elif mode == "3":
            result = run_process_epub(self.manager.selected_epub, mode="3")
            self.manager.get_screen('status').status_label.text = result
            self.manager.current = 'status'
        elif mode == "1":
            self.manager.get_screen('cover_select').file_chooser.filters = ['*.jpg', '*.jpeg', '*.png']
            self.manager.current = 'cover_select'
        elif mode == "2":
            self.manager.current = 'profile_select'

class CoverSelectScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(Label(text="Select Replacement Cover Image (.jpg/.png):", size_hint_y=0.1))
        
        start_path = '/sdcard/Download' if os.path.exists('/sdcard/Download') else os.path.expanduser('~')
        self.file_chooser = FileChooserIconView(path=start_path, filters=['*.jpg', '*.jpeg', '*.png'])
        
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=0.15, spacing=10)
        back_btn = Button(text="Back")
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'file_select'))
        
        next_btn = Button(text="Select Image")
        next_btn.bind(on_press=self.confirm_cover)
        
        btn_layout.add_widget(back_btn)
        btn_layout.add_widget(next_btn)
        layout.add_widget(self.file_chooser)
        layout.add_widget(btn_layout)
        self.add_widget(layout)

    def confirm_cover(self, instance):
        selection = self.file_chooser.selection
        if not selection:
            return
        self.manager.selected_cover = selection[0]
        self.manager.current = 'profile_select'

class ProfileSelectScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text="Select Kindle Configuration Profile:", font_size='18sp', size_hint_y=0.15))
        
        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        
        for key, value in KINDLE_PROFILES.items():
            btn = Button(text=f"{value['name']} ({value['width']}x{value['height']})", size_hint_y=None, height=60)
            btn.bind(on_press=lambda x, k=key: self.process_and_run(k))
            grid.add_widget(btn)
            
        scroll.add_widget(grid)
        layout.add_widget(scroll)
        
        back_btn = Button(text="Cancel", size_hint_y=0.15)
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'main_menu'))
        layout.add_widget(back_btn)
        self.add_widget(layout)

    def process_and_run(self, profile_key):
        mode = self.manager.current_mode
        epub = self.manager.selected_epub
        cover = self.manager.selected_cover if mode == "1" else None
        
        result = run_process_epub(epub, mode, profile_key, cover)
        self.manager.get_screen('status').status_label.text = result
        self.manager.current = 'status'

class StatusScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(kwargs)
        layout = BoxLayout(orientation='vertical', padding=30, spacing=20)
        self.status_label = Label(text="Processing...", font_size='16sp', halign='center')
        
        home_btn = Button(text="Return to Main Menu", size_hint_y=0.2)
        home_btn.bind(on_press=self.go_home)
        
        layout.add_widget(self.status_label)
        layout.add_widget(home_btn)
        self.add_widget(layout)

    def go_home(self, instance):
        self.manager.current = 'main_menu'

class KindleOptimizerApp(App):
    def build(self):
        sm = ScreenManager()
        sm.current_mode = "1"
        sm.selected_epub = ""
        sm.selected_cover = ""
        
        sm.add_widget(MainMenuScreen(name='main_menu'))
        sm.add_widget(FileSelectScreen(name='file_select'))
        sm.add_widget(CoverSelectScreen(name='cover_select'))
        sm.add_widget(ProfileSelectScreen(name='profile_select'))
        sm.add_widget(StatusScreen(name='status'))
        return sm

if __name__ == '__main__':
    KindleOptimizerApp().run()
