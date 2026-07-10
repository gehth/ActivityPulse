"""Windows开机自启工具 - 通过注册表实现"""

import sys
import os

if sys.platform == 'win32':
    import winreg


def is_auto_start_enabled() -> bool:
    """检查是否已启用开机自启"""
    if sys.platform != 'win32':
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, "BehaviorRecord")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def enable_auto_start() -> bool:
    """启用开机自启"""
    if sys.platform != 'win32':
        return False
    try:
        # 获取可执行文件路径
        if getattr(sys, 'frozen', False):
            # PyInstaller打包后
            exe_path = sys.executable
        else:
            # 开发模式 - 使用pythonw启动main.py
            exe_path = f'"{sys.executable}" "{os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py")}"'
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "BehaviorRecord", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"启用开机自启失败: {e}")
        return False


def disable_auto_start() -> bool:
    """禁用开机自启"""
    if sys.platform != 'win32':
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        try:
            winreg.DeleteValue(key, "BehaviorRecord")
        except FileNotFoundError:
            pass  # 值不存在，无需删除
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"禁用开机自启失败: {e}")
        return False