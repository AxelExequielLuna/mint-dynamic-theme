from .base import GSettingsDesktop

class MateDesktop(GSettingsDesktop):
    def __init__(self):
        super().__init__(
            schema="org.mate.background",
            key="picture-filename",
            theme_schemas={
                "gtk": "org.mate.interface",
                "icon": "org.mate.interface",
                "desktop": "org.mate.Marco.general",
            },
            theme_keys={"gtk": "gtk-theme", "icon": "icon-theme", "desktop": "theme"}
        )
