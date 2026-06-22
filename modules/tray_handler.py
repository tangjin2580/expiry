# -*- coding: utf-8 -*-
"""
到期提醒工具 — 系统托盘管理
支持后台运行模式：最小化到托盘、从托盘恢复窗口。
依赖：pystray, Pillow（可选，导入失败时静默降级为无托盘模式）
"""

import threading
import sys
import os


class TrayHandler:
    """系统托盘图标管理器。"""

    def __init__(self, app):
        """
        Parameters
        ----------
        app : ExpiryApp
            主窗口实例（tk.Tk 子类）。
        """
        self._app = app
        self._icon = None
        self._thread = None
        self._force_close = False  # 标记：真正退出而非最小化到托盘

    @property
    def force_close(self):
        return self._force_close

    # ------------------------------------------------------------------
    # 图标加载
    # ------------------------------------------------------------------

    @staticmethod
    def _load_icon_image():
        """加载应用图标为 PIL.Image 对象。Pillow 未安装时返回 None。"""
        try:
            from PIL import Image
        except ImportError:
            return None
        if getattr(sys, "frozen", False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ico_path = os.path.join(base, "assets", "icon.ico")
        if os.path.exists(ico_path):
            try:
                return Image.open(ico_path)
            except Exception:
                pass
        # 生成一个简易蓝色图标作为 fallback
        img = Image.new("RGBA", (64, 64), (37, 99, 235, 255))
        return img

    # ------------------------------------------------------------------
    # 启动 / 停止
    # ------------------------------------------------------------------

    def start(self):
        """在后台线程启动系统托盘图标。"""
        try:
            import pystray
        except ImportError:
            return False

        icon_image = self._load_icon_image()
        if icon_image is None:
            # Pillow 未安装，无法创建托盘图标
            return False

        menu = pystray.Menu(
            pystray.MenuItem("打开主窗口", self._toggle_window, default=True),
            pystray.MenuItem("检查更新", self._check_update),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._quit_app),
        )

        self._icon = pystray.Icon(
            "expiry_reminder",
            icon_image,
            "到期提醒工具",
            menu,
        )

        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """停止托盘图标。"""
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None

    # ------------------------------------------------------------------
    # 窗口操作
    # ------------------------------------------------------------------

    def show_window(self):
        """从托盘恢复主窗口（线程安全）。"""
        self._app.after(0, self._do_show_window)

    def _do_show_window(self):
        """在主线程中恢复窗口。"""
        app = self._app
        app.deiconify()
        app.lift()
        app.focus_force()
        # Windows 下需要额外确保窗口前置
        try:
            app.attributes("-topmost", True)
            app.after(200, lambda: app.attributes("-topmost", False))
        except Exception:
            pass

    def _toggle_window(self, icon=None, item=None):
        """托盘左键/默认动作：切换窗口显示/隐藏。"""
        app = self._app
        try:
            if app.winfo_viewable():
                self.hide_window()
            else:
                self.show_window()
        except Exception:
            self.show_window()

    def hide_window(self):
        """隐藏主窗口到托盘。"""
        self._app.withdraw()

    def _quit_app(self, icon=None, item=None):
        """托盘菜单回调：真正退出程序。"""
        self._force_close = True
        self.stop()
        # 在主线程中执行 destroy，避免跨线程问题
        self._app.after(0, self._app.destroy)

    # ------------------------------------------------------------------
    # 窗口关闭处理
    # ------------------------------------------------------------------

    def on_close(self):
        """
        拦截 WM_DELETE_WINDOW。
        如果托盘在运行，则隐藏窗口（最小化到托盘）；
        否则正常关闭。
        """
        if self._force_close:
            self.stop()
            self._app.destroy()
            return

        if self._icon is not None:
            # 最小化到托盘
            self.hide_window()
        else:
            # 无托盘，正常关闭
            self.stop()
            self._app.destroy()

    # ------------------------------------------------------------------
    # 检查更新
    # ------------------------------------------------------------------

    def _check_update(self, icon=None, item=None):
        """托盘菜单回调：切换到检查更新标签页。"""
        app = self._app
        # 如果窗口隐藏，先显示
        try:
            if not app.winfo_viewable():
                self.show_window()
        except Exception:
            self.show_window()
        # 在主线程切换到检查更新标签页
        app.after(100, lambda: app.notebook.select(app.update_tab))
