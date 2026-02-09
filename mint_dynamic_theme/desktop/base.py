from abc import ABC, abstractmethod
from typing import Optional

class DesktopEnvironment(ABC):
    @abstractmethod
    def get_wallpaper(self) -> Optional[str]:
        """Returns the current wallpaper path."""
        pass

    @abstractmethod
    def apply_theme(self, theme_type: str, theme_name: str) -> bool:
        """Applies a specific theme setting."""
        pass

    @abstractmethod
    def monitor_changes(self, callback) -> None:
        """Starts monitoring for wallpaper changes. Should block or run a loop."""
        pass
    
    @abstractmethod
    def stop_monitoring(self) -> None:
        """Stops the monitoring process."""
        pass
