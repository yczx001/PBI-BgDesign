"""Register/unregister as Power BI Desktop External Tool via Windows Registry."""
import sys
import winreg


TOOL_NAME = "PBI-BgDesign"
DISPLAY_NAME = "PBI 背景设计"
DESCRIPTION = "为报表页设计美观的背景图和装饰元素"
REG_PATH = rf"Software\Microsoft\Power BI Desktop\External Tools\{TOOL_NAME}"


def register(exe_path: str | None = None, icon_path: str | None = None):
    """Register this tool in Power BI Desktop External Tools."""
    if exe_path is None:
        exe_path = sys.executable

    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, DISPLAY_NAME)
        winreg.SetValueEx(key, "Description", 0, winreg.REG_SZ, DESCRIPTION)
        winreg.SetValueEx(key, "Path", 0, winreg.REG_SZ, exe_path)
        winreg.SetValueEx(key, "Arguments", 0, winreg.REG_SZ, '"%pbi%"')
        if icon_path:
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon_path)
        winreg.CloseKey(key)
        print(f"Registered: {DISPLAY_NAME} in Power BI External Tools")
    except OSError as e:
        print(f"Failed to register: {e}")


def unregister():
    """Remove this tool from Power BI Desktop External Tools."""
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        print(f"Unregistered: {TOOL_NAME}")
    except FileNotFoundError:
        print(f"Not registered: {TOOL_NAME}")
    except OSError as e:
        print(f"Failed to unregister: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--unregister":
        unregister()
    else:
        register()
