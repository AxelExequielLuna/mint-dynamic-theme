from .base import GSettingsDesktop

class CinnamonDesktop(GSettingsDesktop):
    def __init__(self):
        super().__init__(
            schema="org.cinnamon.desktop.background",
            key="picture-uri",
            theme_schemas={
                "gtk": "org.cinnamon.desktop.interface",
                "icon": "org.cinnamon.desktop.interface",
                "desktop": "org.cinnamon.theme",
            },
            theme_keys={"gtk": "gtk-theme", "icon": "icon-theme", "desktop": "name"}
        )
