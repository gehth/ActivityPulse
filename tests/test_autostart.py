"""autostart Windows开机自启工具单元测试"""
import sys
import pytest
from unittest.mock import patch, MagicMock


class TestIsAutoStartEnabled:
    """is_auto_start_enabled 检查开机自启状态测试"""

    @pytest.mark.skipif(sys.platform != 'win32', reason="Windows only")
    def test_returns_true_when_enabled(self):
        """注册表中有值时应返回True"""
        mock_key = MagicMock()
        with patch('utils.autostart.winreg') as mock_winreg:
            mock_winreg.HKEY_CURRENT_USER = 0x80000001
            mock_winreg.KEY_READ = 0x20019
            mock_winreg.OpenKey.return_value = mock_key
            mock_winreg.QueryValueEx.return_value = ("C:\\app.exe",)

            from utils.autostart import is_auto_start_enabled
            result = is_auto_start_enabled()

        assert result is True
        mock_winreg.CloseKey.assert_called_with(mock_key)

    @pytest.mark.skipif(sys.platform != 'win32', reason="Windows only")
    def test_returns_false_when_not_enabled(self):
        """注册表中没有值时应返回False"""
        mock_key = MagicMock()
        with patch('utils.autostart.winreg') as mock_winreg:
            mock_winreg.HKEY_CURRENT_USER = 0x80000001
            mock_winreg.KEY_READ = 0x20019
            mock_winreg.OpenKey.return_value = mock_key
            mock_winreg.QueryValueEx.side_effect = FileNotFoundError

            from utils.autostart import is_auto_start_enabled
            result = is_auto_start_enabled()

        assert result is False

    def test_returns_false_on_non_windows(self):
        """非Windows平台应返回False"""
        with patch.object(sys, 'platform', 'linux'):
            import importlib
            import utils.autostart
            importlib.reload(utils.autostart)
            result = utils.autostart.is_auto_start_enabled()

        assert result is False


class TestEnableAutoStart:
    """enable_auto_start 启用开机自启测试"""

    @pytest.mark.skipif(sys.platform != 'win32', reason="Windows only")
    def test_returns_true_on_success(self):
        """成功设置注册表应返回True"""
        mock_key = MagicMock()
        with patch('utils.autostart.winreg') as mock_winreg:
            mock_winreg.HKEY_CURRENT_USER = 0x80000001
            mock_winreg.KEY_SET_VALUE = 0x0002
            mock_winreg.REG_SZ = 1
            mock_winreg.OpenKey.return_value = mock_key

            from utils.autostart import enable_auto_start
            result = enable_auto_start()

        assert result is True

    def test_returns_false_on_non_windows(self):
        """非Windows平台应返回False"""
        with patch.object(sys, 'platform', 'linux'):
            import importlib
            import utils.autostart
            importlib.reload(utils.autostart)
            result = utils.autostart.enable_auto_start()

        assert result is False


class TestDisableAutoStart:
    """disable_auto_start 禁用开机自启测试"""

    @pytest.mark.skipif(sys.platform != 'win32', reason="Windows only")
    def test_returns_true_on_success(self):
        """成功删除注册表值应返回True"""
        mock_key = MagicMock()
        with patch('utils.autostart.winreg') as mock_winreg:
            mock_winreg.HKEY_CURRENT_USER = 0x80000001
            mock_winreg.KEY_SET_VALUE = 0x0002
            mock_winreg.OpenKey.return_value = mock_key

            from utils.autostart import disable_auto_start
            result = disable_auto_start()

        assert result is True

    @pytest.mark.skipif(sys.platform != 'win32', reason="Windows only")
    def test_returns_true_when_value_not_exists(self):
        """值不存在时也应返回True（幂等）"""
        mock_key = MagicMock()
        with patch('utils.autostart.winreg') as mock_winreg:
            mock_winreg.HKEY_CURRENT_USER = 0x80000001
            mock_winreg.KEY_SET_VALUE = 0x0002
            mock_winreg.OpenKey.return_value = mock_key
            mock_winreg.DeleteValue.side_effect = FileNotFoundError

            from utils.autostart import disable_auto_start
            result = disable_auto_start()

        assert result is True

    def test_returns_false_on_non_windows(self):
        """非Windows平台应返回False"""
        with patch.object(sys, 'platform', 'linux'):
            import importlib
            import utils.autostart
            importlib.reload(utils.autostart)
            result = utils.autostart.disable_auto_start()

        assert result is False