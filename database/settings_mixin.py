"""应用设置和配置的数据库操作"""

from typing import Dict


class SettingsMixin:
    """应用设置和配置的数据库操作"""

    def save_app_setting(self, app_name: str, custom_category: str = None, is_sensitive: bool = False) -> None:
        """保存应用设置（分类/敏感标记，线程安全）"""
        self._execute("""
            INSERT OR REPLACE INTO app_settings (app_name, custom_category, is_sensitive)
            VALUES (?, ?, ?)
        """, (app_name, custom_category, 1 if is_sensitive else 0))

    def get_app_settings(self) -> Dict[str, Dict]:
        """获取所有应用设置"""
        rows = self._query_all("SELECT app_name, custom_category, is_sensitive FROM app_settings")
        return {
            row["app_name"]: {
                "custom_category": row["custom_category"],
                "is_sensitive": bool(row["is_sensitive"])
            }
            for row in rows
        }

    def get_sensitive_apps(self) -> set:
        """获取所有敏感应用名称集合"""
        rows = self._query_all("SELECT app_name FROM app_settings WHERE is_sensitive = 1")
        return {row["app_name"] for row in rows}

    def add_sensitive_app(self, app_name: str) -> None:
        """标记应用为敏感（线程安全）"""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT app_name FROM app_settings WHERE app_name = ?", (app_name,))
            if cursor.fetchone():
                cursor.execute("UPDATE app_settings SET is_sensitive = 1 WHERE app_name = ?", (app_name,))
            else:
                cursor.execute("INSERT INTO app_settings (app_name, is_sensitive) VALUES (?, 1)", (app_name,))
            conn.commit()

    def remove_sensitive_app(self, app_name: str) -> None:
        """取消应用的敏感标记（线程安全）"""
        self._execute("UPDATE app_settings SET is_sensitive = 0 WHERE app_name = ?", (app_name,))

    def set_app_category(self, app_name: str, category: str) -> None:
        """设置应用的自定义分类（线程安全）"""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT app_name FROM app_settings WHERE app_name = ?", (app_name,))
            if cursor.fetchone():
                cursor.execute("UPDATE app_settings SET custom_category = ? WHERE app_name = ?", (category, app_name))
            else:
                cursor.execute("INSERT INTO app_settings (app_name, custom_category) VALUES (?, ?)", (app_name, category))
            conn.commit()

    def save_config(self, key: str, value: str) -> None:
        """保存配置项（线程安全），同时更新内存缓存"""
        self._execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
        self._config_cache[key] = value

    def get_config(self, key: str, default: str = None) -> str:
        """获取配置项，优先从内存缓存读取"""
        if key in self._config_cache:
            return self._config_cache[key]
        row = self._query_one("SELECT value FROM config WHERE key = ?", (key,))
        value = row["value"] if row else default
        if value is not None:
            self._config_cache[key] = value
        return value
