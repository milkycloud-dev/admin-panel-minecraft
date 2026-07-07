import os
import re
import threading
import json
import sys
import subprocess
import base64
import time
import ctypes
import shutil
import datetime
import inspect

try:
    import flet as ft
    import paramiko
    import blake3
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "blake3", "flet", "Pillow"])
    import flet as ft
    import paramiko
    import blake3

# Flet >=0.27 renamed icons/colors modules to Icons/Colors enums.
if hasattr(ft, "Icons") and not hasattr(ft.icons, "BUILD"):
    ft.icons = ft.Icons
if hasattr(ft, "Colors") and not hasattr(ft, "colors"):
    ft.colors = ft.Colors

# Flet >=0.80: ElevatedButton deprecated — alias to Button.
if hasattr(ft, "Button"):
    ft.ElevatedButton = ft.Button

# Flet >=0.80: padding.only removed — use Padding().
if hasattr(ft, "Padding") and not hasattr(ft.padding, "only"):
    def _padding_only(left=0, top=0, right=0, bottom=0):
        return ft.Padding(left=left, top=top, right=right, bottom=bottom)
    ft.padding.only = _padding_only

def schedule_ui(page: ft.Page, fn):
    """Run UI callback on the Flet event loop (thread-safe)."""
    async def _task():
        fn()
        try:
            page.update()
        except Exception:
            pass
    try:
        page.run_task(_task)
    except Exception:
        try:
            fn()
            page.update()
        except Exception:
            pass

def launch_flet_app(target, assets_dir="."):
    """Start Flet app using run() on 0.80+ or app() on older versions."""
    launcher = getattr(ft, "run", None) or ft.app
    launcher(target, assets_dir=assets_dir)

def configure_page_window(page, icon="icon.png", width=1300, height=800, min_width=1000, min_height=650):
    """Apply window settings for both legacy and modern Flet Page APIs."""
    window = getattr(page, "window", None)
    if window is not None:
        window.icon = icon
        window.width = width
        window.height = height
        window.min_width = min_width
        window.min_height = min_height
        return
    for attr, value in {
        "window_icon": icon,
        "window_width": width,
        "window_height": height,
        "window_min_width": min_width,
        "window_min_height": min_height,
    }.items():
        if hasattr(page, attr):
            setattr(page, attr, value)

def close_application(page):
    """Close desktop app on legacy and modern Flet versions."""
    window = getattr(page, "window", None)
    if window is not None and hasattr(window, "close"):
        async def _close_window():
            await window.close()
        page.run_task(_close_window)
        return
    if hasattr(page, "window_destroy"):
        page.window_destroy()

def register_file_picker(page: ft.Page, picker: ft.FilePicker, *, mounted: bool = False):
    """Attach FilePicker via services registry (Flet 0.80+) or overlay (legacy)."""
    try:
        from flet.controls.services.service import Service
        if isinstance(picker, Service):
            if mounted:
                page._services.register_service(picker)
            else:
                registry = page._services
                with registry._lock:
                    if picker not in registry._services:
                        registry._services.append(picker)
            return
    except Exception:
        pass
    if picker not in page.overlay:
        page.overlay.append(picker)

def pick_jar_files(page: ft.Page, picker: ft.FilePicker, callback):
    """Open jar file picker using sync or async Flet API."""
    if inspect.iscoroutinefunction(getattr(picker, "pick_files", None)):
        async def _pick():
            try:
                picked = await picker.pick_files(
                    allow_multiple=True,
                    allowed_extensions=["jar"],
                    file_type=ft.FilePickerFileType.CUSTOM,
                )
            except Exception:
                return
            if picked:
                callback(picked)
        page.run_task(_pick)
        return

    def _on_result(event):
        if event.files:
            callback(event.files)

    picker.on_result = _on_result
    picker.pick_files(allow_multiple=True, allowed_extensions=["jar"])

def pick_directory(page: ft.Page, picker: ft.FilePicker, title: str, callback):
    """Open directory picker using sync or async Flet API."""
    if inspect.iscoroutinefunction(getattr(picker, "get_directory_path", None)):
        async def _pick():
            try:
                path = await picker.get_directory_path(dialog_title=title)
            except Exception:
                return
            if path:
                callback(path)
        page.run_task(_pick)
        return

    def _on_result(event):
        if event.path:
            callback(event.path)

    picker.on_result = _on_result
    picker.get_directory_path(title)

def pick_json_file(page: ft.Page, picker: ft.FilePicker, title: str, callback):
    """Open JSON file picker for config import."""
    if inspect.iscoroutinefunction(getattr(picker, "pick_files", None)):
        async def _pick():
            try:
                picked = await picker.pick_files(
                    dialog_title=title,
                    allow_multiple=False,
                    allowed_extensions=["json"],
                    file_type=ft.FilePickerFileType.CUSTOM,
                )
            except Exception:
                return
            if picked:
                callback(picked[0].path)
        page.run_task(_pick)
        return

    def _on_result(event):
        if event.files:
            callback(event.files[0].path)

    picker.on_result = _on_result
    picker.pick_files(allow_multiple=False, allowed_extensions=["json"])

def save_json_file(page: ft.Page, picker: ft.FilePicker, title: str, default_name: str, callback):
    """Save JSON file dialog for config export."""
    if inspect.iscoroutinefunction(getattr(picker, "save_file", None)):
        async def _save():
            try:
                path = await picker.save_file(
                    dialog_title=title,
                    file_name=default_name,
                    allowed_extensions=["json"],
                    file_type=ft.FilePickerFileType.CUSTOM,
                )
            except Exception:
                return
            if path:
                callback(path)
        page.run_task(_save)
        return

    def _on_result(event):
        if event.path:
            callback(event.path)

    picker.on_result = _on_result
    picker.save_file(file_name=default_name)

from config_manager import ConfigManager
from ssh_manager import SSHManager
from index_manifest_builder import remote_rebuild_script
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

def fmt_size(s):
    if s < 1024: return f"{s} B"
    elif s < 1048576: return f"{s//1024} KB"
    else: return f"{s/1048576:.1f} MB"

def mod_base(f):
    name = f.rsplit('.jar', 1)[0]
    m = re.match(r'^([a-zA-Z_\-]+?)[\-_]?\d', name)
    return m.group(1).rstrip('-_').lower() if m else name.lower()

class Logger:
    """Log panel helper — plain object, not a Flet control (avoids .page mount errors)."""

    def __init__(self, page: ft.Page):
        self._page = page
        self.lv = ft.ListView(expand=True, spacing=5, auto_scroll=True)
        self.widget = ft.Container(
            height=160,
            content=ft.Column([
                ft.Text("Системный лог", size=12, color=C["text_dim"], weight="bold"),
                self.lv,
            ], spacing=4, expand=True),
            bgcolor=C["section"],
            padding=10,
            border_radius=0,
        )
        self._ready = False

    def mark_mounted(self):
        self._ready = True

    def log(self, msg, is_error=False):
        t = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = "[ОШИБКА] " if is_error else "[СИСТЕМА] "
        color = C["red"] if is_error else C["text_dim"]
        text = ft.Text(f"[{t}] {prefix}{msg}", color=color, font_family="Consolas", size=12)

        def _append():
            self.lv.controls.append(text)
            if len(self.lv.controls) > 400:
                del self.lv.controls[0]

        if self._ready:
            schedule_ui(self._page, _append)
        else:
            _append()

class SyncTab(ft.Container):
    def __init__(self, ctx):
        super().__init__(expand=True, padding=20)
        self.ctx = ctx
        self.client_mods_cache = {}
        self.game_mods_cache = {}

        self.mods_lv = ft.ListView(spacing=2, expand=True)

        self.file_picker = ft.FilePicker()

        cs_conf = self.ctx.config_manager.get("client_server")
        gs_conf = self.ctx.config_manager.get("game_server")

        self.content = ft.Column([
            ft.Row([
                ft.Text("Управление Модами", size=24, color=C["text"], weight="bold"),
                ft.Container(expand=True),
                ft.ElevatedButton("Собрать Index", icon=ft.icons.BUILD, bgcolor=C["orange"], color=ft.colors.WHITE, on_click=lambda e: self.rebuild_index_only(), style=ft.ButtonStyle(padding=10)),
                ft.ElevatedButton("Пересканировать", bgcolor=C["accent"], color=ft.colors.WHITE, on_click=lambda e: self.scan_mods())
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(
                bgcolor=C["section"], border_radius=12, padding=15, expand=True,
                content=ft.Column([
                    ft.Row([
                        self._make_panel_header(cs_conf.get("name", "Клиент-сервер"), cs_conf.get("host", "Не настроен"), "client_server"),
                        ft.VerticalDivider(width=20, color=ft.colors.TRANSPARENT),
                        self._make_panel_header(gs_conf.get("name", "Игровой сервер"), gs_conf.get("host", "Не настроен"), "game_server"),
                    ]),
                    ft.Row([
                        ft.Container(content=ft.Text("Мод", weight="bold"), width=250),
                        ft.Container(content=ft.Text("Размер", weight="bold"), width=80),
                        ft.Container(content=ft.Text("Статус", weight="bold"), expand=True),
                        ft.Container(width=40),
                        ft.VerticalDivider(width=20, color=C["bg"]),
                        ft.Container(content=ft.Text("Мод", weight="bold"), width=250),
                        ft.Container(content=ft.Text("Размер", weight="bold"), width=80),
                        ft.Container(content=ft.Text("Статус", weight="bold"), expand=True),
                        ft.Container(width=40)
                    ]),
                    self.mods_lv
                ])
            )
        ], expand=True, spacing=20)

    def _remote_mods_dir(self, server_key):
        return self.ctx.sync_manager.get_remote_mods_dir(server_key)

    def _local_mods_dir(self):
        _, path = self.ctx.sync_manager.get_local_mods()
        return path

    def _make_panel_header(self, title, ip, server_key):
        btns = [
            ft.ElevatedButton("Скачать все", icon=ft.icons.DOWNLOAD, on_click=lambda e, sk=server_key: self._dl_all(sk), style=ft.ButtonStyle(padding=10)),
            ft.ElevatedButton("Загрузить", icon=ft.icons.UPLOAD, on_click=lambda e, sk=server_key: self._trigger_upload_local(sk), style=ft.ButtonStyle(padding=10))
        ]
        return ft.Column([
            ft.Text(title, size=18, color=C["text"], weight="bold", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(ip, size=12, color=C["text_dim"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Row(btns, wrap=True)
        ], expand=True)

    def _trigger_upload_local(self, server_key):
        self._upload_target = server_key
        pick_jar_files(self.ctx.page, self.file_picker, self._on_local_files_picked)

    def _on_local_files_picked(self, files):
        if not files:
            return
        target_server = self._upload_target
        self.ctx.logger.log(f"Загрузка {len(files)} модов на {target_server}...")
        def t():
            c = self.ctx.config_manager.get(target_server)
            s = SSHManager(c["host"], c["user"], c["password"])
            ok, msg = s.connect()
            if not ok: self.ctx.logger.log(f"Ошибка: {msg}", True); return
            for f in files:
                s.upload_file(f.path, f"{self._remote_mods_dir(server_key)}/{f.name}")
            s.disconnect()
            self.ctx.logger.log(f"Загружено {len(files)} модов на {target_server}.")
            self.scan_mods()
        threading.Thread(target=t, daemon=True).start()

    def _on_local_file_picked(self, e):
        if not e.files: return
        self._on_local_files_picked(e.files)

    def _make_mod_cell(self, filename, size_str, status_str, color, server_key, index=0):
        if not filename:
            return ft.Container(expand=True)
        other = "game_server" if server_key == "client_server" else "client_server"
        c1 = self.ctx.config_manager.get(server_key, "name")
        c2 = self.ctx.config_manager.get(other, "name")
        items = [
            ft.PopupMenuItem(content=f"Перебросить на {c2}", on_click=lambda e, _sk=server_key, _ot=other, _fn=filename: self._transfer(_sk, _ot, _fn)),
            ft.PopupMenuItem(content="Скачать локально", on_click=lambda e, _sk=server_key, _fn=filename: self._dl_local(_sk, _fn)),
            ft.PopupMenuItem(content=f"Удалить с {c1}", on_click=lambda e, _sk=server_key, _fn=filename: self._delete(_sk, _fn))
        ]

        return ft.Container(
            content=ft.Row([
                ft.Container(content=ft.Text(filename, color=color, size=13, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, tooltip=filename), width=250),
                ft.Container(content=ft.Text(size_str, color=color, size=13, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), width=80),
                ft.Container(content=ft.Text(status_str, color=color, size=13, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), expand=True),
                ft.PopupMenuButton(items=items, icon=ft.icons.MORE_VERT, tooltip="Действия")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor=ft.colors.WHITE10 if index % 2 == 0 else ft.colors.TRANSPARENT,
            padding=ft.padding.only(left=5, right=5),
            border_radius=4,
            expand=True
        )

    def scan_mods(self):
        page = self.ctx.page
        schedule_ui(page, lambda: self.mods_lv.controls.clear())

        def worker():
            self.ctx.logger.log("[Система] Сканирование модов на серверах...")

            cm, c_err = None, None
            for attempt in range(3):
                cm, c_err = self.ctx.sync_manager.get_remote_mods("client_server")
                if c_err and "Authentication failed" in c_err:
                    self.ctx.logger.log("Неверный логин или пароль для Клиент-сервера.", True)
                    break
                if c_err:
                    if attempt < 2:
                        self.ctx.logger.log(f"Ошибка Клиент: {c_err.strip()}. Переподключение через 3с...", True)
                        time.sleep(3)
                    else:
                        self.ctx.logger.log(f"Ошибка Клиент: {c_err.strip()}. Пропуск.", True)
                    break
                break

            gm, g_err = None, None
            for attempt in range(3):
                gm, g_err = self.ctx.sync_manager.get_remote_mods("game_server")
                if g_err and "Authentication failed" in g_err:
                    self.ctx.logger.log("Неверный логин или пароль для Игрового сервера.", True)
                    break
                if g_err:
                    if attempt < 2:
                        self.ctx.logger.log(f"Ошибка Игровой: {g_err.strip()}. Переподключение через 3с...", True)
                        time.sleep(3)
                    else:
                        self.ctx.logger.log(f"Ошибка Игровой: {g_err.strip()}. Пропуск.", True)
                    break
                break

            cm = cm or {}
            gm = gm or {}
            self.client_mods_cache = cm
            self.game_mods_cache = gm
            schedule_ui(page, lambda: self._render_mod_scan(cm, gm))
            self.ctx.logger.log(f"Клиент-сервер: {len(cm)} модов, Игровой: {len(gm)} модов.")
            self.ctx.logger.log("[Система] Списки модов обновлены и сверены.")

        page.run_thread(worker)

    def _render_mod_scan(self, cm, gm):
        cb = {}
        for f in cm:
            cb.setdefault(mod_base(f), []).append(f)
        gb = {}
        for f in gm:
            gb.setdefault(mod_base(f), []).append(f)
        matched, partial, c_only, g_only = [], [], [], []
        pc, pg = set(), set()

        for f in sorted(set(cm) & set(gm), key=str.lower):
            if cm[f]["size"] == gm[f]["size"]:
                hash_match = True
                if cm[f].get("hash") and gm[f].get("hash") and cm[f]["hash"] != gm[f]["hash"]:
                    hash_match = False
                matched.append((f, f, cm[f]["size"], gm[f]["size"], hash_match))
            else:
                partial.append((f, f, cm[f]["size"], gm[f]["size"]))
            pc.add(f)
            pg.add(f)

        for b, cfs in sorted(cb.items()):
            if b in gb:
                for cf in cfs:
                    if cf in pc:
                        continue
                    for gf in gb[b]:
                        if gf in pg:
                            continue
                        partial.append((cf, gf, cm[cf]["size"], gm[gf]["size"]))
                        pc.add(cf)
                        pg.add(gf)
                        break

        c_only.extend(sorted(set(cm) - pc, key=str.lower))
        g_only.extend(sorted(set(gm) - pg, key=str.lower))

        def add_row(c_cell, g_cell):
            self.mods_lv.controls.append(ft.Row([
                c_cell,
                ft.VerticalDivider(width=20, color=C["bg"]),
                g_cell,
            ]))

        for cf, gf, cs, gs, hash_match in sorted(matched, key=lambda x: x[0].lower()):
            idx = len(self.mods_lv.controls)
            c_cell = self._make_mod_cell(cf, fmt_size(cs), "✔ совпадает" if hash_match else "❌ суммы разные", ft.colors.GREEN_400 if hash_match else ft.colors.RED_400, "client_server", idx)
            g_cell = self._make_mod_cell(gf, fmt_size(gs), "✔ совпадает" if hash_match else "❌ суммы разные", ft.colors.GREEN_400 if hash_match else ft.colors.RED_400, "game_server", idx)
            add_row(c_cell, g_cell)

        for cf, gf, cs, gs in sorted(partial, key=lambda x: x[0].lower()):
            idx = len(self.mods_lv.controls)
            c_cell = self._make_mod_cell(cf, fmt_size(cs), "разные версии", ft.colors.YELLOW_400, "client_server", idx)
            g_cell = self._make_mod_cell(gf, fmt_size(gs), "разные версии", ft.colors.YELLOW_400, "game_server", idx)
            add_row(c_cell, g_cell)

        pad_c = max(0, len(g_only) - len(c_only))
        pad_g = max(0, len(c_only) - len(g_only))
        c_items = [self._make_mod_cell(f, fmt_size(cm[f]["size"]), "только здесь", ft.colors.BLUE_400, "client_server", len(matched) + len(partial) + i) for i, f in enumerate(c_only)] + [self._make_mod_cell(None, "", "", None, "client_server") for _ in range(pad_c)]
        g_items = [self._make_mod_cell(f, fmt_size(gm[f]["size"]), "только здесь", ft.colors.BLUE_400, "game_server", len(matched) + len(partial) + i) for i, f in enumerate(g_only)] + [self._make_mod_cell(None, "", "", None, "game_server") for _ in range(pad_g)]

        for c, g in zip(c_items, g_items):
            add_row(c, g)

    def _dl_all(self, server_key):
        self.ctx.logger.log(f"Скачивание всех модов с {server_key}...")
        def t():
            c = self.ctx.config_manager.get(server_key)
            s = SSHManager(c["host"], c["user"], c["password"])
            ok, msg = s.connect()
            if not ok: self.ctx.logger.log(f"Ошибка: {msg}", True); return
            
            mods_dir = self._remote_mods_dir(server_key)
            ok, out = s.execute_command(f"find {mods_dir} -name '*.jar'")
            if not ok or not out.strip():
                self.ctx.logger.log("Моды не найдены на сервере.")
                s.disconnect()
                return
                
            files = out.strip().split('\n')
            downloaded = 0
            local_dir = self._local_mods_dir()
            os.makedirs(local_dir, exist_ok=True)
            for file_path in files:
                if not file_path:
                    continue
                fname = os.path.basename(file_path)
                ok_dl, msg_dl = s.download_file(file_path, os.path.join(local_dir, fname))
                if not ok_dl:
                    self.ctx.logger.log(f"Ошибка {fname}: {msg_dl}", True)
                    continue
                downloaded += 1
                
            s.disconnect()
            self.ctx.logger.log(f"Успешно скачано {downloaded} модов.")
            if hasattr(self.ctx, "local_mods_tab"): self.ctx.local_mods_tab._refresh_local()
        threading.Thread(target=t, daemon=True).start()

    def _transfer(self, src, dst, fn):
        def _confirmed(e):
            dlg.open = False
            self.ctx.page.update()
            self.ctx.logger.log(f"Переброс {fn} с {src} на {dst}...")
            def t():
                c1, c2 = self.ctx.config_manager.get(src), self.ctx.config_manager.get(dst)
                s1, s2 = SSHManager(c1["host"],c1["user"],c1["password"]), SSHManager(c2["host"],c2["user"],c2["password"])
                ok1, m1 = s1.connect()
                if not ok1: self.ctx.logger.log(f"Сервер {src}:\n{m1}", True); return
                ok2, m2 = s2.connect()
                if not ok2: self.ctx.logger.log(f"Сервер {dst}:\n{m2}", True); return
                _, ld = self.ctx.sync_manager.get_local_mods()
                tmp = os.path.join(ld, os.path.basename(fn))
                try: 
                    s1.sftp.get(f"{self._remote_mods_dir(src)}/{fn}", tmp)
                    s2.upload_file(tmp, f"{self._remote_mods_dir(dst)}/{fn}")
                except Exception as err: self.ctx.logger.log(f"Ошибка переброса: {str(err)}", True)
                finally: 
                    s1.disconnect()
                    s2.disconnect()
                    self.scan_mods()
                    self.ctx.logger.log(f"Успешно переброшен {fn}")
            threading.Thread(target=t, daemon=True).start()

        dlg = ft.AlertDialog(title=ft.Text("Переброс"), content=ft.Text(f"Перебросить {fn}?"),
                             actions=[ft.TextButton("Да", on_click=_confirmed), ft.TextButton("Нет", on_click=lambda e: setattr(dlg, 'open', False) or self.ctx.page.update())])
        self.ctx.page.overlay.append(dlg)
        dlg.open = True
        self.ctx.page.update()

    def _delete(self, srv, fn):
        def _confirmed(e):
            dlg.open = False
            self.ctx.page.update()
            self.ctx.logger.log(f"Удаление {fn} с сервера {srv}...")
            def t():
                c = self.ctx.config_manager.get(srv); ssh = SSHManager(c["host"],c["user"],c["password"])
                ok, msg = ssh.connect()
                if not ok: self.ctx.logger.log(f"Ошибка: {msg}", True); return
                ssh.execute_command(f"rm -f \"{self._remote_mods_dir(srv)}/{fn}\"")
                ssh.disconnect()
                self.ctx.logger.log(f"Удалено {fn}")
                self.scan_mods()
            threading.Thread(target=t, daemon=True).start()

        dlg = ft.AlertDialog(title=ft.Text("Удаление"), content=ft.Text(f"Удалить {fn}?"),
                             actions=[ft.TextButton("Да", on_click=_confirmed), ft.TextButton("Нет", on_click=lambda e: setattr(dlg, 'open', False) or self.ctx.page.update())])
        self.ctx.page.overlay.append(dlg)
        dlg.open = True
        self.ctx.page.update()

    def _dl_local(self, srv, fn):
        self.ctx.logger.log(f"Скачивание {fn} локально...")
        def t():
            c = self.ctx.config_manager.get(srv); ssh = SSHManager(c["host"],c["user"],c["password"])
            ok, msg = ssh.connect()
            if not ok: self.ctx.logger.log(f"Ошибка: {msg}", True); return
            d = self._local_mods_dir()
            os.makedirs(d, exist_ok=True)
            try: ssh.sftp.get(f"{self._remote_mods_dir(srv)}/{fn}", os.path.join(d, os.path.basename(fn)))
            except Exception as err: self.ctx.logger.log(f"Ошибка: {str(err)}", True)
            finally: 
                ssh.disconnect()
                if hasattr(self.ctx, "local_mods_tab"): self.ctx.local_mods_tab._refresh_local()
                self.ctx.logger.log(f"Скачано {fn}")
        threading.Thread(target=t, daemon=True).start()

    def rebuild_index_only(self):
        def _confirmed(e):
            dlg.open = False
            self.ctx.page.update()
            self.ctx.logger.log("Запущена пересборка client/index.json...")

            prog_dlg = ft.AlertDialog(
                title=ft.Text("Сборка Index"),
                content=ft.Row([
                    ft.ProgressRing(),
                    ft.Text(" Сканирование client/mods и вычисление BLAKE3...", expand=True)
                ]),
                modal=True
            )
            self.ctx.page.overlay.append(prog_dlg)
            prog_dlg.open = True
            self.ctx.page.update()

            def t():
                dc = self.ctx.config_manager.get("client_server")
                db = dc["remote_dir"]
                mods_dir = self.ctx.sync_manager.get_remote_mods_dir("client_server")
                index_path = f"{db}/client/index.json"
                ssh = SSHManager(dc["host"], dc["user"], dc["password"])
                ok, msg = ssh.connect()
                if not ok:
                    schedule_ui(self.ctx.page, lambda: setattr(prog_dlg, "open", False) or self.ctx.page.update())
                    self.ctx.logger.log(f"Ошибка SSH: {msg}", True)
                    return
                script = remote_rebuild_script(index_path, mods_dir)
                b = base64.b64encode(script.encode()).decode()
                _, out = ssh.execute_command(
                    f'python3 -c "import base64,sys;exec(base64.b64decode(sys.argv[1]).decode(\'utf-8\'))" {b}',
                    timeout=300,
                )
                ssh.disconnect()
                result = (out or "").strip().splitlines()[-1] if out else ""
                if result.startswith("OK"):
                    self.ctx.logger.log(f"index.json пересобран: {result}")
                else:
                    self.ctx.logger.log(f"Ошибка сборки index: {out or 'пустой ответ'}", True)
                schedule_ui(self.ctx.page, lambda: setattr(prog_dlg, "open", False) or self.ctx.page.update())

            threading.Thread(target=t, daemon=True).start()

        dlg = ft.AlertDialog(
            title=ft.Text("Index"),
            content=ft.Text(
                "Пересобрать client/index.json на сервере скачивания?\n"
                "(manifest.json не трогаем — лаунчер читает моды из index.json)"
            ),
            actions=[
                ft.TextButton("Да", on_click=_confirmed),
                ft.TextButton("Нет", on_click=lambda e: setattr(dlg, "open", False) or self.ctx.page.update()),
            ],
        )
        self.ctx.page.overlay.append(dlg)
        dlg.open = True
        self.ctx.page.update()

class ConsoleTab(ft.Container):
    def __init__(self, ctx):
        super().__init__(expand=True)
        self.ctx = ctx
        self._console_checked = False
        self._live_ssh = None
        self._stream_channel = None
        self._stream_running = False

        self.srv_status = ft.Text("Подключение к серверу...", size=18, color=C["text_dim"])
        self.console_btns = ft.Row([])

        self.term_out = ft.TextField(multiline=True, read_only=True, expand=True, bgcolor=C["section"], border_color=ft.colors.TRANSPARENT, color=C["text"], text_style=ft.TextStyle(font_family="Consolas"))
        self.cmd_entry = ft.TextField(expand=True, bgcolor=C["bg"], border_color=ft.colors.TRANSPARENT, color=C["text"], text_style=ft.TextStyle(font_family="Consolas"), hint_text="Ввод команды для screen...", on_submit=self._run_cmd)

        self.content = ft.Column([
            ft.Row([
                self.srv_status,
                ft.Container(expand=True),
                self.console_btns
            ]),
            ft.Container(
                bgcolor=C["section"], border_radius=12, expand=True, padding=10,
                content=ft.Column([
                    self.term_out,
                    ft.Row([
                        ft.Text(">", font_family="Consolas", color=C["text_dim"]),
                        self.cmd_entry
                    ])
                ])
            )
        ], expand=True)

    def _tlog(self, text):
        if not text:
            return
        def apply():
            self.term_out.value = (self.term_out.value or "") + text
        schedule_ui(self.ctx.page, apply)

    def _ensure_ssh(self):
        if self._live_ssh and self._live_ssh.ssh and self._live_ssh.ssh.get_transport() and self._live_ssh.ssh.get_transport().is_active():
            return True, ""
        gc = self.ctx.config_manager.get("game_server")
        if not gc.get("host"): return False, "Хост не указан в настройках"
        self._live_ssh = SSHManager(gc["host"], gc["user"], gc["password"])
        ok, msg = self._live_ssh.connect()
        return ok, msg

    def _start_live_stream(self):
        if self._stream_running: return
        self._stream_running = True
        self._tlog("[Система] Подключение к консоли (ssh)...")
        def t():
            ok, msg = self._ensure_ssh()
            if not ok:
                self._tlog(f"[Ошибка] SSH сбой: {msg}")
                self._stream_running = False
                schedule_ui(self.ctx.page, lambda: (
                    setattr(self.srv_status, "value", "Сервер недоступен"),
                    setattr(self.srv_status, "color", C["red"]),
                ))
                return
                
            gc = self.ctx.config_manager.get("game_server")
            try:
                transport = self._live_ssh.ssh.get_transport()
                self._stream_channel = transport.open_session()
                self._tlog("[Система] Подключение к сессии screen установлено...\n")
                
                s_name = gc.get("screen_name", "NoteBuns")
                self._stream_channel.settimeout(1.0)
                self._stream_channel.get_pty()
                self._stream_channel.invoke_shell()
                self._stream_channel.send(f"screen -x {s_name}\n")
                
                while self._stream_running:
                    try:
                        if self._stream_channel.recv_ready():
                            data = self._stream_channel.recv(4096).decode("utf-8", errors="ignore")
                            if data:
                                data = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', data)
                                chunk = data
                                schedule_ui(self.ctx.page, lambda: setattr(
                                    self.term_out, "value", (self.term_out.value or "") + chunk
                                ))
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

    def _run_cmd(self, e):
        cmd = self.cmd_entry.value.strip()
        if not cmd: return
        self.cmd_entry.value = ""
        self.cmd_entry.update()
        def t():
            ok, _ = self._ensure_ssh()
            if not ok: return
            safe_cmd = cmd.replace('"', '\\"')
            s_name = self.ctx.config_manager.get("game_server", "screen_name")
            self._live_ssh.execute_command(f'screen -S {s_name} -X stuff "{safe_cmd}\\n"')
        threading.Thread(target=t, daemon=True).start()

    def _check_server_status(self):
        def t():
            ok, msg = self._ensure_ssh()
            if not ok: self._set_srv("error", msg); return
            s_name = self.ctx.config_manager.get("game_server", "screen_name")
            ok_cmd, out = self._live_ssh.execute_command(f"screen -ls | grep {s_name}")
            if out and s_name in out: self._set_srv("running")
            else: self._set_srv("stopped")
        threading.Thread(target=t, daemon=True).start()

    def _set_srv(self, state, msg=""):
        def apply():
            self.console_btns.controls.clear()
            self.console_btns.controls.append(
                ft.IconButton(ft.icons.REFRESH, tooltip="Обновить состояние", on_click=lambda e: self._check_server_status())
            )
            if state == "running":
                self.srv_status.value = "Игровой сервер РАБОТАЕТ"
                self.srv_status.color = C["green"]
                self.console_btns.controls.extend([
                    ft.ElevatedButton("Перезапустить сервер", bgcolor=C["section"], color=C["text"], on_click=self._restart),
                    ft.ElevatedButton("Остановить сервер", bgcolor=C["red"], color=ft.colors.WHITE, on_click=self._stop),
                ])
            elif state == "stopped":
                self.srv_status.value = "Игровой сервер ОСТАНОВЛЕН"
                self.srv_status.color = C["text_dim"]
                self.console_btns.controls.extend([
                    ft.ElevatedButton("Запустить сервер", bgcolor=C["accent"], color=ft.colors.WHITE, on_click=self._start),
                ])
            else:
                self.srv_status.value = f"Ошибка: {msg}"
                self.srv_status.color = C["red"]
        schedule_ui(self.ctx.page, apply)

    def _start(self, e):
        self._tlog("[Система] Отправка команды запуска сервера...")
        def t():
            if not self._ensure_ssh()[0]: return
            gc = self.ctx.config_manager.get("game_server")
            self._live_ssh.execute_command(f"cd {gc['remote_dir']} && ./start.sh &")
            time.sleep(3); self._check_server_status()
        threading.Thread(target=t, daemon=True).start()

    def _stop(self, e):
        def _confirmed(e):
            dlg.open = False
            self.ctx.page.update()
            self._tlog("[Система] Отправка команды остановки сервера...")
            def t():
                if not self._ensure_ssh()[0]: return
                s_name = self.ctx.config_manager.get("game_server", "screen_name")
                self._live_ssh.execute_command(f'screen -S {s_name} -X stuff "stop\\n"')
                time.sleep(5); self._check_server_status()
            threading.Thread(target=t, daemon=True).start()

        dlg = ft.AlertDialog(title=ft.Text("Остановка"), content=ft.Text("Вы уверены, что хотите остановить игровой сервер?"),
                             actions=[ft.TextButton("Да", on_click=_confirmed), ft.TextButton("Нет", on_click=lambda e: setattr(dlg, 'open', False) or self.ctx.page.update())])
        self.ctx.page.overlay.append(dlg)
        dlg.open = True
        self.ctx.page.update()

    def _restart(self, e):
        def _confirmed(e):
            dlg.open = False
            self.ctx.page.update()
            self._tlog("[Система] Рестарт сервера...")
            def t():
                if not self._ensure_ssh()[0]: return
                s_name = self.ctx.config_manager.get("game_server", "screen_name")
                self._live_ssh.execute_command(f'screen -S {s_name} -X stuff "stop\\n"')
                time.sleep(10)
                gc = self.ctx.config_manager.get("game_server")
                self._live_ssh.execute_command(f"cd {gc['remote_dir']} && ./start.sh &")
                time.sleep(3); self._check_server_status()
            threading.Thread(target=t, daemon=True).start()

        dlg = ft.AlertDialog(title=ft.Text("Перезапуск"), content=ft.Text("Отправить сервер в перезагрузку?"),
                             actions=[ft.TextButton("Да", on_click=_confirmed), ft.TextButton("Нет", on_click=lambda e: setattr(dlg, 'open', False) or self.ctx.page.update())])
        self.ctx.page.overlay.append(dlg)
        dlg.open = True
        self.ctx.page.update()

class BackupsTab(ft.Container):
    def __init__(self, ctx):
        super().__init__(expand=True)
        self.ctx = ctx
        self._backup_monitoring = False
        
        self.tree_backups = ft.ListView(expand=True, spacing=2)
        
        self.backup_lbl = ft.Text("Прогресс: 0% | Оценка времени: --:--", weight="bold")
        self.backup_pb = ft.ProgressBar(value=0, color=C["accent"], bgcolor=C["section"])
        self.backup_log = ft.TextField(multiline=True, read_only=True, height=80, text_style=ft.TextStyle(font_family="Consolas"), bgcolor=C["section"], border_color=ft.colors.TRANSPARENT, color=C["text_dim"])
        
        self.backup_prog_frame = ft.Column([
            ft.Row([self.backup_lbl, ft.Container(expand=True), ft.ElevatedButton("Отменить", bgcolor=C["row_red"], color=ft.colors.WHITE, on_click=self._cancel_backup)]),
            self.backup_pb,
            self.backup_log
        ], visible=False)

        self.content = ft.Column([
            ft.Row([
                ft.Text("Резервные Копии", size=24, color=C["text"], weight="bold"),
                ft.Container(expand=True),
                ft.ElevatedButton("Обновить список", on_click=lambda e: self.refresh_backups()),
                ft.ElevatedButton("Создать бекап сервера", bgcolor=C["accent"], color=ft.colors.WHITE, on_click=self._create_backup)
            ]),
            self.backup_prog_frame,
            ft.Container(
                bgcolor=C["section"], border_radius=12, padding=15, expand=True,
                content=ft.Column([
                    ft.Row([
                        ft.Text("Имя архива", expand=4, weight="bold"),
                        ft.Text("Размер", expand=1, weight="bold", text_align="right"),
                        ft.Text("Дата", expand=2, weight="bold", text_align="center")
                    ]),
                    self.tree_backups
                ])
            )
        ], expand=True)

    def refresh_backups(self):
        page = self.ctx.page
        schedule_ui(page, lambda: self.tree_backups.controls.clear())
        self.ctx.logger.log("[Система] Обновление списка бекапов...")

        def worker():
            gc = self.ctx.config_manager.get("game_server")
            ssh = SSHManager(gc["host"], gc["user"], gc["password"])
            ok, msg = ssh.connect()
            if not ok:
                self.ctx.logger.log(f"Бекапы недоступны:\n{msg}", True)
                return

            ok, out = ssh.execute_command("screen -ls | grep admin_backup")
            if out and "admin_backup" in out:
                threading.Thread(target=self._start_monitor_backup, daemon=True).start()

            b_dir = f"{gc['remote_dir']}/backups"
            ssh.execute_command(f"mkdir -p {b_dir}")
            ok, out = ssh.execute_command(f"ls -lh --time-style=long-iso {b_dir}")
            rows = []
            if ok and out:
                for line in out.strip().split('\n'):
                    if line.startswith('total'):
                        continue
                    parts = line.split()
                    if len(parts) >= 8:
                        size = parts[4]
                        date = f"{parts[5]} {parts[6]}"
                        name = " ".join(parts[7:])
                        if name.endswith('.7z') or name.endswith('.zip') or name.endswith('.tar.gz'):
                            rows.append((name, size, date, b_dir))
            ssh.disconnect()

            def apply_rows():
                for index, (name, size, date, b_dir) in enumerate(rows):
                    items = [
                        ft.PopupMenuItem(content="Удалить бекап", on_click=lambda e, _name=name, _dir=b_dir: self._delete_backup(_dir, _name))
                    ]
                    self.tree_backups.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(name, expand=4),
                                ft.Text(size, expand=1, text_align="right"),
                                ft.Text(date, expand=2, text_align="center"),
                                ft.PopupMenuButton(items=items, icon=ft.icons.MORE_VERT, tooltip="Действия")
                            ]),
                            bgcolor=ft.colors.WHITE10 if index % 2 == 0 else ft.colors.TRANSPARENT,
                            padding=ft.padding.only(left=5, right=5),
                            border_radius=4
                        )
                    )

            schedule_ui(page, apply_rows)
            self.ctx.logger.log("[Система] Список бекапов успешно получен.")

        page.run_thread(worker)

    def _delete_backup(self, b_dir, name):
        def _confirmed(e):
            dlg.open = False
            self.ctx.page.update()
            self.ctx.logger.log(f"Удаление бекапа {name}...")
            def t():
                gc = self.ctx.config_manager.get("game_server")
                ssh = SSHManager(gc["host"], gc["user"], gc["password"])
                ok, msg = ssh.connect()
                if ok:
                    ssh.execute_command(f"rm -f \"{b_dir}/{name}\"")
                    ssh.disconnect()
                    self.ctx.logger.log(f"Бекап {name} удален.")
                    self.refresh_backups()
                else:
                    self.ctx.logger.log(f"Ошибка удаления: {msg}", True)
            threading.Thread(target=t, daemon=True).start()

        dlg = ft.AlertDialog(title=ft.Text("Удаление"), content=ft.Text(f"Вы уверены, что хотите безвозвратно удалить {name}?"),
                             actions=[ft.TextButton("Да", on_click=_confirmed), ft.TextButton("Нет", on_click=lambda e: setattr(dlg, 'open', False) or self.ctx.page.update())])
        self.ctx.page.overlay.append(dlg)
        dlg.open = True
        self.ctx.page.update()

    def _cancel_backup(self, e):
        def _confirmed(e):
            dlg.open = False
            self.ctx.page.update()
            def t():
                self.ctx.logger.log("[Система] Отмена бекапа на сервере...")
                gc = self.ctx.config_manager.get("game_server")
                ssh = SSHManager(gc["host"], gc["user"], gc["password"], timeout=30)
                ok, msg = ssh.connect()
                if ok:
                    ssh.execute_command("screen -X -S admin_backup quit")
                    ssh.execute_command("killall 7z")
                    ssh.disconnect()
                self._backup_monitoring = False
                self.backup_prog_frame.visible = False
                try: self.ctx.page.update()
                except: pass
                self.ctx.logger.log("[Система] Бекап успешно отменен.", True)
            threading.Thread(target=t, daemon=True).start()

        dlg = ft.AlertDialog(title=ft.Text("Отмена"), content=ft.Text("Вы уверены, что хотите отменить текущий бекап?"),
                             actions=[ft.TextButton("Да", on_click=_confirmed), ft.TextButton("Нет", on_click=lambda e: setattr(dlg, 'open', False) or self.ctx.page.update())])
        self.ctx.page.overlay.append(dlg)
        dlg.open = True
        self.ctx.page.update()

    def _create_backup(self, e):
        def _confirmed(e):
            dlg.open = False
            self.ctx.page.update()
            self.ctx.logger.log("Запущено создание резервной копии сервера. Ждем завершения...")
            def t():
                gc = self.ctx.config_manager.get("game_server")
                ssh = SSHManager(gc["host"], gc["user"], gc["password"], timeout=300)
                ok, msg = ssh.connect()
                if not ok:
                    self.ctx.logger.log(f"Ошибка бекапа: {msg}", True)
                    return
                    
                ok_7z, out_7z = ssh.execute_command("which 7z")
                if not ok_7z or not out_7z.strip():
                    self.ctx.logger.log("Ошибка: 7z не установлен на сервере. Установите: apt install p7zip-full", True)
                    ssh.disconnect()
                    return
                    
                ok_scr, out_scr = ssh.execute_command("which screen")
                if not ok_scr or not out_scr.strip():
                    self.ctx.logger.log("Ошибка: screen не установлен на сервере. Установите: apt install screen", True)
                    ssh.disconnect()
                    return
                    
                date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
                b_dir = f"{gc['remote_dir']}/backups"
                b_name = f"backup_{date_str}.7z"
                
                excl = self.ctx.config_manager.get("backups", "excluded_folders")
                args = self.ctx.config_manager.get("backups", "7z_args")
                
                excl_cmd = " ".join([f"-x!{f.strip()}" for f in excl.split(",") if f.strip()])
                
                log_file = f"{gc['remote_dir']}/backups/backup_progress.log"
                ssh.execute_command(f"rm -f {log_file}")
                
                cmd = f"cd {gc['remote_dir']} && env LC_ALL=C.UTF-8 7z a -bsp1 {args} {b_dir}/{b_name} ./* {excl_cmd} >> {log_file} 2>&1"
                screen_cmd = f"screen -dmS admin_backup bash -c '{cmd}'"
                
                self.ctx.logger.log(f"Сжатие файлов в {b_name} (Фоновый процесс)...")
                ssh.execute_command(screen_cmd)
                ssh.disconnect()
                
                threading.Thread(target=self._start_monitor_backup, daemon=True).start()
                
            threading.Thread(target=t, daemon=True).start()

        dlg = ft.AlertDialog(title=ft.Text("Бекап"), content=ft.Text("Запустить создание резервной копии сервера? Это может занять время и снизить производительность (TPS)."),
                             actions=[ft.TextButton("Да", on_click=_confirmed), ft.TextButton("Нет", on_click=lambda e: setattr(dlg, 'open', False) or self.ctx.page.update())])
        self.ctx.page.overlay.append(dlg)
        dlg.open = True
        self.ctx.page.update()

    def _start_monitor_backup(self):
        if self._backup_monitoring: return
        self._backup_monitoring = True
        schedule_ui(self.ctx.page, lambda: setattr(self.backup_prog_frame, "visible", True))
        
        def t():
            gc = self.ctx.config_manager.get("game_server")
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
                    lines = log_out.replace('\r', '\n').split('\n')
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
                            fname = re.sub(r'^\d+\s*\+\s*', '', fname)
                            if fname and fname != "U" and not fname.startswith("U "):
                                files_added.append(fname)
                    
                    if last_pct > 0:
                        last_pct_recorded = last_pct
                        elapsed = time.time() - start_time
                        eta_sec = (elapsed / last_pct) * (100 - last_pct) if last_pct > 0 else 0
                        mins, secs = divmod(int(eta_sec), 60)
                        pb_val = last_pct / 100.0
                        lbl_val = f"Прогресс: {last_pct}% | Оценка времени: {mins:02d}:{secs:02d}"
                        log_append = ""
                        if files_added:
                            new_line = files_added[-1]
                            if new_line != last_logged_line:
                                cleaned_line = ''.join(c for c in new_line if c.isprintable())
                                if cleaned_line:
                                    log_append = cleaned_line + "\n"
                                    last_logged_line = new_line

                        def apply_progress(_pb=pb_val, _lbl=lbl_val, _log=log_append):
                            self.backup_pb.value = _pb
                            self.backup_lbl.value = _lbl
                            if _log:
                                self.backup_log.value = (self.backup_log.value or "") + _log

                        schedule_ui(self.ctx.page, apply_progress)
                
                if not is_running:
                    break
                time.sleep(2)
                
            ssh.disconnect()
            self._backup_monitoring = False

            def finish():
                self.backup_prog_frame.visible = False
                self.backup_pb.value = 0
                self.backup_log.value = ""

            schedule_ui(self.ctx.page, finish)
            self.ctx.logger.log("Бекап завершен.")
            self.refresh_backups()
            
        threading.Thread(target=t, daemon=True).start()

class SettingsTab(ft.Container):
    def __init__(self, ctx):
        super().__init__(expand=True)
        self.ctx = ctx
        self._sv = {}
        
        self.content = ft.ListView(expand=True, spacing=10)
        self.content.controls.append(ft.Text("Настройки", size=24, color=C["text"], weight="bold"))
        
        self._scard("Клиент-сервер", "client_server", [("name","Название",False),("host","Хост",False),("user","Логин",False),("password","Пароль",True),("remote_dir","Путь к сайту",False)])
        self._scard("Игровой сервер", "game_server", [("name","Название",False),("host","Хост",False),("user","Логин",False),("password","Пароль",True),("remote_dir","Путь к серверу",False), ("screen_name", "Имя Screen", False)])
        self._scard("Настройки бекапа", "backups", [("excluded_folders", "Исключения (через запятую)", False), ("7z_args", "Аргументы 7z", False)])
        
        self.dir_picker = ft.FilePicker()
        self.config_picker = ft.FilePicker()
        var = ft.TextField(value=self.ctx.config_manager.get("paths", "local_mods_dir") or "mods", expand=True, bgcolor=C["bg"], border_color=ft.colors.TRANSPARENT, color=C["text"])
        self._sv[("paths", "local_mods_dir")] = var
        self.content.controls.append(
            ft.Container(
                bgcolor=C["section"], border_radius=12, padding=15,
                content=ft.Column([
                    ft.Text("Локальные файлы", size=18, color=C["text"], weight="bold"),
                    ft.Row([
                        ft.Text("Папка модов:", width=180, color=C["text_dim"]),
                        var,
                        ft.ElevatedButton("Обзор", icon=ft.icons.FOLDER, on_click=lambda e: pick_directory(self.ctx.page, self.dir_picker, "Выберите папку", self._on_local_dir_picked))
                    ])
                ])
            )
        )
        
        self.content.controls.append(
            ft.Container(
                bgcolor=C["section"], border_radius=12, padding=15,
                content=ft.Column([
                    ft.Text("Файл настроек", size=18, color=C["text"], weight="bold"),
                    ft.Text(
                        self.ctx.config_manager.config_path,
                        size=12,
                        color=C["text_dim"],
                        selectable=True,
                    ),
                    ft.Row([
                        ft.ElevatedButton(
                            "Импорт",
                            icon=ft.icons.UPLOAD_FILE,
                            on_click=self._import_settings,
                        ),
                        ft.ElevatedButton(
                            "Экспорт",
                            icon=ft.icons.DOWNLOAD,
                            on_click=self._export_settings,
                        ),
                    ], spacing=10),
                ]),
            )
        )

        self.btn_reset = ft.ElevatedButton("Сбросить настройки", bgcolor=C["red"], color=ft.colors.WHITE, on_click=self._start_reset_timer)
        self.content.controls.append(ft.Row([
            ft.ElevatedButton("Сохранить", bgcolor=C["accent"], color=ft.colors.WHITE, on_click=self._save_settings),
            self.btn_reset
        ], spacing=10))

        self._reset_timer = False
        self._reset_count = 0

    def _on_local_dir_picked(self, path):
        if path:
            self._sv[("paths", "local_mods_dir")].value = path
            self._sv[("paths", "local_mods_dir")].update()

    def _reload_fields_from_config(self):
        for (section, key), field in self._sv.items():
            field.value = self.ctx.config_manager.get(section, key) or ""
        try:
            self.ctx.page.update()
        except Exception:
            pass

    def _import_settings(self, e):
        pick_json_file(
            self.ctx.page,
            self.config_picker,
            "Выберите файл настроек (json)",
            self._on_config_imported,
        )

    def _on_config_imported(self, path):
        if not path:
            return
        try:
            self.ctx.config_manager.import_from(path)
            self._reload_fields_from_config()
            self.ctx.logger.log(f"Настройки импортированы из {path}")
        except Exception as err:
            self.ctx.logger.log(f"Ошибка импорта: {err}", True)

    def _export_settings(self, e):
        save_json_file(
            self.ctx.page,
            self.config_picker,
            "Сохранить настройки как",
            "admin_settings.json",
            self._on_config_exported,
        )

    def _on_config_exported(self, path):
        if not path:
            return
        try:
            for (section, key), field in self._sv.items():
                self.ctx.config_manager.set(section, key, field.value)
            self.ctx.config_manager.export_to(path)
            self.ctx.logger.log(f"Настройки экспортированы в {path}")
        except Exception as err:
            self.ctx.logger.log(f"Ошибка экспорта: {err}", True)

    def _scard(self, title, section, fields):
        rows = [ft.Text(title, size=18, color=C["text"], weight="bold")]
        for key, label, pw in fields:
            var = ft.TextField(value=self.ctx.config_manager.get(section, key) or "", password=pw, can_reveal_password=pw, expand=True, bgcolor=C["bg"], border_color=ft.colors.TRANSPARENT, color=C["text"])
            self._sv[(section, key)] = var
            rows.append(ft.Row([ft.Text(label, width=180, color=C["text_dim"]), var]))
            
        self.content.controls.append(ft.Container(bgcolor=C["section"], border_radius=12, padding=15, content=ft.Column(rows)))

    def _save_settings(self, e):
        for (s, k), v in self._sv.items(): 
            self.ctx.config_manager.set(s, k, v.value)
        self.ctx.logger.log("Настройки успешно сохранены и применены.")
        if self.ctx.app:
            if hasattr(self.ctx.app.console_tab, '_stream_running') and self.ctx.app.console_tab._stream_running:
                self.ctx.app.console_tab._stream_running = False
                threading.Thread(target=lambda: (time.sleep(0.5), self.ctx.app.console_tab._start_live_stream()), daemon=True).start()
            if self.ctx.app.sync_tab:
                self.ctx.app.sync_tab.scan_mods()

    def _start_reset_timer(self, e):
        if self._reset_timer:
            self._reset_timer = False
            self.btn_reset.text = "Сбросить настройки"
            self.btn_reset.bgcolor = C["red"]
            self.ctx.page.update()
            return
            
        self._reset_count = 10
        self.btn_reset.bgcolor = C["orange"]
        self._reset_timer = True
        threading.Thread(target=self._tick_reset, daemon=True).start()
        
    def _tick_reset(self):
        while self._reset_timer and self._reset_count > 0:
            self.btn_reset.text = f"Отменить сброс ({self._reset_count})"
            try: self.ctx.page.update()
            except: pass
            time.sleep(1)
            self._reset_count -= 1
            
        if self._reset_timer and self._reset_count <= 0:
            self._do_reset()

    def _do_reset(self):
        self._reset_timer = False
        self.btn_reset.text = "Сбросить настройки"
        self.btn_reset.bgcolor = C["red"]
        cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin_settings.json")
        if os.path.exists(cfg): os.remove(cfg)
        self.ctx.config_manager = ConfigManager()
        self.ctx.logger.log("Настройки полностью сброшены!")
        
        dlg = ft.AlertDialog(title=ft.Text("Сброс"), content=ft.Text("Настройки сброшены! Программа закроется."),
                             actions=[ft.TextButton("ОК", on_click=lambda e: close_application(self.ctx.page))])
        self.ctx.page.overlay.append(dlg)
        dlg.open = True
        try: self.ctx.page.update()
        except: pass

class AppContext:
    def __init__(self, page: ft.Page):
        self.page = page
        self.config_manager = ConfigManager()
        self.sync_manager = SyncManager(self.config_manager)
        self.logger = Logger(page)
        self.app = None

class AdminPanelFlet:
    def __init__(self, page: ft.Page):
        self.page = page
        self.ctx = AppContext(page)
        self.ctx.app = self

        self.sync_tab = SyncTab(self.ctx)
        self.console_tab = ConsoleTab(self.ctx)
        self.backups_tab = BackupsTab(self.ctx)
        self.settings_tab = SettingsTab(self.ctx)
        
        self.sync_tab.visible = True
        self.console_tab.visible = False
        self.backups_tab.visible = False
        self.settings_tab.visible = False

        self.main_content = ft.Column([
            self.sync_tab,
            self.console_tab,
            self.backups_tab,
            self.settings_tab
        ], expand=True)

        rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.SELECTED,
            bgcolor=C["bg2"],
            destinations=[
                ft.NavigationRailDestination(icon=ft.icons.SYNC, selected_icon=ft.icons.SYNC_OUTLINED, label="Моды"),
                ft.NavigationRailDestination(icon=ft.icons.TERMINAL, selected_icon=ft.icons.TERMINAL_OUTLINED, label="Консоль"),
                ft.NavigationRailDestination(icon=ft.icons.SAVE, selected_icon=ft.icons.SAVE_OUTLINED, label="Бекапы"),
                ft.NavigationRailDestination(icon=ft.icons.SETTINGS, selected_icon=ft.icons.SETTINGS_OUTLINED, label="Настройки"),
            ],
            on_change=self.rail_change,
        )

        page.add(
            ft.Row([
                rail,
                ft.VerticalDivider(width=1),
                ft.Column([
                    self.main_content,
                    self.ctx.logger.widget
                ], expand=True)
            ], expand=True)
        )
        page.update()
        self.ctx.logger.mark_mounted()
        register_file_picker(page, self.sync_tab.file_picker, mounted=True)
        register_file_picker(page, self.settings_tab.dir_picker, mounted=True)
        register_file_picker(page, self.settings_tab.config_picker, mounted=True)
        page.update()
        cm = self.ctx.config_manager
        if cm.discovered_from:
            self.ctx.logger.log(f"Настройки найдены: {cm.discovered_from}")
        if cm.import_required:
            self._show_config_import_dialog()
        self.sync_tab.scan_mods()
        threading.Thread(target=self.backups_tab.refresh_backups, daemon=True).start()
        threading.Thread(target=self.console_tab._check_server_status, daemon=True).start()
        threading.Thread(target=self.console_tab._start_live_stream, daemon=True).start()
        check_for_updates(page)

    def _show_config_import_dialog(self):
        page = self.page

        def on_import(e):
            dlg.open = False
            page.update()
            pick_json_file(
                page,
                self.settings_tab.config_picker,
                "Выберите файл настроек (json)",
                self._on_startup_config_imported,
            )

        def on_empty(e):
            dlg.open = False
            page.update()
            self.ctx.config_manager.import_required = False
            self.ctx.logger.log("Создан шаблон настроек. Заполните их во вкладке «Настройки».")

        def on_close(e):
            dlg.open = False
            page.update()
            close_application(page)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Настройки не найдены"),
            content=ft.Text(
                "Файл admin_settings.json не найден в папке программы, Desktop или Downloads.\n\n"
                "Импортируйте существующий файл или создайте пустой шаблон."
            ),
            actions=[
                ft.TextButton("Импорт", on_click=on_import),
                ft.TextButton("Пустой шаблон", on_click=on_empty),
                ft.TextButton("Выход", on_click=on_close),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def _on_startup_config_imported(self, path):
        if not path:
            self._show_config_import_dialog()
            return
        try:
            self.ctx.config_manager.import_from(path)
            self.settings_tab._reload_fields_from_config()
            self.ctx.logger.log(f"Настройки импортированы из {path}")
        except Exception as err:
            self.ctx.logger.log(f"Ошибка импорта: {err}", True)
            self._show_config_import_dialog()

    def rail_change(self, e):
        idx = e.control.selected_index
        tabs = [self.sync_tab, self.console_tab, self.backups_tab, self.settings_tab]
        for i, tab in enumerate(tabs):
            tab.visible = (i == idx)
        self.main_content.update()

def main(page: ft.Page):
    page.title = "Minecraft Admin Panel"
    configure_page_window(page, icon="icon.png", width=1300, height=800, min_width=1000, min_height=650)
    page.bgcolor = C["bg"]
    page.theme_mode = ft.ThemeMode.DARK
    
    app = AdminPanelFlet(page)

import sys
import os

if __name__ == "__main__":
    assets_dir = sys._MEIPASS if getattr(sys, 'frozen', False) else "."
    launch_flet_app(main, assets_dir=assets_dir)
