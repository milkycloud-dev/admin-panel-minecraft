"""
Minecraft Admin Panel v1.3.6
Standalone App with Auto-updater, Custom Fonts, Backups and White-Labeling.
"""
import os
import re
import threading
import json
import sys
import subprocess
import base64
import time
import ctypes

try:
    import customtkinter as ctk
    from tkinter import messagebox, ttk, filedialog, Menu
    from PIL import Image, ImageTk
    import paramiko
    import blake3
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "paramiko", "blake3", "customtkinter", "Pillow"])
    import customtkinter as ctk
    from tkinter import messagebox, ttk, filedialog, Menu
    from PIL import Image, ImageTk
    import paramiko
    import blake3

from config_manager import ConfigManager
from ssh_manager import SSHManager
from manifest_manager import ManifestManager
from sync_manager import SyncManager
from updater import check_for_updates

# Colors
C = {
    "bg":        "#0E0E0E",
    "bg2":       "#18181A",
    "section":   "#202022",
    "hover":     "#2A2A2D",
    "border":    "#333336",
    "text":      "#FFFFFF",
    "text_dim":  "#A0A0A5",
    "accent":    "#0078D4",
    "accent_h":  "#2b88d8",
    "green":     "#107C10",
    "green_h":   "#0F6A0F",
    "red":       "#E81123",
    "red_h":     "#D10F1F",
    "orange":    "#D83B01",
    "row_green": "#163319",
    "row_yellow":"#3D3512",
    "row_blue":  "#142940",
    "row_red":   "#4D1B1B"
}

ctk.set_appearance_mode("Dark")

def _inject_font_to_os(font_path):
    """
    [RU] Функция _inject_font_to_os.
    [EN] Function _inject_font_to_os.
    """
    if sys.platform == "win32":
        try:
            FR_PRIVATE = 0x10
            FR_NOT_ENUM = 0x20
            ctypes.windll.gdi32.AddFontResourceExW(font_path, FR_PRIVATE | FR_NOT_ENUM, 0)
        except Exception:
            pass

class AdminPanel(ctk.CTk):
    def __init__(self):
        """
        [RU] Функция __init__.
        [EN] Function __init__.
        """
        super().__init__()
        self.title("Minecraft Admin Panel")
        self.geometry("1300x800")
        self.configure(fg_color=C["bg"])
        self.minsize(1000, 650)

        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                self._icon_photo = ImageTk.PhotoImage(img.resize((64, 64)))
                self.iconphoto(True, self._icon_photo)
            except Exception:
                pass

        self._load_fonts()

        self.config_manager = ConfigManager()
        self.manifest_manager = ManifestManager(self.config_manager)
        self.sync_manager = SyncManager(self.config_manager)

        self.client_mods_cache = {}
        self.game_mods_cache = {}

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self._build_sidebar()
        
        self.log_frame = ctk.CTkFrame(self, fg_color=C["section"], height=120, corner_radius=0)
        self.log_frame.grid(row=1, column=1, sticky="ews")
        self.log_frame.pack_propagate(False)
        self.live_log = ctk.CTkTextbox(self.log_frame, font=self.MONO_S, fg_color="transparent", text_color=C["text_dim"])
        self.live_log.pack(fill="both", expand=True, padx=10, pady=10)

        self._pages = {}
        self._build_sync_hub()
        self._build_game_console()
        self._build_backups()
        self._build_settings()
        self._setup_bindings()
        self._show_page("sync")
        self.after(500, self.scan_mods)
        
        # Check for updates in background
        check_for_updates(self)

    def log_message(self, msg, is_error=False):
        """
        [RU] Функция log_message.
        [EN] Function log_message.
        """
        import datetime
        t = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = "[ОШИБКА] " if is_error else "[СИСТЕМА] "
        line = f"[{t}] {prefix}{msg}\n"
        def _append():
            """
            [RU] Функция _append.
            [EN] Function _append.
            """
            self.live_log.insert("end", line)
            if is_error:
                # Покрасим строку в красный
                pass
            self.live_log.see("end")
        self.after(0, _append)

    def _setup_bindings(self):
        """
        [RU] Функция _setup_bindings.
        [EN] Function _setup_bindings.
        """
        # Поддержка копирования/вставки на английской раскладке
        self.bind_all("<Control-a>", lambda e: self.focus_get().event_generate("<<SelectAll>>") if hasattr(self.focus_get(), 'event_generate') else None)
        self.bind_all("<Control-c>", lambda e: self.focus_get().event_generate("<<Copy>>") if hasattr(self.focus_get(), 'event_generate') else None)
        self.bind_all("<Control-v>", lambda e: self.focus_get().event_generate("<<Paste>>") if hasattr(self.focus_get(), 'event_generate') else None)
        self.bind_all("<Control-x>", lambda e: self.focus_get().event_generate("<<Cut>>") if hasattr(self.focus_get(), 'event_generate') else None)
        
        # Обработка русской раскладки через коды клавиш
        def _on_key(e):
            """
            [RU] Функция _on_key.
            [EN] Function _on_key.
            """
            if e.state & 4: # Control is pressed
                if e.keycode == 65: # A
                    if hasattr(self.focus_get(), 'event_generate'): self.focus_get().event_generate("<<SelectAll>>")
                elif e.keycode == 67: # C
                    if hasattr(self.focus_get(), 'event_generate'): self.focus_get().event_generate("<<Copy>>")
                elif e.keycode == 86: # V
                    if hasattr(self.focus_get(), 'event_generate'): self.focus_get().event_generate("<<Paste>>")
                elif e.keycode == 88: # X
                    if hasattr(self.focus_get(), 'event_generate'): self.focus_get().event_generate("<<Cut>>")
        self.bind_all("<Key>", _on_key, add="+")

    def _load_fonts(self):
        """
        [RU] Функция _load_fonts.
        [EN] Function _load_fonts.
        """
        f_dir = os.path.join(os.path.dirname(__file__), "fonts")
        
        has_custom = False
        try:
            p1 = os.path.join(f_dir, "Inter.ttf")
            p2 = os.path.join(f_dir, "Inter-Bold.ttf")
            if os.path.exists(p1):
                ctk.FontManager.load_font(p1)
                _inject_font_to_os(p1)
                has_custom = True
            if os.path.exists(p2):
                ctk.FontManager.load_font(p2)
                _inject_font_to_os(p2)
                has_custom = True
        except Exception:
            pass

        if has_custom:
            self.F_FAM = ("Inter", "Segoe UI", "Helvetica")
            self.F_FAM_H = ("Inter", "Segoe UI", "Helvetica")
        else:
            self.F_FAM = ("Segoe UI Variable Display", "Segoe UI", "Helvetica")
            self.F_FAM_H = self.F_FAM

        self.FONT_XL  = (self.F_FAM_H[0], 24, "bold")
        self.FONT_L   = (self.F_FAM_H[0], 18, "bold")
        self.FONT     = (self.F_FAM[0], 14)
        self.FONT_B   = (self.F_FAM[0], 14, "bold")
        self.FONT_S   = (self.F_FAM[0], 12)
        self.MONO     = ("Consolas", 14)
        self.MONO_S   = ("Consolas", 12)

    # ═══════════════════════════════════════════════════════════
    #  SIDEBAR
    # ═══════════════════════════════════════════════════════════
    def _build_sidebar(self):
        """
        [RU] Функция _build_sidebar.
        [EN] Function _build_sidebar.
        """
        sb = ctk.CTkFrame(self, width=240, fg_color=C["bg2"], corner_radius=0)
        sb.grid(row=0, column=0, rowspan=2, sticky="ns")
        sb.grid_propagate(False)

        ctk.CTkLabel(sb, text="Minecraft", font=self.FONT_XL, text_color=C["text"]).pack(pady=(30, 2), anchor="w", padx=20)
        ctk.CTkLabel(sb, text="Admin Panel", font=self.FONT_S, text_color=C["text_dim"]).pack(pady=(0, 30), anchor="w", padx=20)

        self._sb_btns = {}
        items = [
            ("sync",    "📦  Управление Модами"),
            ("console", "💻  Игровая Консоль"),
            ("backups", "💾  Бекапы"),
            ("settings","⚙️  Настройки"),
        ]

        for key, text in items:
            btn = ctk.CTkButton(sb, text=text, anchor="w", height=40, corner_radius=8,
                                font=self.FONT_B, fg_color="transparent", hover_color=C["section"],
                                text_color=C["text_dim"],
                                command=lambda k=key: self._show_page(k))
            btn.pack(fill="x", padx=15, pady=4)
            self._sb_btns[key] = btn

    def _show_page(self, key):
        """
        [RU] Функция _show_page.
        [EN] Function _show_page.
        """
        for k, btn in self._sb_btns.items():
            if k == key:
                btn.configure(fg_color=C["section"], text_color=C["text"])
            else:
                btn.configure(fg_color="transparent", text_color=C["text_dim"])
                
        for k, fr in self._pages.items():
            fr.grid(row=0, column=1, sticky="nsew") if k == key else fr.grid_forget()
            
        if key == "console" and not getattr(self, "_console_checked", False):
            self._console_checked = True
            self._check_server_status()
            self._start_live_stream()
            
        if key == "backups":
            self.refresh_backups()

    # ═══════════════════════════════════════════════════════════
    #  MODS HUB
    # ═══════════════════════════════════════════════════════════
    def _build_sync_hub(self):
        """
        [RU] Функция _build_sync_hub.
        [EN] Function _build_sync_hub.
        """
        page = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        self._pages["sync"] = page

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(header, text="Управление Модами", font=self.FONT_XL, text_color=C["text"]).pack(side="left")
        
        sc_btn = ctk.CTkButton(header, text="Пересканировать", width=140, height=36, corner_radius=18,
                               font=self.FONT_B, fg_color=C["accent"], hover_color=C["accent_h"], text_color="#FFFFFF", command=self.scan_mods)
        sc_btn.pack(side="right", padx=0)

        # Main Layout: 3 Columns
        panels_container = ctk.CTkFrame(page, fg_color="transparent")
        panels_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        panels_container.columnconfigure(0, weight=1)
        panels_container.columnconfigure(1, weight=0)
        panels_container.columnconfigure(2, weight=1)
        panels_container.rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("NB.Treeview", background=C["section"], foreground=C["text"], fieldbackground=C["section"], borderwidth=0, font=self.FONT_S, rowheight=26)
        style.configure("NB.Treeview.Heading", background=C["section"], foreground=C["text_dim"], font=self.FONT_B, borderwidth=0, relief="flat", padding=(0, 5))
        style.map("NB.Treeview", background=[("selected", C["accent"])])

        def _make_panel(parent, col, title, ip, server_key, is_client=False):
            """
            [RU] Функция _make_panel.
            [EN] Function _make_panel.
            """
            c = ctk.CTkFrame(parent, fg_color=C["section"], corner_radius=12)
            c.grid(row=0, column=col, sticky="nsew")
            
            th = ctk.CTkFrame(c, fg_color="transparent")
            th.pack(fill="x", padx=15, pady=(15, 10))
            
            th_left = ctk.CTkFrame(th, fg_color="transparent")
            th_left.pack(side="left")
            ctk.CTkLabel(th_left, text=title, font=self.FONT_L, text_color=C["text"]).pack(anchor="w")
            ctk.CTkLabel(th_left, text=ip, font=self.FONT_S, text_color=C["text_dim"]).pack(anchor="w")

            th_right = ctk.CTkFrame(th, fg_color="transparent")
            th_right.pack(side="right")
            
            up_btn = ctk.CTkButton(th_right, text="Загрузить .jar", width=110, height=30, corner_radius=15,
                                   font=self.FONT_B, fg_color=C["bg2"], hover_color=C["hover"], text_color=C["text"], command=lambda: self.upload_local_mod(server_key))
            up_btn.pack(side="right", padx=(10, 0), pady=(5,0))

            if is_client:
                mf_btn = ctk.CTkButton(th_right, text="Собрать Manifest", width=130, height=30, corner_radius=15,
                                       font=self.FONT_B, fg_color=C["orange"], hover_color="#FF7B1A", text_color="#FFFFFF", command=self.update_manifest_only)
                mf_btn.pack(side="right", padx=(10, 0), pady=(5,0))

            tf = ctk.CTkFrame(c, fg_color="transparent")
            tf.pack(fill="both", expand=True, padx=15, pady=(0, 15))
            
            tree = ttk.Treeview(tf, columns=("file", "size", "status"), show="headings", style="NB.Treeview")
            tree.heading("file", text="Мод")
            tree.heading("size", text="Размер")
            tree.heading("status", text="Статус")
            tree.column("file", width=200, minwidth=100)
            tree.column("size", width=80, minwidth=60, anchor="e")
            tree.column("status", width=120, minwidth=80, anchor="center")
            
            for tag in ("green", "yellow", "blue", "red"):
                tree.tag_configure(tag, background=C[f"row_{tag}"])
            
            tree.pack(side="left", fill="both", expand=True)
            return tree

        cs_conf = self.config_manager.get("client_server")
        gs_conf = self.config_manager.get("game_server")

        self.tree_client = _make_panel(panels_container, 0, cs_conf.get("name", "Клиент-сервер"), cs_conf.get("host", "Не настроен"), "client_server", is_client=True)
        self.tree_game = _make_panel(panels_container, 2, gs_conf.get("name", "Игровой сервер"), gs_conf.get("host", "Не настроен"), "game_server")

        # Centralized Scrollbar
        scroll_frame = ctk.CTkFrame(panels_container, fg_color="transparent", width=20)
        scroll_frame.grid(row=0, column=1, sticky="ns", padx=5)
        
        self.center_scroll = ttk.Scrollbar(scroll_frame, orient="vertical")
        self.center_scroll.pack(fill="y", expand=True)

        def sync_yview(*args):
            """
            [RU] Функция sync_yview.
            [EN] Function sync_yview.
            """
            self.tree_client.yview(*args)
            self.tree_game.yview(*args)
            
        def set_scroll(*args):
            """
            [RU] Функция set_scroll.
            [EN] Function set_scroll.
            """
            self.center_scroll.set(*args)
            self.tree_client.yview_moveto(args[0])
            self.tree_game.yview_moveto(args[0])

        self.center_scroll.configure(command=sync_yview)
        self.tree_client.configure(yscrollcommand=set_scroll)
        self.tree_game.configure(yscrollcommand=set_scroll)
        
        def on_mw(e): 
            """
            [RU] Функция on_mw.
            [EN] Function on_mw.
            """
            self.tree_client.yview_scroll(int(-1*(e.delta/120)), "units")
            self.tree_game.yview_scroll(int(-1*(e.delta/120)), "units")
            return "break"
        self.tree_client.bind("<MouseWheel>", on_mw)
        self.tree_game.bind("<MouseWheel>", on_mw)

        self.tree_client.bind("<Button-3>", lambda e: self._ctx(e, "client_server", self.tree_client))
        self.tree_game.bind("<Button-3>", lambda e: self._ctx(e, "game_server", self.tree_game))

        # Local folder
        loc = ctk.CTkFrame(page, fg_color=C["section"], corner_radius=12, height=180)
        loc.pack(fill="x", padx=20, pady=(10, 20))
        loc.pack_propagate(False)

        lh = ctk.CTkFrame(loc, fg_color="transparent")
        lh.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(lh, text="Локальная папка", font=self.FONT_L, text_color=C["text"]).pack(side="left")
        self.local_path_var = ctk.StringVar(value=os.path.join(os.path.dirname(os.path.abspath(__file__)), self.config_manager.get("paths", "local_mods_dir") or "mods"))
        ctk.CTkLabel(lh, textvariable=self.local_path_var, font=self.FONT_S, text_color=C["text_dim"]).pack(side="left", padx=15)
        
        ctk.CTkButton(lh, text="Обзор", width=60, height=28, corner_radius=14, font=self.FONT_S, fg_color=C["hover"], hover_color=C["border"], command=self._choose_local_dir).pack(side="right", padx=0)
        ctk.CTkButton(lh, text="На Клиент", width=100, height=28, corner_radius=14, font=self.FONT_S, fg_color=C["bg2"], command=lambda: self._upload_local_to("client_server")).pack(side="right", padx=10)
        ctk.CTkButton(lh, text="На Игровой", width=100, height=28, corner_radius=14, font=self.FONT_S, fg_color=C["bg2"], command=lambda: self._upload_local_to("game_server")).pack(side="right", padx=10)

        self.tree_local = ttk.Treeview(loc, columns=("file", "size"), show="headings", style="NB.Treeview")
        self.tree_local.heading("file", text="Мод")
        self.tree_local.heading("size", text="Размер")
        self.tree_local.column("file", width=500, minwidth=200)
        self.tree_local.column("size", width=120, minwidth=80, anchor="e")
        self.tree_local.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.tree_local.bind("<Button-3>", self._ctx_local)

    @staticmethod
    def _mod_base(f):
        """
        [RU] Функция _mod_base.
        [EN] Function _mod_base.
        """
        name = f.rsplit('.jar', 1)[0]
        m = re.match(r'^([a-zA-Z_\-]+?)[\-_]?\d', name)
        return m.group(1).rstrip('-_').lower() if m else name.lower()

    @staticmethod
    def _fmt(s):
        """
        [RU] Функция _fmt.
        [EN] Function _fmt.
        """
        if s < 1024: return f"{s} B"
        elif s < 1048576: return f"{s//1024} KB"
        else: return f"{s/1048576:.1f} MB"

    def _choose_local_dir(self):
        """
        [RU] Функция _choose_local_dir.
        [EN] Function _choose_local_dir.
        """
        d = filedialog.askdirectory(title="Выберите папку с модами")
        if d: self.local_path_var.set(d); self._refresh_local()

    def _ctx(self, event, server_key, tree):
        """
        [RU] Функция _ctx.
        [EN] Function _ctx.
        """
        item = tree.identify_row(event.y)
        if not item: return
        tree.selection_set(item)
        fn = tree.item(item, "values")[0]
        if not fn: return
        other = "game_server" if server_key == "client_server" else "client_server"
        
        ol = self.config_manager.get(other, "name")
        tl = self.config_manager.get(server_key, "name")
        
        m = Menu(self, tearoff=0, font=self.FONT_S, bg=C["section"], fg=C["text"], activebackground=C["accent"], activeforeground="white", borderwidth=0)
        m.add_command(label=f"Перебросить на {ol}", command=lambda: self._transfer(server_key, other, fn))
        m.add_command(label="Скачать локально", command=lambda: self._dl_local(server_key, fn))
        m.add_separator()
        m.add_command(label=f"Удалить с {tl}", command=lambda: self._delete(server_key, fn))
        m.post(event.x_root, event.y_root)

    def _ctx_local(self, event):
        """
        [RU] Функция _ctx_local.
        [EN] Function _ctx_local.
        """
        item = self.tree_local.identify_row(event.y)
        if not item: return
        self.tree_local.selection_set(item)
        fn = self.tree_local.item(item, "values")[0]
        ap = os.path.join(self.local_path_var.get(), fn)
        
        m = Menu(self, tearoff=0, font=self.FONT_S, bg=C["section"], fg=C["text"], activebackground=C["accent"], activeforeground="white", borderwidth=0)
        m.add_command(label="Загрузить на Клиент", command=lambda: self._up1(ap, "client_server"))
        m.add_command(label="Загрузить на Игровой", command=lambda: self._up1(ap, "game_server"))
        m.add_separator()
        m.add_command(label="Удалить файл", command=lambda: self._del_local(ap, fn))
        m.post(event.x_root, event.y_root)

    def scan_mods(self):
        """
        [RU] Функция scan_mods.
        [EN] Function scan_mods.
        """
        for t in (self.tree_client, self.tree_game):
            for i in t.get_children(): t.delete(i)
        self.log_message("[Система] Сканирование модов на серверах...")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            for t in (self.tree_client, self.tree_game, self.tree_local):
                for i in t.get_children(): t.delete(i)
            cm, c_err = self.sync_manager.get_remote_mods("client_server")
            gm, g_err = self.sync_manager.get_remote_mods("game_server")
            
            if c_err and "Authentication failed" in c_err:
                self.log_message("Неверный логин или пароль для Клиент-сервера.", True)
            elif c_err:
                self.log_message(f"Ошибка Клиент: {c_err}", True)
                
            if g_err and "Authentication failed" in g_err:
                self.log_message("Неверный логин или пароль для Игрового сервера.", True)
            elif g_err:
                self.log_message(f"Ошибка Игровой: {g_err}", True)

            cm = cm or {}; gm = gm or {}
            self.client_mods_cache = cm; self.game_mods_cache = gm
            cb = {}; [cb.setdefault(self._mod_base(f), []).append(f) for f in cm]
            gb = {}; [gb.setdefault(self._mod_base(f), []).append(f) for f in gm]
            matched, partial, c_only, g_only = [], [], [], []; pc, pg = set(), set()
            for f in sorted(set(cm) & set(gm), key=str.lower):
                if cm[f]["size"] == gm[f]["size"]:
                    hash_match = True
                    if cm[f].get("hash") and gm[f].get("hash") and cm[f]["hash"] != gm[f]["hash"]:
                        hash_match = False
                    matched.append((f, f, cm[f]["size"], gm[f]["size"], hash_match))
                else: 
                    partial.append((f, f, cm[f]["size"], gm[f]["size"]))
                pc.add(f); pg.add(f)
            for b, cfs in sorted(cb.items()):
                if b in gb:
                    for cf in cfs:
                        if cf in pc: continue
                        for gf in gb[b]:
                            if gf in pg: continue
                            partial.append((cf, gf, cm[cf]["size"], gm[gf]["size"]))
                            pc.add(cf); pg.add(gf); break
            [c_only.append(f) for f in sorted(set(cm) - pc, key=str.lower)]
            [g_only.append(f) for f in sorted(set(gm) - pg, key=str.lower)]

            for cf, gf, cs, gs, hash_match in sorted(matched, key=lambda x: x[0].lower()):
                if hash_match:
                    self.tree_client.insert("", "end", values=(cf, self._fmt(cs), "✔ совпадает"), tags=("green",))
                    self.tree_game.insert("", "end", values=(gf, self._fmt(gs), "✔ совпадает"), tags=("green",))
                else:
                    self.tree_client.insert("", "end", values=(cf, self._fmt(cs), "❌ суммы разные"), tags=("red",))
                    self.tree_game.insert("", "end", values=(gf, self._fmt(gs), "❌ суммы разные"), tags=("red",))
            for cf, gf, cs, gs in sorted(partial, key=lambda x: x[0].lower()):
                self.tree_client.insert("", "end", values=(cf, self._fmt(cs), "разные версии"), tags=("yellow",))
                self.tree_game.insert("", "end", values=(gf, self._fmt(gs), "разные версии"), tags=("yellow",))
            pad_c = max(0, len(g_only) - len(c_only)); pad_g = max(0, len(c_only) - len(g_only))
            for f in c_only: self.tree_client.insert("", "end", values=(f, self._fmt(cm[f]["size"]), "только здесь"), tags=("blue",))
            for _ in range(pad_c): self.tree_client.insert("", "end", values=("", "", ""), tags=())
            for f in g_only: self.tree_game.insert("", "end", values=(f, self._fmt(gm[f]["size"]), "только здесь"), tags=("blue",))
            for _ in range(pad_g): self.tree_game.insert("", "end", values=("", "", ""), tags=())
            self._refresh_local()
            self.log_message("[Система] Списки модов обновлены и сверены.")
        threading.Thread(target=t, daemon=True).start()

    def _refresh_local(self):
        """
        [RU] Функция _refresh_local.
        [EN] Function _refresh_local.
        """
        for i in self.tree_local.get_children(): self.tree_local.delete(i)
        d = self.local_path_var.get(); os.makedirs(d, exist_ok=True)
        for f in sorted(os.listdir(d)):
            if f.endswith(".jar") and not f.startswith("."):
                sz = os.path.getsize(os.path.join(d, f))
                self.tree_local.insert("", "end", values=(f, self._fmt(sz)))

    def _transfer(self, src, dst, fn):
        """
        [RU] Функция _transfer.
        [EN] Function _transfer.
        """
        if not messagebox.askyesno("Переброс", f"Перебросить {fn}?"): return
        self.log_message(f"Переброс {fn} с {src} на {dst}...")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            c1, c2 = self.config_manager.get(src), self.config_manager.get(dst)
            s1, s2 = SSHManager(c1["host"],c1["user"],c1["password"]), SSHManager(c2["host"],c2["user"],c2["password"])
            ok1, m1 = s1.connect()
            if not ok1: self.log_message(f"Сервер {src}:\n{m1}", True); return
            ok2, m2 = s2.connect()
            if not ok2: self.log_message(f"Сервер {dst}:\n{m2}", True); return
            _, ld = self.sync_manager.get_local_mods()
            tmp = os.path.join(ld, os.path.basename(fn))
            try: s1.sftp.get(f"{c1['remote_dir']}/mods/{fn}", tmp); s2.upload_file(tmp, f"{c2['remote_dir']}/mods/{fn}")
            except Exception as e: self.log_message(f"Ошибка переброса: {str(e)}", True)
            finally: s1.disconnect(); s2.disconnect(); self.scan_mods(); self.log_message(f"Успешно переброшен {fn}")
        threading.Thread(target=t, daemon=True).start()

    def _delete(self, srv, fn):
        """
        [RU] Функция _delete.
        [EN] Function _delete.
        """
        if not messagebox.askyesno("Удаление", f"Удалить {fn}?"): return
        self.log_message(f"Удаление {fn} с сервера {srv}...")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            c = self.config_manager.get(srv); ssh = SSHManager(c["host"],c["user"],c["password"])
            ok, msg = ssh.connect()
            if not ok: self.log_message(f"Ошибка: {msg}", True); return
            ssh.execute_command(f"rm -f \"{c['remote_dir']}/mods/{fn}\"")
            ssh.disconnect()
            self.log_message(f"Удалено {fn}")
            self.scan_mods()
        threading.Thread(target=t, daemon=True).start()

    def _dl_local(self, srv, fn):
        """
        [RU] Функция _dl_local.
        [EN] Function _dl_local.
        """
        self.log_message(f"Скачивание {fn} локально...")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            c = self.config_manager.get(srv); ssh = SSHManager(c["host"],c["user"],c["password"])
            ok, msg = ssh.connect()
            if not ok: self.log_message(f"Ошибка: {msg}", True); return
            d = self.local_path_var.get(); os.makedirs(d, exist_ok=True)
            try: ssh.sftp.get(f"{c['remote_dir']}/mods/{fn}", os.path.join(d, os.path.basename(fn)))
            except Exception as e: self.log_message(f"Ошибка: {str(e)}", True)
            finally: ssh.disconnect(); self._refresh_local(); self.log_message(f"Скачано {fn}")
        threading.Thread(target=t, daemon=True).start()

    def upload_local_mod(self, target_server):
        """
        [RU] Функция upload_local_mod.
        [EN] Function upload_local_mod.
        """
        files = filedialog.askopenfilenames(title="Моды (.jar)", filetypes=[("JAR", "*.jar")])
        if not files: return
        self.log_message(f"Загрузка {len(files)} модов на {target_server}...")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            c = self.config_manager.get(target_server)
            s = SSHManager(c["host"],c["user"],c["password"])
            ok, msg = s.connect()
            if not ok: self.log_message(f"Ошибка: {msg}", True); return
            for f in files:
                s.upload_file(f, f"{c['remote_dir']}/mods/{os.path.basename(f)}")
            s.disconnect()
            self.log_message(f"Загружено {len(files)} модов на {target_server}.")
            self.scan_mods()
        threading.Thread(target=t, daemon=True).start()

    def _up1(self, ap, srv):
        """
        [RU] Функция _up1.
        [EN] Function _up1.
        """
        if not messagebox.askyesno("Загрузка", f"Загрузить {os.path.basename(ap)}?"): return
        self.log_message(f"Загрузка {os.path.basename(ap)} на {srv}...")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            c = self.config_manager.get(srv); ssh = SSHManager(c["host"],c["user"],c["password"])
            ok, msg = ssh.connect()
            if not ok: self.log_message(f"Ошибка: {msg}", True); return
            ssh.upload_file(ap, f"{c['remote_dir']}/mods/{os.path.basename(ap)}")
            ssh.disconnect()
            self.log_message(f"Загружено {os.path.basename(ap)}")
            self.scan_mods()
        threading.Thread(target=t, daemon=True).start()

    def _upload_local_to(self, srv):
        """
        [RU] Функция _upload_local_to.
        [EN] Function _upload_local_to.
        """
        d = self.local_path_var.get()
        jars = [f for f in os.listdir(d) if f.endswith(".jar") and not f.startswith(".")]
        if not jars or not messagebox.askyesno("Загрузка", f"Загрузить {len(jars)} модов?"): return
        self.log_message(f"Загрузка локальной папки на {srv}...")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            c = self.config_manager.get(srv); ssh = SSHManager(c["host"],c["user"],c["password"])
            ok, msg = ssh.connect()
            if not ok: self.log_message(f"Ошибка: {msg}", True); return
            for j in jars: ssh.upload_file(os.path.join(d,j), f"{c['remote_dir']}/mods/{j}")
            ssh.disconnect(); self.log_message("Массовая загрузка завершена."); self.scan_mods()
        threading.Thread(target=t, daemon=True).start()

    def update_manifest_only(self):
        """
        [RU] Функция update_manifest_only.
        [EN] Function update_manifest_only.
        """
        if not messagebox.askyesno("Manifest", "Пересобрать manifest.json на сервере скачивания?"): return
        self.log_message("Запущена пересборка manifest.json...")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            dc = self.config_manager.get("client_server"); db = dc["remote_dir"]
            ssh = SSHManager(dc["host"],dc["user"],dc["password"])
            ok, msg = ssh.connect()
            if not ok: self.log_message(f"Ошибка: {msg}", True); return
            script = f"""import os,json,blake3
d='{db}/mods';mp='{db}/manifest.json'
with open(mp,'r') as f: m=json.load(f)
m['files']=[f for f in m.get('files',[]) if not f.get('path','').startswith('mods/')]
for r,_,fs in os.walk(d):
 for f in fs:
  if f.endswith('.jar') and not f.startswith('.'):
   p=os.path.join(r,f);h=blake3.blake3();sz=0
   with open(p,'rb') as x:
    while c:=x.read(8192): h.update(c); sz+=len(c)
   rl=os.path.relpath(p,d).replace('\\\\','/')
   m['files'].append({{"path":"mods/"+rl,"url":"https://"+os.path.basename('{db}')+"/mods/"+rl,"hash":"b3:"+h.hexdigest(),"size":sz,"type":"file"}})
with open(mp,'w') as f: json.dump(m,f,indent=4)
print("OK")
"""
            b = base64.b64encode(script.encode()).decode()
            ssh.execute_command(f'python3 -c "import base64,sys;exec(base64.b64decode(sys.argv[1]).decode(\'utf-8\'))" {b}')
            ssh.disconnect()
            self.log_message("Manifest успешно пересобран!")
        threading.Thread(target=t, daemon=True).start()


    # ═══════════════════════════════════════════════════════════
    #  GAME CONSOLE
    # ═══════════════════════════════════════════════════════════
    _console_checked = False
    _live_ssh = None
    _stream_channel = None

    def _build_game_console(self):
        """
        [RU] Функция _build_game_console.
        [EN] Function _build_game_console.
        """
        page = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        self._pages["console"] = page

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        self.srv_status = ctk.CTkLabel(header, text="Подключение к серверу...", font=self.FONT_L, text_color=C["text_dim"])
        self.srv_status.pack(side="left")
        
        self.console_btns = ctk.CTkFrame(header, fg_color="transparent")
        self.console_btns.pack(side="right")

        term = ctk.CTkFrame(page, fg_color=C["section"], corner_radius=12)
        term.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.term_out = ctk.CTkTextbox(term, font=self.MONO, fg_color=C["section"], text_color=C["text"], border_width=0)
        self.term_out.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        inp = ctk.CTkFrame(term, fg_color="transparent", height=40)
        inp.pack(fill="x", padx=15, pady=15)
        inp.pack_propagate(False)
        
        ctk.CTkLabel(inp, text=">", font=self.MONO, text_color=C["text_dim"]).pack(side="left", padx=(0, 10))
        self.cmd_entry = ctk.CTkEntry(inp, font=self.MONO, fg_color=C["bg"], border_width=0, corner_radius=8, text_color=C["text"], placeholder_text="Ввод команды для screen...")
        self.cmd_entry.pack(side="left", fill="both", expand=True)
        self.cmd_entry.bind("<Return>", self._run_cmd)

    def _tlog(self, text):
        """
        [RU] Функция _tlog.
        [EN] Function _tlog.
        """
        self.term_out.insert("end", text + "\n")
        self.term_out.see("end")

    def _ensure_ssh(self):
        """
        [RU] Функция _ensure_ssh.
        [EN] Function _ensure_ssh.
        """
        if self._live_ssh and self._live_ssh.ssh and self._live_ssh.ssh.get_transport() and self._live_ssh.ssh.get_transport().is_active():
            return True, ""
        gc = self.config_manager.get("game_server")
        if not gc.get("host"): return False, "Хост не указан в настройках"
        self._live_ssh = SSHManager(gc["host"], gc["user"], gc["password"])
        ok, msg = self._live_ssh.connect()
        return ok, msg

    def _start_live_stream(self):
        """
        [RU] Функция _start_live_stream.
        [EN] Function _start_live_stream.
        """
        if getattr(self, "_stream_running", False): return
        self._stream_running = True
        self._tlog("[Система] Подключение к консоли (ssh)...")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            ok, msg = self._ensure_ssh()
            if not ok: 
                self._tlog(f"[Ошибка] SSH сбой: {msg}")
                self._stream_running = False
                self.srv_status.configure(text="Сервер недоступен", text_color=C["red"])
                return
                
            gc = self.config_manager.get("game_server")
            try:
                transport = self._live_ssh.ssh.get_transport()
                self._stream_channel = transport.open_session()
                self._tlog("[Система] Чтение логов установлено. Ожидание вывода...")
                
                stdin, stdout, stderr = self._live_ssh.ssh.exec_command(f"tail -n 100 {gc['remote_dir']}/logs/latest.log", timeout=5)
                initial_lines = stdout.read().decode('utf-8', errors='ignore')
                if initial_lines:
                    self.term_out.insert("end", initial_lines)
                    self.term_out.see("end")
                    
                self._stream_channel.settimeout(1.0)
                self._stream_channel.exec_command(f"tail -n 0 -F {gc['remote_dir']}/logs/latest.log")
                
                while self._stream_running:
                    try:
                        if self._stream_channel.recv_ready():
                            data = self._stream_channel.recv(4096).decode("utf-8", errors="ignore")
                            if data:
                                self.term_out.insert("end", data)
                                self.term_out.see("end")
                    except Exception as e:
                        if "timed out" not in str(e).lower():
                            raise e
                            
                    if self._stream_channel.exit_status_ready():
                        self._tlog("[Система] Поток лога закрылся.")
                        break
                        
                    time.sleep(0.5)
            except Exception as e:
                self._tlog(f"[Система] Ошибка чтения потока: {str(e)}")
            finally:
                if self._stream_channel: self._stream_channel.close()
                self._stream_running = False
        threading.Thread(target=t, daemon=True).start()

    def _run_cmd(self, event=None):
        """
        [RU] Функция _run_cmd.
        [EN] Function _run_cmd.
        """
        cmd = self.cmd_entry.get().strip()
        if not cmd: return
        self.cmd_entry.delete(0, "end")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            ok, _ = self._ensure_ssh()
            if not ok: return
            safe_cmd = cmd.replace('"', '\\"')
            s_name = self.config_manager.get("game_server", "screen_name")
            self._live_ssh.execute_command(f'screen -S {s_name} -X stuff "{safe_cmd}\\n"')
        threading.Thread(target=t, daemon=True).start()

    def _check_server_status(self):
        """
        [RU] Функция _check_server_status.
        [EN] Function _check_server_status.
        """
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            ok, msg = self._ensure_ssh()
            if not ok: self._set_srv("error", msg); return
            s_name = self.config_manager.get("game_server", "screen_name")
            ok_cmd, out = self._live_ssh.execute_command(f"screen -ls | grep {s_name}")
            if out and s_name in out: self._set_srv("running")
            else: self._set_srv("stopped")
        threading.Thread(target=t, daemon=True).start()

    def _set_srv(self, state, msg=""):
        """
        [RU] Функция _set_srv.
        [EN] Function _set_srv.
        """
        for w in self.console_btns.winfo_children(): w.destroy()
        if state == "running":
            self.srv_status.configure(text="Игровой сервер РАБОТАЕТ", text_color=C["green"])
            ctk.CTkButton(self.console_btns, text="Перезапустить сервер", width=160, height=36, corner_radius=18, font=self.FONT_B, fg_color=C["section"], hover_color=C["hover"], text_color=C["text"], command=self._restart).pack(side="left", padx=10)
            ctk.CTkButton(self.console_btns, text="Остановить сервер", width=150, height=36, corner_radius=18, font=self.FONT_B, fg_color=C["red"], hover_color=C["red_h"], command=self._stop).pack(side="left", padx=0)
        elif state == "stopped":
            self.srv_status.configure(text="Игровой сервер ОСТАНОВЛЕН", text_color=C["text_dim"])
            ctk.CTkButton(self.console_btns, text="Запустить сервер", width=150, height=36, corner_radius=18, font=self.FONT_B, fg_color=C["accent"], hover_color=C["accent_h"], command=self._start).pack(side="left", padx=0)
        else:
            self.srv_status.configure(text=f"Ошибка: {msg}", text_color=C["red"])

    def _start(self):
        """
        [RU] Функция _start.
        [EN] Function _start.
        """
        self._tlog("[Система] Отправка команды запуска сервера...")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            if not self._ensure_ssh()[0]: return
            gc = self.config_manager.get("game_server")
            self._live_ssh.execute_command(f"cd {gc['remote_dir']} && ./start.sh &")
            time.sleep(3); self._check_server_status()
        threading.Thread(target=t, daemon=True).start()

    def _stop(self):
        """
        [RU] Функция _stop.
        [EN] Function _stop.
        """
        if not messagebox.askyesno("Остановка", "Вы уверены, что хотите остановить игровой сервер?"): return
        self._tlog("[Система] Отправка команды остановки сервера...")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            if not self._ensure_ssh()[0]: return
            s_name = self.config_manager.get("game_server", "screen_name")
            self._live_ssh.execute_command(f'screen -S {s_name} -X stuff "stop\\n"')
            time.sleep(5); self._check_server_status()
        threading.Thread(target=t, daemon=True).start()

    def _restart(self):
        """
        [RU] Функция _restart.
        [EN] Function _restart.
        """
        if not messagebox.askyesno("Перезапуск", "Отправить сервер в перезагрузку?"): return
        self._tlog("[Система] Рестарт сервера...")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            if not self._ensure_ssh()[0]: return
            s_name = self.config_manager.get("game_server", "screen_name")
            self._live_ssh.execute_command(f'screen -S {s_name} -X stuff "stop\\n"')
            time.sleep(10)
            gc = self.config_manager.get("game_server")
            self._live_ssh.execute_command(f"cd {gc['remote_dir']} && ./start.sh &")
            time.sleep(3); self._check_server_status()
        threading.Thread(target=t, daemon=True).start()

    # ═══════════════════════════════════════════════════════════
    #  BACKUPS
    # ═══════════════════════════════════════════════════════════
    def _build_backups(self):
        """
        [RU] Функция _build_backups.
        [EN] Function _build_backups.
        """
        page = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        self._pages["backups"] = page

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(header, text="Резервные Копии", font=self.FONT_XL, text_color=C["text"]).pack(side="left")
        
        up_btn = ctk.CTkButton(header, text="Создать бекап сервера", width=160, height=36, corner_radius=18,
                               font=self.FONT_B, fg_color=C["accent"], hover_color=C["accent_h"], text_color="#FFFFFF", command=self._create_backup)
        up_btn.pack(side="right", padx=0)
        
        ref_btn = ctk.CTkButton(header, text="Обновить список", width=130, height=36, corner_radius=18,
                                font=self.FONT_B, fg_color=C["section"], hover_color=C["hover"], text_color=C["text"], command=self.refresh_backups)
        ref_btn.pack(side="right", padx=10)
        
        self.backup_prog_frame = ctk.CTkFrame(page, fg_color="transparent")
        self.backup_lbl = ctk.CTkLabel(self.backup_prog_frame, text="Прогресс: 0% | Оценка времени: --:--", font=self.FONT_B, text_color=C["text"])
        self.backup_lbl.pack(anchor="w", padx=20, pady=(5, 0))
        self.backup_pb = ctk.CTkProgressBar(self.backup_prog_frame, progress_color=C["accent"], height=10)
        self.backup_pb.set(0)
        self.backup_pb.pack(fill="x", padx=20, pady=5)
        self.backup_log = ctk.CTkTextbox(self.backup_prog_frame, height=80, font=self.MONO, fg_color=C["section"], text_color=C["text_dim"])
        self.backup_log.pack(fill="x", padx=20, pady=(0, 10))
        
        list_frame = ctk.CTkFrame(page, fg_color=C["section"], corner_radius=12)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.tree_backups = ttk.Treeview(list_frame, columns=("file", "size", "date"), show="headings", style="NB.Treeview")
        self.tree_backups.heading("file", text="Имя архива")
        self.tree_backups.heading("size", text="Размер")
        self.tree_backups.heading("date", text="Дата")
        self.tree_backups.column("file", width=400)
        self.tree_backups.column("size", width=100, anchor="e")
        self.tree_backups.column("date", width=150, anchor="center")
        self.tree_backups.pack(fill="both", expand=True, padx=15, pady=15)

    def refresh_backups(self):
        """
        [RU] Функция refresh_backups.
        [EN] Function refresh_backups.
        """
        for i in self.tree_backups.get_children(): self.tree_backups.delete(i)
        self.log_message("[Система] Обновление списка бекапов...")
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            gc = self.config_manager.get("game_server")
            ssh = SSHManager(gc["host"], gc["user"], gc["password"])
            ok, msg = ssh.connect()
            if not ok: self.log_message(f"Бекапы недоступны:\n{msg}", True); return
            
            ok, out = ssh.execute_command("screen -ls | grep admin_backup")
            if out and "admin_backup" in out:
                self.after(0, self._start_monitor_backup)
                
            b_dir = f"{gc['remote_dir']}/backups"
            ssh.execute_command(f"mkdir -p {b_dir}")
            ok, out = ssh.execute_command(f"ls -lh --time-style=long-iso {b_dir}")
            if ok and out:
                for line in out.strip().split('\n'):
                    if line.startswith('total'): continue
                    parts = line.split()
                    if len(parts) >= 8:
                        size = parts[4]
                        date = f"{parts[5]} {parts[6]}"
                        name = " ".join(parts[7:])
                        if name.endswith('.7z') or name.endswith('.zip') or name.endswith('.tar.gz'):
                            self.tree_backups.insert("", "end", values=(name, size, date))
            ssh.disconnect()
            self.log_message("[Система] Список бекапов успешно получен.")
        threading.Thread(target=t, daemon=True).start()

    def _create_backup(self):
        """
        [RU] Функция _create_backup.
        [EN] Function _create_backup.
        """
        if not messagebox.askyesno("Бекап", "Запустить создание резервной копии сервера? Это может занять время и снизить производительность (TPS)."): return
        
        self.log_message("Запущено создание резервной копии сервера. Ждем завершения...")
        
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            gc = self.config_manager.get("game_server")
            ssh = SSHManager(gc["host"], gc["user"], gc["password"], timeout=300) # Long timeout for 7z
            ok, msg = ssh.connect()
            if not ok:
                self.log_message(f"Ошибка бекапа: {msg}", True)
                return
                
            ok_7z, out_7z = ssh.execute_command("which 7z")
            if not ok_7z or not out_7z.strip():
                self.log_message("Ошибка: 7z не установлен на сервере. Установите: apt install p7zip-full", True)
                ssh.disconnect()
                return
                
            ok_scr, out_scr = ssh.execute_command("which screen")
            if not ok_scr or not out_scr.strip():
                self.log_message("Ошибка: screen не установлен на сервере. Установите: apt install screen", True)
                ssh.disconnect()
                return
                
            import datetime
            date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
            b_dir = f"{gc['remote_dir']}/backups"
            b_name = f"backup_{date_str}.7z"
            
            excl = self.config_manager.get("backups", "excluded_folders")
            args = self.config_manager.get("backups", "7z_args")
            
            excl_cmd = " ".join([f"-x!{f.strip()}" for f in excl.split(",") if f.strip()])
            
            log_file = f"{gc['remote_dir']}/backups/backup_progress.log"
            ssh.execute_command(f"rm -f {log_file}")
            
            cmd = f"cd {gc['remote_dir']} && 7z a -bsp1 {args} {b_dir}/{b_name} ./* {excl_cmd} >> {log_file} 2>&1"
            screen_cmd = f"screen -dmS admin_backup bash -c '{cmd}'"
            
            self.log_message(f"Сжатие файлов в {b_name} (Фоновый процесс)...")
            ssh.execute_command(screen_cmd)
            ssh.disconnect()
            
            self.after(0, self._start_monitor_backup)
            
        threading.Thread(target=t, daemon=True).start()

    _backup_monitoring = False

    def _start_monitor_backup(self):
        """
        [RU] Функция _start_monitor_backup.
        [EN] Function _start_monitor_backup.
        """
        if self._backup_monitoring: return
        self._backup_monitoring = True
        self.backup_prog_frame.pack(fill="x", before=self.tree_backups.master)
        
        def t():
            """
            [RU] Функция t.
            [EN] Function t.
            """
            gc = self.config_manager.get("game_server")
            ssh = SSHManager(gc["host"], gc["user"], gc["password"])
            if not ssh.connect()[0]:
                self._backup_monitoring = False
                return
            
            log_file = f"{gc['remote_dir']}/backups/backup_progress.log"
            start_time = time.time()
            last_pct_recorded = 0
            last_logged_line = ""
            
            while self._backup_monitoring:
                ok, ls_out = ssh.execute_command("screen -ls | grep admin_backup")
                is_running = (ls_out and "admin_backup" in ls_out)
                
                ok, log_out = ssh.execute_command(f"tail -c 2000 {log_file} 2>/dev/null")
                if log_out:
                    lines = log_out.replace('\\r', '\\n').split('\\n')
                    last_pct = last_pct_recorded
                    files_added = []
                    for line in lines:
                        if "command not found" in line.lower() or "error" in line.lower() or "не найден" in line.lower():
                            if line.strip() and line.strip() not in files_added:
                                files_added.append(f"ОШИБКА: {line.strip()}")
                        m = re.search(r'(\d+)%\s+(.*)', line)
                        if m:
                            pct = int(m.group(1))
                            last_pct = pct
                            fname = m.group(2).strip()
                            fname = re.sub(r'^\\d+\\s*\\+\\s*', '', fname)
                            if fname and fname != "U" and not fname.startswith("U "):
                                files_added.append(fname)
                    
                    if last_pct > 0:
                        last_pct_recorded = last_pct
                        elapsed = time.time() - start_time
                        eta_sec = (elapsed / last_pct) * (100 - last_pct) if last_pct > 0 else 0
                        mins, secs = divmod(int(eta_sec), 60)
                        
                        def update_ui(p=last_pct, ms=mins, ss=secs, fa=files_added):
                            nonlocal last_logged_line
                            self.backup_pb.set(p / 100.0)
                            self.backup_lbl.configure(text=f"Прогресс: {p}% | Оценка времени: {ms:02d}:{ss:02d}")
                            if fa:
                                new_line = fa[-1]
                                if new_line != last_logged_line:
                                    self.backup_log.insert("end", new_line + "\n")
                                    self.backup_log.see("end")
                                    last_logged_line = new_line
                                
                        self.after(0, update_ui)
                
                if not is_running:
                    break
                time.sleep(2)
                
            ssh.disconnect()
            self._backup_monitoring = False
            self.after(0, self._finish_monitor)
            
        threading.Thread(target=t, daemon=True).start()

    def _finish_monitor(self):
        """
        [RU] Функция _finish_monitor.
        [EN] Function _finish_monitor.
        """
        self.backup_prog_frame.pack_forget()
        self.backup_pb.set(0)
        self.backup_log.delete("1.0", "end")
        self.log_message("Бекап завершен.")
        self.refresh_backups()

    # ═══════════════════════════════════════════════════════════
    #  SETTINGS
    # ═══════════════════════════════════════════════════════════
    def _build_settings(self):
        """
        [RU] Функция _build_settings.
        [EN] Function _build_settings.
        """
        page = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        self._pages["settings"] = page
        
        scroll = ctk.CTkScrollableFrame(page, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        self._sv = {}

        header = ctk.CTkFrame(scroll, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text="Настройки", font=self.FONT_XL, text_color=C["text"]).pack(anchor="w")

        self._scard(scroll, "Клиент-сервер", "client_server", [("name","Название",False),("host","Хост",False),("user","Логин",False),("password","Пароль",True),("remote_dir","Путь к сайту",False)])
        self._scard(scroll, "Игровой сервер", "game_server", [("name","Название",False),("host","Хост",False),("user","Логин",False),("password","Пароль",True),("remote_dir","Путь к серверу",False), ("screen_name", "Имя Screen", False)])

        self._scard(scroll, "Настройки бекапа", "backups", [("excluded_folders", "Исключения (через запятую)", False), ("7z_args", "Аргументы 7z", False)])

        lc = ctk.CTkFrame(scroll, fg_color=C["section"], corner_radius=12)
        lc.pack(fill="x", pady=10)
        ctk.CTkLabel(lc, text="Локальные файлы", font=self.FONT_L, text_color=C["text"]).pack(anchor="w", padx=20, pady=(20, 10))
        r = ctk.CTkFrame(lc, fg_color="transparent")
        r.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(r, text="Папка модов:", width=180, anchor="w", text_color=C["text_dim"], font=self.FONT).pack(side="left")
        v = ctk.StringVar(value=self.config_manager.get("paths","local_mods_dir") or "mods")
        self._sv[("paths","local_mods_dir")] = v
        ctk.CTkEntry(r, textvariable=v, fg_color=C["bg"], border_width=0, font=self.FONT, height=36, corner_radius=8, text_color=C["text"]).pack(side="left", fill="x", expand=True)

        btns = ctk.CTkFrame(scroll, fg_color="transparent")
        btns.pack(pady=(20, 20))
        ctk.CTkButton(btns, text="Сохранить", height=40, width=150, corner_radius=20, font=self.FONT_B, fg_color=C["accent"], hover_color=C["accent_h"], command=self._save_settings).pack(side="left", padx=10)
        self.btn_reset = ctk.CTkButton(btns, text="Сбросить настройки", height=40, width=150, corner_radius=20, font=self.FONT_B, fg_color=C["red"], hover_color=C["red_h"], command=self._start_reset_timer)
        self.btn_reset.pack(side="left", padx=10)
        self._reset_timer = None
        self._reset_count = 0

    def _start_reset_timer(self):
        """
        [RU] Функция _start_reset_timer.
        [EN] Function _start_reset_timer.
        """
        if self._reset_timer:
            self.after_cancel(self._reset_timer)
            self._reset_timer = None
            self.btn_reset.configure(text="Сбросить настройки", fg_color=C["red"], hover_color=C["red_h"])
            return
            
        self._reset_count = 10
        self.btn_reset.configure(fg_color=C["orange"], hover_color="#FF7B1A")
        self._tick_reset()
        
    def _tick_reset(self):
        """
        [RU] Функция _tick_reset.
        [EN] Function _tick_reset.
        """
        if self._reset_count <= 0:
            self._do_reset()
            return
            
        self.btn_reset.configure(text=f"Отменить сброс ({self._reset_count})")
        self._reset_count -= 1
        self._reset_timer = self.after(1000, self._tick_reset)
        
    def _do_reset(self):
        """
        [RU] Функция _do_reset.
        [EN] Function _do_reset.
        """
        self._reset_timer = None
        self.btn_reset.configure(text="Сбросить настройки", fg_color=C["red"], hover_color=C["red_h"])
        import shutil
        cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin_settings.json")
        if os.path.exists(cfg): os.remove(cfg)
        self.config_manager = ConfigManager()
        self.log_message("Настройки полностью сброшены!")
        self.after(0, lambda: messagebox.showinfo("Сброс", "Настройки сброшены! Программа закроется."))
        self.after(500, self.destroy)

    def _scard(self, parent, title, section, fields):
        """
        [RU] Функция _scard.
        [EN] Function _scard.
        """
        card = ctk.CTkFrame(parent, fg_color=C["section"], corner_radius=12)
        card.pack(fill="x", pady=10)
        ctk.CTkLabel(card, text=title, font=self.FONT_L, text_color=C["text"]).pack(anchor="w", padx=20, pady=(20, 10))
        for key, label, pw in fields:
            r = ctk.CTkFrame(card, fg_color="transparent")
            r.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(r, text=label, width=180, anchor="w", text_color=C["text_dim"], font=self.FONT).pack(side="left")
            var = ctk.StringVar(value=self.config_manager.get(section, key) or "")
            self._sv[(section, key)] = var
            ctk.CTkEntry(r, textvariable=var, show="•" if pw else "", fg_color=C["bg"], border_width=0, font=self.FONT, height=36, corner_radius=8, text_color=C["text"]).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(card, text="", height=10).pack()

    def _save_settings(self):
        """
        [RU] Функция _save_settings.
        [EN] Function _save_settings.
        """
        for (s, k), v in self._sv.items(): self.config_manager.set(s, k, v.get())
        self.log_message("Настройки успешно сохранены и применены.")
        if getattr(self, "_stream_running", False):
            self._stream_running = False
            self.after(500, self._start_live_stream)
        self.scan_mods()

if __name__ == "__main__":
    app = AdminPanel()
    app.mainloop()
