from __future__ import annotations

from datetime import datetime


class FileNameService:
    def timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def sanitize_filename(self, name: str) -> str:
        """Sanitize a filename by removing/replacing invalid characters."""
        if not name:
            return ""
        invalid_chars = '<>:"/\\|?*'
        sanitized = name.strip()
        for char in invalid_chars:
            sanitized = sanitized.replace(char, "_")
        sanitized = sanitized.strip(". ")
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        return sanitized

    def generate_filename(self, base_name: str, extension: str, custom_name: str | None = None) -> str:
        """Generate a filename with custom name or timestamp fallback."""
        if custom_name and custom_name.strip():
            sanitized = self.sanitize_filename(custom_name.strip())
            if sanitized:
                return f"{sanitized}.{extension}"
        return f"{self.timestamp()}.{extension}"

