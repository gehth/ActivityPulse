"""全局快捷键工具 - 使用pynput监听全局热键（支持多组快捷键）"""

from pynput import keyboard


# 默认快捷键配置
DEFAULT_HOTKEYS = {
    "toggle_window": {
        "hotkey": '<ctrl>+<shift>+h',
        "display": 'Ctrl+Shift+H',
        "label": "显示/隐藏主窗口"
    },
    "toggle_pause": {
        "hotkey": '<ctrl>+<shift>+p',
        "display": 'Ctrl+Shift+P',
        "label": "暂停/恢复记录"
    },
    "toggle_privacy": {
        "hotkey": '<ctrl>+<shift>+v',
        "display": 'Ctrl+Shift+V',
        "label": "隐私模式切换"
    },
    "toggle_pomodoro": {
        "hotkey": '<ctrl>+<shift>+t',
        "display": 'Ctrl+Shift+T',
        "label": "番茄钟开关"
    },
}

# 兼容旧版常量
DEFAULT_HOTKEY = '<ctrl>+<shift>+h'
DEFAULT_HOTKEY_DISPLAY = 'Ctrl+Shift+H'


class GlobalHotkeyManager:
    """全局热键管理器 - 支持多组快捷键注册和管理"""

    def __init__(self, callback=None, hotkey_str: str = None):
        """
        Args:
            callback: 默认热键（toggle_window）触发时的回调函数
            hotkey_str: 默认快捷键字符串（pynput格式），如 '<ctrl>+<shift>+h'
        """
        self._listener = None
        self._running = False
        self._hotkeys = {}  # {action_name: {hotkey_str, callback, hotkey_obj}}
        
        # 注册默认的显示/隐藏窗口快捷键（兼容旧版接口）
        initial_hotkey = hotkey_str or DEFAULT_HOTKEY
        self.register_hotkey("toggle_window", initial_hotkey, callback)

    def register_hotkey(self, action: str, hotkey_str: str, callback=None):
        """注册一组快捷键
        
        Args:
            action: 动作名称，如 'toggle_window', 'toggle_pause'
            hotkey_str: 快捷键字符串（pynput格式）
            callback: 触发时的回调函数
        """
        hotkey_obj = keyboard.HotKey(
            keyboard.HotKey.parse(hotkey_str),
            lambda cb=callback: self._invoke_callback(cb)
        )
        self._hotkeys[action] = {
            "hotkey_str": hotkey_str,
            "callback": callback,
            "hotkey_obj": hotkey_obj
        }
        # 如果正在运行，需要重启以应用新的快捷键
        if self._running:
            self.stop()
            self.start()

    def unregister_hotkey(self, action: str):
        """取消注册一组快捷键"""
        if action in self._hotkeys:
            del self._hotkeys[action]
            if self._running:
                self.stop()
                self.start()

    def _invoke_callback(self, callback):
        """安全调用回调函数"""
        if callback:
            try:
                callback()
            except Exception:
                pass

    def _on_press(self, key):
        """按键事件 - 传递给所有HotKey处理"""
        for entry in self._hotkeys.values():
            try:
                entry["hotkey_obj"].press(key)
            except (AttributeError, TypeError):
                pass

    def _on_release(self, key):
        """释放事件 - 传递给所有HotKey处理"""
        for entry in self._hotkeys.values():
            try:
                entry["hotkey_obj"].release(key)
            except (AttributeError, TypeError):
                pass

    def start(self):
        """启动全局热键监听"""
        if self._running:
            return
        self._running = True
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        """停止全局热键监听"""
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._running = False

    def set_callback(self, callback):
        """设置默认（toggle_window）回调函数"""
        if "toggle_window" in self._hotkeys:
            self._hotkeys["toggle_window"]["callback"] = callback

    def update_hotkey(self, hotkey_str: str, action: str = "toggle_window"):
        """更新指定动作的快捷键（运行时切换）
        
        Args:
            hotkey_str: 新的快捷键字符串（pynput格式）
            action: 动作名称，默认为 toggle_window
        """
        if action not in self._hotkeys:
            return
        callback = self._hotkeys[action]["callback"]
        self.register_hotkey(action, hotkey_str, callback)

    def get_hotkey_str(self, action: str = "toggle_window") -> str:
        """获取指定动作的快捷键字符串"""
        if action in self._hotkeys:
            return self._hotkeys[action]["hotkey_str"]
        return ""

    def get_all_hotkeys(self) -> dict:
        """获取所有已注册的快捷键信息"""
        return {action: entry["hotkey_str"] for action, entry in self._hotkeys.items()}

    @property
    def hotkey_str(self) -> str:
        """当前默认快捷键字符串（pynput格式），兼容旧版接口"""
        return self.get_hotkey_str("toggle_window")

    @staticmethod
    def hotkey_to_display(hotkey_str: str) -> str:
        """将pynput格式快捷键转为显示格式
        
        例如: '<ctrl>+<shift>+h' -> 'Ctrl+Shift+H'
        """
        result = hotkey_str.replace('<ctrl>', 'Ctrl').replace('<alt>', 'Alt') \
                           .replace('<shift>', 'Shift').replace('<cmd>', 'Win') \
                           .replace('<super>', 'Win')
        # 将普通按键首字母大写
        parts = result.split('+')
        display_parts = []
        for part in parts:
            if part in ('Ctrl', 'Alt', 'Shift', 'Win'):
                display_parts.append(part)
            else:
                display_parts.append(part.upper())
        return '+'.join(display_parts)

    @staticmethod
    def display_to_hotkey(display: str) -> str:
        """将显示格式快捷键转为pynput格式
        
        例如: 'Ctrl+Shift+H' -> '<ctrl>+<shift>+h'
        """
        parts = [p.strip() for p in display.split('+')]
        result = []
        for part in parts:
            lower = part.lower()
            if lower in ('ctrl', 'control'):
                result.append('<ctrl>')
            elif lower in ('alt',):
                result.append('<alt>')
            elif lower in ('shift',):
                result.append('<shift>')
            elif lower in ('win', 'super', 'cmd', 'windows'):
                result.append('<cmd>')
            else:
                # 普通按键，小写
                result.append(lower)
        return '+'.join(result)

    @staticmethod
    def validate_hotkey(hotkey_str: str) -> bool:
        """验证快捷键字符串是否有效"""
        try:
            keys = keyboard.HotKey.parse(hotkey_str)
            return len(keys) > 0
        except Exception:
            return False