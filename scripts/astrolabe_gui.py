from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QByteArray, QPointF, QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QFont, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFileDialog, QFontComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox, QSplitter, QTabWidget, QTextEdit, QInputDialog,
    QVBoxLayout, QWidget,
    QTextBrowser,
)

from draw_projection import (
    AZIMUTHAL_EQUIDISTANT, STEREOGRAPHIC, build_parser, parse_args, svg_bytes,
)
from perspective_corrector import rectify_mode_b
from draw_star_chart import build_parser as build_star_parser
from draw_astrolabe_back import build_parser as build_back_parser, render_back, LABEL_GROUPS, validate as validate_back
from draw_astrolabe_ruler import build_parser as build_ruler_parser, render_ruler, validate_ruler
from star_chart import available_cultures, default_data_cache, download_star_data, render_star_chart, validate_star_cache


TASKS = {
    "draw-azimuthal-equidistant": AZIMUTHAL_EQUIDISTANT,
    "draw-stereographic": STEREOGRAPHIC,
}

UI = {
    "en": {
        "file": "File", "settings": "Settings", "language": "Language",
        "english": "English", "chinese": "中文", "import": "Import Configuration…", "export_config": "Export Configuration…",
        "save": "Save", "save_as": "Save As…", "exit": "Exit",
        "azimuthal": "Azimuthal Equidistant", "stereographic": "Stereographic",
        "perspective": "Perspective Correction", "update": "Update Preview",
        "main": "Main", "ecliptic": "Ecliptic", "ready": "Set the arguments, then click Update Preview to refresh the whole workspace.",
        "updated": "Preview updated.", "updated_pair": "Main and Ecliptic previews updated.", "error": "Error: {value}",
        "main_updated": "Main preview updated.", "ecliptic_updated": "Ecliptic preview updated.",
        "star_failed": "Star Chart preview failed: {value}",
        "main_failed": "Main preview failed: {value}", "ecliptic_failed": "Ecliptic preview failed: {value}",
        "imported": "Configuration imported. Update the preview to render it.",
        "saved": "Saved: {value}", "need_preview": "Update the preview before saving.",
        "load": "Load Image", "undo": "Undo Point", "reset": "Reset",
        "rectify": "Update Preview / Rectify", "pick4": "Load an image, then click its four corners in order.",
        "pick4_short": "Click the four corners in order.", "reset_done": "Reset complete.",
        "need4": "Load an image and select exactly four corner points.", "rectified": "Correction preview updated.",
        "need_rectify": "Complete a correction preview before saving.", "load_title": "Load Image",
        "images": "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)", "read_failed": "Could not read the image.",
        "paste_title": "Paste Configuration", "paste_help": "Paste a pixi command, PowerShell @() arguments, or plain args:",
        "import_title": "Import Configuration", "import_how": "Open a file or paste configuration text?",
        "open_file": "Open File", "paste": "Paste", "open_config": "Open Configuration",
        "text_files": "Text (*.txt *.md *.ps1);;All files (*)", "task_missing": "No drawing task was found in the configuration.",
        "import_failed": "Import Failed", "bad_args": "Invalid argument format.", "save_failed": "Save Failed",
        "save_title": "Save As", "write_failed": "Could not save {value}", "unsupported": "Unsupported format: {value}",
        "automatic": "Automatic", "ok": "OK", "cancel": "Cancel",
        "export_title": "Export Configuration", "config_files": "Text (*.txt)",
        "projection_only": "Configuration export is available on drawing tabs only.", "export_failed": "Export Failed",
        "exported": "Configuration exported: {value}",
        "help": "Help", "gui_help": "GUI Usage", "about": "About", "close": "Close",
        "dpi": "Raster Export DPI…", "dpi_title": "Raster Export DPI", "dpi_prompt": "DPI for PNG and JPEG export:",
    },
    "zh": {
        "file": "文件", "settings": "设置", "language": "语言",
        "english": "English", "chinese": "中文", "import": "导入配置…", "export_config": "导出配置…",
        "save": "保存", "save_as": "另存为…", "exit": "退出",
        "azimuthal": "等距方位投影", "stereographic": "球极投影", "perspective": "透视校正",
        "update": "更新预览", "main": "主图", "ecliptic": "黄道图",
        "ready": "设置参数后点击“更新预览”，将刷新当前工作区的全部图。", "updated": "预览已更新。", "updated_pair": "主图和黄道图预览已更新。", "error": "错误：{value}",
        "main_updated": "主图预览已更新。", "ecliptic_updated": "黄道图预览已更新。",
        "main_failed": "主图预览更新失败：{value}", "ecliptic_failed": "黄道图预览更新失败：{value}",
        "star_failed": "星图预览更新失败：{value}",
        "imported": "配置已导入，请更新预览。", "saved": "已保存：{value}", "need_preview": "请先更新预览。",
        "load": "载入图片", "undo": "撤销点", "reset": "重置", "rectify": "更新预览 / 校正",
        "pick4": "载入图片，然后依次点击四个角点。", "pick4_short": "依次点击四个角点。", "reset_done": "已重置。",
        "need4": "需要载入图片并选择四个角点。", "rectified": "校正预览已更新。", "need_rectify": "请先完成校正预览。",
        "load_title": "载入图片", "images": "图片 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)", "read_failed": "无法读取图片。",
        "paste_title": "粘贴配置", "paste_help": "粘贴 pixi 命令、PowerShell @() 参数或纯 args：",
        "import_title": "导入配置", "import_how": "从文件读取，还是粘贴配置？", "open_file": "打开文件",
        "paste": "粘贴", "open_config": "打开配置", "text_files": "文本 (*.txt *.md *.ps1);;所有文件 (*)",
        "task_missing": "配置中未找到绘图 task。", "import_failed": "导入失败", "bad_args": "参数格式错误。",
        "save_failed": "保存失败", "save_title": "另存为", "write_failed": "无法保存 {value}", "unsupported": "不支持的格式：{value}",
        "automatic": "自动", "ok": "确定", "cancel": "取消",
        "export_title": "导出配置", "config_files": "文本 (*.txt)",
        "projection_only": "仅绘图标签页支持导出配置。", "export_failed": "导出失败",
        "exported": "配置已导出：{value}",
        "help": "帮助", "gui_help": "GUI 使用说明", "about": "关于", "close": "关闭",
        "dpi": "栅格导出 DPI…", "dpi_title": "栅格导出 DPI", "dpi_prompt": "PNG 和 JPEG 导出 DPI：",
    },
}

# Star-chart strings are kept together so additions do not depend on the legacy
# projection translation table above.
UI["en"].update({
    "star_chart": "Star Chart", "astronomy_data": "Astronomical Data…",
    "data_title": "Astronomical Data", "cache_location": "Cache: {value}",
    "cache_ready": "HYG 4.1 and Stellarium 26.1 are available.",
    "cache_missing": "Data are missing. Download them before updating the preview.",
    "download_update": "Download / Update", "clear_cache": "Clear Cache",
    "open_cache": "Open Cache Folder", "download_done": "Astronomical data downloaded.",
    "view_licenses": "View Licenses", "licenses_title": "Astronomical Data Licenses",
    "clear_done": "Astronomical data cache cleared.", "confirm_clear": "Clear all cached astronomical data?",
    "star_summary": "Updated: {stars} stars, {segments} line segments, {labels} labels; {hidden} hidden, {missing} missing identifiers, {degraded} degraded motions.",
})
UI["zh"].update({
    "star_chart": "星图", "astronomy_data": "天文数据…",
    "data_title": "天文数据", "cache_location": "缓存位置：{value}",
    "cache_ready": "HYG 4.1 与 Stellarium 26.1 数据已就绪。",
    "cache_missing": "缺少数据，请先下载后再更新预览。",
    "download_update": "下载 / 更新", "clear_cache": "清理缓存",
    "open_cache": "打开缓存目录", "download_done": "天文数据下载完成。",
    "view_licenses": "查看许可", "licenses_title": "天文数据许可",
    "clear_done": "天文数据缓存已清理。", "confirm_clear": "确定清理全部天文数据缓存吗？",
    "star_summary": "已更新：{stars} 颗恒星、{segments} 条连线、{labels} 个标签；隐藏 {hidden} 个，缺失标识符 {missing} 个，降级空间运动 {degraded} 个。",
})

STAR_ARG_ZH = {
    "milky_way": "叠加银河轮廓线", "milky_way_width": "银河轮廓线宽",
    "equator": "叠加赤道", "equator_width": "赤道线宽",
    "ecliptic": "叠加黄道", "ecliptic_width": "黄道线宽",
    "center": "中心极点", "range_declination": "边界赤纬", "projection": "投影方法",
    "diameter": "星图直径", "boundary_width": "轮廓线宽", "rotation": "旋转角度", "rotation_direction": "旋转方向",
    "epoch_year": "目标年份", "magnitude_max": "视星等上限",
    "magnitude_levels": "视星等级数", "star_diameter_max": "最亮级星点直径", "star_diameter_min": "最暗级星点直径",
    "star_stroke_width": "星点边缘线宽", "fill_stars": "填充星点",
    "constellation_lines": "显示星座连线", "sky_culture": "星空文化体系",
    "constellation_width": "星座连线宽度", "show_star_names": "显示恒星名",
    "star_name_language": "恒星名语言", "star_name_font": "恒星名字体",
    "star_name_size": "恒星名字号", "star_name_position": "恒星名首选位置",
    "star_name_radial_offset": "恒星名径向偏移", "star_name_tangential_offset": "恒星名切向偏移",
    "show_constellation_names": "显示星座／星官名", "constellation_name_language": "星座／星官名语言",
    "constellation_name_font": "星座／星官名字体", "constellation_name_size": "星座／星官名字号",
    "constellation_name_position": "星座／星官名首选位置",
    "constellation_name_radial_offset": "星座／星官名径向偏移",
    "constellation_name_tangential_offset": "星座／星官名切向偏移",
    "avoid_label_overlap": "自动避让标签",
}

STAR_HELP_ZH = {
    "milky_way": "叠加本地 d3-celestial 数据中的五级银河亮度轮廓，按星图年份进行岁差转换。缺少数据时请在设置 → 天文数据中更新。",
    "milky_way_width": "银河轮廓线宽，单位为毫米。",
    "equator": "在星图上叠加天球赤道，随当前投影、旋转和赤纬范围绘制。",
    "equator_width": "赤道线宽，单位为毫米。",
    "ecliptic": "在星图上叠加黄道，沿用投影图的黄赤交角，并随当前投影、旋转和赤纬范围绘制。",
    "ecliptic_width": "黄道线宽，单位为毫米。",
    "center": "选择星图中心为北天极或南天极。", "range_declination": "圆形边界处的赤纬，单位为度；北纬为正，南纬为负。",
    "projection": "选择等距方位投影或球极投影。", "diameter": "圆形星图边界直径，单位为毫米。",
    "boundary_width": "星图外轮廓线宽，单位为毫米。", "rotation": "整体旋转星图，单位为度。",
    "rotation_direction": "设置赤经围绕星图递增的顺时针或逆时针方向。",
    "epoch_year": "从 J2000 应用空间运动和岁差的目标年份。",
    "magnitude_max": "纳入星图的最暗视星等上限；数值小于等于该上限的恒星全部绘制。", "magnitude_levels": "将默认恒星亮度范围等宽划分的级数。",
    "star_diameter_max": "最亮视星等级的星点直径，单位为毫米。",
    "star_diameter_min": "最暗视星等级的星点直径，单位为毫米；中间等级采用线性插值。", "star_stroke_width": "星点边缘线宽，单位为毫米。",
    "fill_stars": "启用时填充星点，关闭时绘制空心星点。", "constellation_lines": "显示所选星空文化的星座／星官连线。",
    "sky_culture": "从本地 Stellarium 缓存中选择星空文化体系。", "constellation_width": "星座／星官连线宽度，单位为毫米。",
    "show_star_names": "显示可见恒星的名称。", "show_constellation_names": "显示星座／星官名称。",
    "star_name_language": "选择星名使用英语或汉语；此设置独立于软件界面语言。",
    "constellation_name_language": "选择星座／星官名使用英语或汉语；此设置独立于软件界面语言。",
    "avoid_label_overlap": "依次尝试八个位置；仍碰撞时隐藏该标签。",
}

STAR_CHOICE_ZH = {
    "north": "北极", "south": "南极", "azimuthal-equidistant": "等距方位投影", "stereographic": "球极投影",
    "en": "英文", "zh": "中文", "northwest": "左上", "northeast": "右上", "southwest": "左下", "southeast": "右下",
    "east": "右", "west": "左",
}
STAR_CHOICE_ZH.update({"en": "英语", "zh": "汉语", "clockwise": "顺时针", "counterclockwise": "逆时针"})
STAR_CHOICE_EN = {"en": "English", "zh": "Chinese"}
STAR_POSITION_ZH = {"north": "上", "northeast": "右上", "east": "右", "southeast": "右下", "south": "下", "southwest": "左下", "west": "左", "northwest": "左上"}

ARG_ZH = {
    "latitude": "观察者纬度", "center": "投影中心极点", "range_latitude": "边界纬度", "diameter": "投影直径",
    "azimuth_lines": "方位线间隔", "altitude_lines": "高度线间隔", "sub_azimuth_lines": "方位子分格数",
    "sub_altitude_lines": "高度子分格数", "boundary_width": "外边界线宽", "horizon_width": "地平线线宽",
    "azimuth_width": "方位线线宽", "altitude_width": "高度线线宽", "sub_azimuth_width": "方位子线线宽",
    "sub_altitude_width": "高度子线线宽", "civil_twilight": "民用曙暮光线", "nautical_twilight": "航海曙暮光线",
    "astronomical_twilight": "天文曙暮光线", "twilight_width": "曙暮光线宽", "twilight_style": "曙暮光线型",
    "astronomical_twilight_width": "旧版曙暮光备用线宽", "equator_tropics": "天赤道与回归线",
    "equator_tropics_width": "天赤道与回归线线宽", "ecliptic": "黄道伴随图", "ecliptic_width": "黄道线宽",
    "ecliptic_band_width": "黄道带宽度", "ecliptic_angle_lines": "黄道主刻度间隔",
    "sub_ecliptic_angle_lines": "黄道子分格数", "ecliptic_angle_width": "黄道主刻度线宽",
    "sub_ecliptic_angle_width": "黄道子刻度线宽", "date_ring": "日期环", "date_ring_width": "日期环边界线宽",
    "date_ring_band_width": "日期环带宽", "date_ring_month_width": "月界刻度线宽",
    "date_ring_sub_width": "日期环子刻度线宽", "date_ring_sub_interval": "日期环子刻度间隔",
    "date_ring_sub_sub_width": "日期环次级子刻度线宽", "date_ring_sub_sub_interval": "日期环次级子刻度间隔",
    "date_ring_month_labels": "月份标签", "date_ring_month_label_size": "月份标签大小",
    "date_ring_month_label_width": "月份标签线宽", "date_ring_month_label_line_position": "月份标签径向位置",
    "date_ring_month_label_arc_adjust": "月份标签圆周调整", "date_ring_month_label_letter_spacing": "月份标签字距",
    "reverse_date_ring_month_label_orientation": "反转月份标签方向", "rotate_date_ring_180": "日期环旋转 180°",
    "date_ring_year": "日期环参考年份", "ecliptic_rotation_direction": "黄道旋转方向",
    "day_unequal_hour_lines": "白昼不等时线", "night_unequal_hour_lines": "夜间不等时线",
    "unequal_hour_width": "不等时线宽", "day_unequal_hour_labels": "白昼不等时标签",
    "night_unequal_hour_labels": "夜间不等时标签", "unequal_hour_label_style": "不等时标签数字样式",
    "unequal_hour_label_size": "不等时标签大小", "unequal_hour_label_width": "不等时标签线宽",
    "unequal_hour_label_line_position": "不等时标签线位置", "unequal_hour_label_arc_adjust": "不等时标签圆弧调整",
    "solar_motion_direction": "太阳运动方向", "unequal_hour_label_letter_spacing": "不等时标签字距",
    "azimuth_labels": "方位标签", "azimuth_label_size": "方位标签大小", "azimuth_label_width": "方位标签线宽",
    "azimuth_label_position": "方位标签位置", "azimuth_label_center_adjust": "方位标签居中调整",
    "azimuth_label_letter_spacing": "方位标签字距", "crosshair": "中心十字线", "crosshair_width": "十字线备用线宽",
    "crosshair_horizontal_width": "水平十字线宽", "crosshair_vertical_width": "垂直十字线宽",
    "rotate_180": "投影旋转 180°",
}

CHOICE_ZH = {
    "north": "北极", "south": "南极", "solid": "实线", "dashed": "虚线",
    "clockwise": "顺时针", "counterclockwise": "逆时针", "roman": "罗马数字", "arabic": "阿拉伯数字",
}


def read_readme_help() -> dict[str, str]:
    """Load the canonical per-option descriptions from README bullet items."""
    try:
        text = Path(__file__).resolve().parent.parent.joinpath("README.md").read_text(encoding="utf-8")
    except OSError:
        return {}
    result: dict[str, str] = {}
    for option, description in re.findall(r"^- `(--[\w-]+)` (.+)$", text, re.MULTILINE):
        result[option] = description.strip()
    return result


README_HELP_EN = read_readme_help()


def read_readme_gui_section() -> str:
    try:
        text = Path(__file__).resolve().parent.parent.joinpath("README.md").read_text(encoding="utf-8")
    except OSError:
        return "# Desktop GUI\n\nRun `pixi run gui` to start the application."
    match = re.search(r"^## Desktop GUI\s*$\n(.*?)(?=^##\s|\Z)", text, re.MULTILINE | re.DOTALL)
    return "## Desktop GUI\n\n" + match.group(1).strip() if match else "## Desktop GUI\n\nRun `pixi run gui`."


README_GUI_EN = read_readme_gui_section()

README_GUI_ZH = """## GUI 使用说明

使用以下命令启动集成桌面应用：

```powershell
pixi run gui
```

前两个标签页分别对应等距方位投影和球极投影。基础参数始终显示；只有启用父功能后，相关的从属参数才会出现。将鼠标悬停在参数名称上可查看说明。设置完成后，点击 **更新预览** 会同时刷新当前工作区的主图、黄道图和星图，并保留当前标签位置。某一张图失败时会保留其上一版有效预览，其他图仍会继续更新。预览不会覆盖已有文件。

启用黄道输出后，预览区的 **黄道图** 标签会启用，并显示独立的伴随图。

在透视校正标签页中载入图片，依次点击四个角点，再点击 **更新预览 / 校正**。执行校正前可以撤销选点或重置。

使用 **文件 > 导入配置** 可以打开 README、TXT 或 PowerShell 文件，也可以粘贴 `pixi run` 命令、PowerShell `@(...)` 参数列表或纯命令行参数。导入操作只解析文本，不会执行其中的命令。

使用 **文件 > 导出配置** 可以把当前绘图标签页的有效参数保存为 `.txt`。导出的文件可以再次导入。

使用 **保存** 或 **另存为** 可输出 SVG、透明背景 PNG 或白色背景 JPEG。可在 **设置 > 栅格导出 DPI** 中调整栅格分辨率，默认为 300 DPI。启用黄道图时，会同时保存带 `_ecliptic` 后缀的伴随文件。

应用默认使用英文。可通过 **设置 > 语言** 在英文和中文之间切换；修改立即全局生效，并会保存到下次启动。

等距方位投影和球极投影各自是一个完整工作区。每个工作区右侧都有并列的 **主图 / 黄道图 / 星图** 标签；左侧始终保留同样顺序的三个参数 section。切换右侧标签时，参数面板会自动滚动到对应 section。导出配置会同时保存当前工作区的投影参数与星图参数，重新导入时一起恢复。

**星图** 标签页使用 HYG 恒星表和 Stellarium 星空文化数据。首次使用前打开 **设置 > 天文数据** 下载缓存；这里也可以更新、清理、打开缓存目录和查看许可。更新星图预览不会自动联网。视星等级数会动态生成相同数量的星点直径输入框；星座连线、恒星名、星座／星官名及避让设置会按各自开关显示。预览状态会报告恒星、连线、标签、隐藏标签、缺失标识符和降级空间运动数量。
"""


def gui_help_markdown(language: str) -> str:
    if language == "zh":
        introduction = README_GUI_ZH.replace("\n\n", "\n\n向着星辰与深渊，欢迎使用本星盘辅助设计工具！\n\n", 1)
        introduction = introduction.replace("视星等级数会动态生成相同数量的星点直径输入框", "星点直径只设置最亮级和最暗级两个端点，中间等级采用线性插值")
        return introduction + "\n\n星图不再重复显示工作区的几何参数：中心极点、边界纬度、投影方法、直径和轮廓线宽均继承自主图 section，并会以继承后的值写入导出的星图命令。星图的 0h 保持在顶部，赤经递增方向继承黄道旋转方向；黄道方向为自动时继承太阳运动方向。星名语言和星座／星官名语言可分别选择英语或汉语，只控制生成图中的文字，不跟随软件界面语言。"
    return README_GUI_EN


REPOSITORY_URL = "https://github.com/Schuai/Astrolabe-Projection-Drawers"
HYG_SOURCE_URL = "https://github.com/astronexus/HYG-Database/tree/main/hyg"
STELLARIUM_SOURCE_URL = "https://github.com/Stellarium/stellarium/releases/tag/v26.1"


def about_markdown(language: str) -> str:
    if language == "zh":
        return f"""# Astrolabe Projection Drawers

向着星辰与深渊，欢迎使用本星盘辅助设计工具！

用于生成星盘投影、黄道伴随图和极区星图的桌面应用。

**仓库地址**  
[{REPOSITORY_URL}]({REPOSITORY_URL})

**本项目许可**  
GNU General Public License v3.0（GPL-3.0）。完整条款见仓库根目录的 `LICENSE` 文件。

## 天文数据来源与许可

- [HYG Database 4.1]({HYG_SOURCE_URL})：恒星目录，采用 CC BY-SA 4.0 许可。
- [Stellarium 26.1 Sky Cultures]({STELLARIUM_SOURCE_URL})：星座连线、名称与中文翻译，来源项目采用 GPL-2.0。各个贡献的星空文化包可能声明附加或不同许可。

重新分发数据或衍生作品前，请同时检查数据缓存清单和缓存中保留的各文化包许可文件。
"""
    return f"""# Astrolabe Projection Drawers

Ad astra abyssosque—welcome to this astrolabe design assistant!

A desktop application for astrolabe projections, ecliptic companion drawings, and polar star charts.

**Repository**  
[{REPOSITORY_URL}]({REPOSITORY_URL})

**Project license**  
GNU General Public License v3.0 (GPL-3.0). See the repository's root `LICENSE` file for the complete terms.

## Astronomical data sources and licenses

- [HYG Database 4.1]({HYG_SOURCE_URL}): stellar catalogue, licensed under CC BY-SA 4.0.
- [Stellarium 26.1 Sky Cultures]({STELLARIUM_SOURCE_URL}): constellation lines, names, and Chinese translations, from the GPL-2.0 project. Individual contributed sky cultures may declare additional or different licenses.

Before redistributing data or derived work, also review the cache manifest and the individual culture license files preserved in the cache.
"""

HELP_ZH = {
    "latitude": "设置观察者纬度，单位为度，范围为 -90 至 90。",
    "center": "选择投影以北极还是南极为中心。",
    "range_latitude": "设置投影外边界所表示的纬度；负值表示南纬。",
    "diameter": "设置投影范围圆的直径，单位为毫米。",
    "azimuth_lines": "每隔 N 度绘制一条方位线；设为 0 时禁用。",
    "altitude_lines": "每隔 N 度绘制一条高度线；设为 0 时禁用。",
    "sub_azimuth_lines": "将每个方位主间隔分成 N 格；0 或 1 表示禁用子线。",
    "sub_altitude_lines": "将每个高度主间隔分成 N 格；0 或 1 表示禁用子线。",
    "civil_twilight": "绘制高度 -6° 的民用曙暮光线。",
    "nautical_twilight": "绘制高度 -12° 的航海曙暮光线。",
    "astronomical_twilight": "绘制高度 -18° 的天文曙暮光线。",
    "twilight_style": "设置已启用曙暮光线为实线或虚线。",
    "astronomical_twilight_width": "当未设置统一曙暮光线宽时使用的旧版备用线宽。",
    "equator_tropics": "绘制天赤道、北回归线和南回归线。",
    "ecliptic": "为相同投影生成独立的黄道伴随 SVG。",
    "ecliptic_band_width": "设置黄道与其内侧同心曲线之间的带宽；自动时采用黄道圆半径。",
    "ecliptic_angle_lines": "每隔 N 度绘制黄道主刻度；设为 0 时禁用。",
    "sub_ecliptic_angle_lines": "将每个黄道主刻度间隔分成 N 格；0 或 1 表示禁用。",
    "date_ring": "在黄道伴随图的投影计数圆外侧绘制日期环。",
    "date_ring_band_width": "设置投影计数圆与日期环外边界之间的径向宽度，单位为毫米。",
    "date_ring_sub_interval": "设置日期环子刻度的日期间隔；1 为每日，0 为禁用。",
    "date_ring_sub_sub_interval": "设置日期环次级子刻度的日期间隔；1 为每日，0 为禁用。",
    "date_ring_month_labels": "在日期环上用阿拉伯数字标注各月起点。",
    "date_ring_month_label_line_position": "设置月份标签在日期环带内的径向位置：0 靠外，1 靠内，负值向外延伸。",
    "date_ring_month_label_arc_adjust": "按角度沿日期环调整月份标签；正值移向较晚日期，负值移向较早日期。",
    "reverse_date_ring_month_label_orientation": "反转月份标签的径向方向，使标签底部朝向中心。",
    "rotate_date_ring_180": "将整个日期环旋转 180°。",
    "date_ring_year": "选择用于优化日期环相位的历年；日期环始终使用 365 个等分。",
    "ecliptic_rotation_direction": "设置黄经和日期环日期按顺时针或逆时针递增；自动时跟随太阳运动方向。",
    "day_unequal_hour_lines": "绘制 11 条白昼不等时线，将日出至日落分为 12 个等时段。",
    "night_unequal_hour_lines": "绘制 11 条夜间不等时线，将日落至日出分为 12 个等时段。",
    "day_unequal_hour_labels": "标注白昼不等时线；仅在对应线条启用时生效。",
    "night_unequal_hour_labels": "标注夜间不等时线；仅在对应线条启用时生效。",
    "unequal_hour_label_style": "选择不等时标签使用罗马数字或阿拉伯数字。",
    "unequal_hour_label_line_position": "设置标签沿不等时线的位置：0 靠近外侧锚点，1 向内，负值向外延伸。",
    "unequal_hour_label_arc_adjust": "在 -1 至 1 范围内沿标签圆调整不等时标签。",
    "solar_motion_direction": "设置太阳运动、不等时编号及方位标签的递增方向。",
    "azimuth_labels": "在地平线与天文曙暮光线之间添加八个主要方位标签。",
    "azimuth_label_position": "设置方位标签在地平线（0）与天文曙暮光线（1）之间的位置。",
    "azimuth_label_center_adjust": "沿局部切线微调方位标签的居中位置，单位为毫米。",
    "crosshair": "绘制贯穿整个投影的水平与垂直中心线。",
    "crosshair_width": "未指定水平或垂直线宽时，两条十字线共用的备用线宽。",
    "crosshair_horizontal_width": "设置水平十字线线宽；只设置单轴时另一轴默认不绘制。",
    "crosshair_vertical_width": "设置垂直十字线线宽；只设置单轴时另一轴默认不绘制。",
    "rotate_180": "将整个投影旋转 180°，使天空区域位于图像下方。",
}


def chinese_help(action: argparse.Action) -> str:
    if action.dest in HELP_ZH:
        return HELP_ZH[action.dest]
    label = ARG_ZH.get(action.dest, action.option_strings[0])
    if action.dest.endswith("letter_spacing"): return f"设置{label}，单位为毫米。"
    if action.dest.endswith("_width"): return f"设置{label}，单位为毫米。"
    if action.dest.endswith("_size"): return f"设置{label}，单位为毫米。"
    if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction, argparse.BooleanOptionalAction)):
        return f"启用或禁用{label}。"
    return f"设置{label}；输入值会在更新预览时校验。"


ERROR_ZH = {
    "azimuth-label-position must be within [0, 1].": "方位标签位置必须在 0 至 1 之间。",
    "unequal-hour-label-line-position cannot be greater than 1.": "不等时标签线位置不能大于 1。",
    "date-ring-month-label-line-position cannot be greater than 1.": "月份标签径向位置不能大于 1。",
    "unequal-hour-label-arc-adjust must be within [-1, 1].": "不等时标签圆弧调整必须在 -1 至 1 之间。",
    "diameter must be positive.": "投影直径必须大于 0。",
    "azimuth-lines must be less than 360, or 0 to disable.": "方位线间隔必须小于 360，或设为 0 以禁用。",
    "altitude-lines must be less than 90, or 0 to disable.": "高度线间隔必须小于 90，或设为 0 以禁用。",
    "ecliptic-angle-lines must be less than 360, or 0 to disable.": "黄道主刻度间隔必须小于 360，或设为 0 以禁用。",
    "twilight-width cannot be negative.": "曙暮光线宽不能为负数。",
    "date-ring requires ecliptic output to be enabled.": "启用日期环前必须先启用黄道伴随图。",
    "date-ring-year must be positive.": "日期环参考年份必须为正数。",
    "range-latitude collapses the projection to zero radius.": "该边界纬度会使投影半径变为零。",
    "range-latitude reaches the antipodal pole and diverges in stereographic projection.": "边界纬度到达对跖极点，球极投影将在此处发散。",
    "Adjacent selected points are too close together.": "相邻选点距离过近。",
    "Selected quadrilateral is too small or degenerate.": "所选四边形过小或已经退化。",
}

ERROR_ZH.update({
    "star-diameters must contain positive values": "各级星点直径必须全部为正数。",
    "invalid magnitude range or level count": "视星等范围或分级数量无效。",
    "range-declination must be within [-90, 90]": "边界赤纬必须在 -90° 至 90° 之间。",
    "diameter must be positive": "星图直径必须大于 0。",
    "magnitude-levels must be positive": "视星等级数必须大于 0。",
    "star-diameters count must equal magnitude-levels": "星点直径数量必须与视星等级数一致。",
    "range-declination is invalid for this projection center": "边界赤纬不适用于当前中心极点与投影组合。",
    "Cache manifest is missing or invalid": "缓存清单缺失或无效。",
    "Cache manifest contains no file hashes": "缓存清单中没有文件哈希。",
})


def localized_error(error: object, language: str) -> str:
    message = str(error)
    if language != "zh": return message
    if message in ERROR_ZH: return ERROR_ZH[message]
    if message.startswith("Star data is missing:"): return "缺少恒星数据，请在“设置 → 天文数据”中下载。"
    if message.startswith("Milky Way data is missing:"): return "缺少银河轮廓数据，请在“设置 → 天文数据”中更新，或运行 pixi run download-star-data --milky-way-only。"
    if message == "Invalid Milky Way GeoJSON data": return "银河轮廓数据格式无效，请重新下载。"
    if message.startswith("Sky culture is missing:"): return "缺少所选星空文化数据，请在“设置 → 天文数据”中下载或更新。"
    if message.startswith("Missing cached file:"): return "缓存文件缺失：" + message.split(":", 1)[1].strip()
    if message.startswith("Cached file hash mismatch:"): return "缓存文件哈希不匹配：" + message.split(":", 1)[1].strip()
    if message.startswith("All HYG download sources failed:"): return "所有 HYG 下载源均失败，请检查网络连接后重试。"
    if message == "Downloaded HYG file has an invalid schema": return "下载的 HYG 文件字段结构无效。"
    if message.startswith("Downloaded Stellarium archive is corrupt:"): return "下载的 Stellarium 压缩包已损坏，请重新下载。"
    if message == "Downloaded Stellarium archive contains no sky cultures": return "下载的 Stellarium 压缩包不包含星空文化数据。"
    match = re.fullmatch(r"([\w-]+) must be within \[(-?[\d.]+), (-?[\d.]+)\] degrees\.", message)
    if match:
        dest = match.group(1).replace("-", "_")
        return f"{ARG_ZH.get(dest, match.group(1))}必须在 {match.group(2)}° 至 {match.group(3)}° 之间。"
    match = re.fullmatch(r"([\w-]+) cannot be negative\.", message)
    if match:
        dest = match.group(1).replace("-", "_")
        return f"{ARG_ZH.get(dest, match.group(1))}不能为负数。"
    if message.startswith("Failed to read image:"): return "无法读取图片：" + message.split(":", 1)[1].strip()
    if message.startswith("Input image not found:"): return "找不到输入图片：" + message.split(":", 1)[1].strip()
    return f"操作失败：{message}"


def help_text(action: argparse.Action, language: str) -> str:
    option = action.option_strings[0]
    english = README_HELP_EN.get(option, action.help or "")
    if language == "en": return english
    return chinese_help(action)

DEFAULT_REQUIRED = {
    "latitude": 50.0,
    "center": "south",
    "range_latitude": 23.5,
    "diameter": 40.0,
}

# A row is visible when its predicate is true. Unlisted arguments are basic.
DEPENDENCIES = {
    "azimuth_width": lambda v: v("azimuth_lines") > 0,
    "sub_azimuth_lines": lambda v: v("azimuth_lines") > 0,
    "sub_azimuth_width": lambda v: v("azimuth_lines") > 0 and v("sub_azimuth_lines") > 1,
    "altitude_width": lambda v: v("altitude_lines") > 0,
    "sub_altitude_lines": lambda v: v("altitude_lines") > 0,
    "sub_altitude_width": lambda v: v("altitude_lines") > 0 and v("sub_altitude_lines") > 1,
    "twilight_width": lambda v: any(v(x) for x in ("civil_twilight", "nautical_twilight", "astronomical_twilight")),
    "twilight_style": lambda v: any(v(x) for x in ("civil_twilight", "nautical_twilight", "astronomical_twilight")),
    "astronomical_twilight_width": lambda v: any(v(x) for x in ("civil_twilight", "nautical_twilight", "astronomical_twilight")) and v("twilight_width") is None,
    "equator_tropics_width": lambda v: v("equator_tropics"),
    "ecliptic_width": lambda v: v("ecliptic"),
    "ecliptic_band_width": lambda v: v("ecliptic"),
    "ecliptic_angle_lines": lambda v: v("ecliptic"),
    "sub_ecliptic_angle_lines": lambda v: v("ecliptic") and v("ecliptic_angle_lines") > 0,
    "ecliptic_angle_width": lambda v: v("ecliptic") and v("ecliptic_angle_lines") > 0,
    "sub_ecliptic_angle_width": lambda v: v("ecliptic") and v("ecliptic_angle_lines") > 0 and v("sub_ecliptic_angle_lines") > 1,
    "ecliptic_rotation_direction": lambda v: v("ecliptic"),
    "date_ring": lambda v: v("ecliptic"),
    "date_ring_width": lambda v: v("ecliptic") and v("date_ring"),
    "date_ring_band_width": lambda v: v("ecliptic") and v("date_ring"),
    "date_ring_month_width": lambda v: v("ecliptic") and v("date_ring"),
    "date_ring_sub_interval": lambda v: v("ecliptic") and v("date_ring"),
    "date_ring_sub_width": lambda v: v("ecliptic") and v("date_ring") and v("date_ring_sub_interval") > 0,
    "date_ring_sub_sub_interval": lambda v: v("ecliptic") and v("date_ring"),
    "date_ring_sub_sub_width": lambda v: v("ecliptic") and v("date_ring") and v("date_ring_sub_sub_interval") > 0,
    "date_ring_month_labels": lambda v: v("ecliptic") and v("date_ring"),
    "date_ring_month_label_size": lambda v: v("ecliptic") and v("date_ring") and v("date_ring_month_labels"),
    "date_ring_month_label_width": lambda v: v("ecliptic") and v("date_ring") and v("date_ring_month_labels"),
    "date_ring_month_label_line_position": lambda v: v("ecliptic") and v("date_ring") and v("date_ring_month_labels"),
    "date_ring_month_label_arc_adjust": lambda v: v("ecliptic") and v("date_ring") and v("date_ring_month_labels"),
    "date_ring_month_label_letter_spacing": lambda v: v("ecliptic") and v("date_ring") and v("date_ring_month_labels"),
    "reverse_date_ring_month_label_orientation": lambda v: v("ecliptic") and v("date_ring") and v("date_ring_month_labels"),
    "rotate_date_ring_180": lambda v: v("ecliptic") and v("date_ring"),
    "date_ring_year": lambda v: v("ecliptic") and v("date_ring"),
    "unequal_hour_width": lambda v: v("day_unequal_hour_lines") or v("night_unequal_hour_lines"),
    "day_unequal_hour_labels": lambda v: v("day_unequal_hour_lines"),
    "night_unequal_hour_labels": lambda v: v("night_unequal_hour_lines"),
    "unequal_hour_label_style": lambda v: v("day_unequal_hour_labels") or v("night_unequal_hour_labels"),
    "unequal_hour_label_size": lambda v: v("day_unequal_hour_labels") or v("night_unequal_hour_labels"),
    "unequal_hour_label_width": lambda v: v("day_unequal_hour_labels") or v("night_unequal_hour_labels"),
    "unequal_hour_label_line_position": lambda v: v("day_unequal_hour_labels") or v("night_unequal_hour_labels"),
    "unequal_hour_label_arc_adjust": lambda v: v("day_unequal_hour_labels") or v("night_unequal_hour_labels"),
    "unequal_hour_label_letter_spacing": lambda v: v("day_unequal_hour_labels") or v("night_unequal_hour_labels"),
    "solar_motion_direction": lambda v: v("day_unequal_hour_lines") or v("night_unequal_hour_lines") or v("azimuth_labels") or v("ecliptic"),
    "azimuth_label_size": lambda v: v("azimuth_labels"),
    "azimuth_label_width": lambda v: v("azimuth_labels"),
    "azimuth_label_position": lambda v: v("azimuth_labels"),
    "azimuth_label_center_adjust": lambda v: v("azimuth_labels"),
    "azimuth_label_letter_spacing": lambda v: v("azimuth_labels"),
    "crosshair_width": lambda v: v("crosshair"),
    "crosshair_horizontal_width": lambda v: v("crosshair"),
    "crosshair_vertical_width": lambda v: v("crosshair"),
}


def tokenize_config(text: str) -> list[str]:
    """Parse README/PowerShell command text without executing it."""
    # A README can contain setup/help commands and several examples. Prefer the
    # first fenced, runnable drawing example containing all required arguments.
    blocks = re.findall(r"```(?:powershell|pwsh|text)?\s*(.*?)```", text, re.I | re.S)
    runnable = [
        block for block in blocks
        if "pixi run draw-" in block
        and all(option in block for option in ("--latitude", "--center", "--range-latitude", "--diameter"))
    ]
    if runnable:
        text = runnable[0]
    task_match = re.search(r"pixi\s+run\s+(draw-(?:azimuthal-equidistant|stereographic|star-chart|astrolabe-back|astrolabe-ruler))", text)
    task = task_match.group(1) if task_match else ""
    tokens = re.findall(r'"([^"\r\n]*)"|\'([^\'\r\n]*)\'|(--?[A-Za-z][\w-]*|[-+]?\d+(?:\.\d+)?(?:,[-+]?\d+(?:\.\d+)?)*|[A-Za-z][\w.-]*)', text)
    flat = [next(part for part in match if part) for match in tokens]
    start = next((i for i, token in enumerate(flat) if token.startswith("--")), len(flat))
    return ([task] if task else []) + flat[start:]


def tokenize_workspace_config(text: str) -> list[list[str]]:
    """Parse both commands emitted by a whole projection-workspace export."""
    if "# Astrolabe workspace:" not in text: return []
    starts = list(re.finditer(r"(?im)^\s*pixi\s+run\s+draw-(?:azimuthal-equidistant|stereographic|star-chart|astrolabe-back|astrolabe-ruler)\b", text))
    commands = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        tokens = tokenize_config(text[match.start():end])
        if tokens: commands.append(tokens)
    return commands


def readme_example_tokens(heading: str, task: str) -> list[str]:
    """Return args from a runnable command in a named README section."""
    try:
        text = Path(__file__).resolve().parent.parent.joinpath("README.md").read_text(encoding="utf-8")
    except OSError:
        return []
    match = re.search(rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^##\s|\Z)", text, re.MULTILINE | re.DOTALL)
    if not match: return []
    for block in re.findall(r"```(?:powershell|pwsh|text)?\s*(.*?)```", match.group(1), re.I | re.S):
        tokens = tokenize_config(block)
        if tokens and tokens[0] == task and "--latitude" in tokens:
            return tokens[1:]
    return []


ECLIPTIC_DEFAULT_DESTS = {
    "ecliptic", "ecliptic_width", "ecliptic_band_width", "ecliptic_angle_lines",
    "sub_ecliptic_angle_lines", "ecliptic_angle_width", "sub_ecliptic_angle_width",
    "ecliptic_rotation_direction", "date_ring", "date_ring_width", "date_ring_band_width",
    "date_ring_month_width", "date_ring_sub_width", "date_ring_sub_interval",
    "date_ring_sub_sub_width", "date_ring_sub_sub_interval", "date_ring_month_labels",
    "date_ring_month_label_size", "date_ring_month_label_width",
    "date_ring_month_label_line_position", "date_ring_month_label_arc_adjust",
    "date_ring_month_label_letter_spacing", "reverse_date_ring_month_label_orientation",
    "rotate_date_ring_180", "date_ring_year",
}


def powershell_config(task: str, arguments: list[str]) -> str:
    """Serialize arguments to the README-compatible PowerShell form."""
    def quote(value: str) -> str:
        return '"' + value.replace('`', '``').replace('"', '`"') + '"'
    lines = [f"pixi run {task} -- @("]
    for index, value in enumerate(arguments):
        suffix = "," if index + 1 < len(arguments) else ""
        lines.append("  " + quote(value) + suffix)
    lines.append(")")
    return "\n".join(lines) + "\n"


def qimage_from_bgr(image: np.ndarray) -> QImage:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format.Format_RGB888).copy()


class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event): event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event): event.ignore()


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event): event.ignore()


class ProjectionTab(QWidget):
    def __init__(self, task: str, projection: str, language, dpi=lambda: 300, mode: str = "combined"):
        super().__init__()
        self.task, self.projection = task, projection
        self.mode = mode
        self.language = language
        self.dpi = dpi
        self.parser = build_parser(projection)
        self.actions: dict[str, argparse.Action] = {}
        self.widgets: dict[str, QWidget] = {}
        self.rows: dict[str, tuple[QLabel, QWidget]] = {}
        self.main_svg: bytes | None = None
        self.ecliptic_svg: bytes | None = None
        self.save_path: Path | None = None

        form_host = QWidget(); self.form = QFormLayout(form_host)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setWidget(form_host)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for action in self.parser._actions:
            if not action.option_strings or action.dest in ("help", "output"):
                continue
            widget = self._make_widget(action)
            label = QLabel(action.option_strings[0])
            self.actions[action.dest] = action
            self.widgets[action.dest] = widget; self.rows[action.dest] = (label, widget)
            self.form.addRow(label, widget)
            self._connect(widget)
        self.update_button = QPushButton(); self.update_button.clicked.connect(self.update_preview)
        self.left_panel = QWidget(); ll = QVBoxLayout(self.left_panel); ll.addWidget(self.scroll); ll.addWidget(self.update_button)

        self.preview_tabs = QTabWidget()
        self.main_view = QSvgWidget(); self.main_view.setMinimumSize(420, 420)
        self.ecliptic_view = QSvgWidget(); self.ecliptic_view.setMinimumSize(420, 420)
        self.main_view.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.ecliptic_view.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.preview_tabs.addTab(self.main_view, "")
        self.preview_tabs.addTab(self.ecliptic_view, "")
        self.preview_tabs.setTabEnabled(self.preview_tabs.indexOf(self.ecliptic_view), False)
        self.status = QLabel(); self.status.setWordWrap(True)
        right = QWidget(); rl = QVBoxLayout(right)
        rl.addWidget(self.preview_tabs if mode == "combined" else self.ecliptic_view if mode == "ecliptic" else self.main_view)
        rl.addWidget(self.status)
        self.splitter = QSplitter(); self.splitter.addWidget(self.left_panel); self.splitter.addWidget(right); self.splitter.setStretchFactor(1, 1)
        layout = QVBoxLayout(self); layout.addWidget(self.splitter)
        self.apply_readme_defaults()
        if self.mode == "ecliptic": self.set_value("ecliptic", True)
        elif self.mode == "main": self.set_value("ecliptic", False)
        self.retranslate()
        self.refresh_visibility()

    def tr(self, key: str, **values) -> str:
        return UI[self.language()][key].format(**values)

    def retranslate(self):
        self.update_button.setText(self.tr("update"))
        self.preview_tabs.setTabText(self.preview_tabs.indexOf(self.main_view), self.tr("main"))
        index = self.preview_tabs.indexOf(self.ecliptic_view)
        self.preview_tabs.setTabText(index, self.tr("ecliptic"))
        for name, action in self.actions.items():
            option = action.option_strings[0]
            self.rows[name][0].setText(f"{ARG_ZH.get(name, option)}（{option}）" if self.language() == "zh" else option)
            tip = help_text(action, self.language())
            self.rows[name][0].setToolTip(tip); self.rows[name][1].setToolTip(tip)
            widget = self.rows[name][1]
            if isinstance(widget, QComboBox) and not isinstance(widget, QFontComboBox) and name != "sky_culture":
                for index in range(widget.count()):
                    value = str(widget.itemData(index))
                    translated = STAR_POSITION_ZH.get(value, value) if name.endswith("_position") else STAR_CHOICE_ZH.get(value, value)
                    widget.setItemText(index, translated if self.language() == "zh" else value)
            widget = self.rows[name][1]
            if isinstance(widget, QComboBox):
                for item_index in range(widget.count()):
                    data = widget.itemData(item_index)
                    if data is None and widget.property("hasAutomatic"):
                        text = self.tr("automatic")
                    else:
                        text = CHOICE_ZH.get(str(data), str(data)) if self.language() == "zh" else str(data)
                    widget.setItemText(item_index, text)
            elif isinstance(widget, QDoubleSpinBox) and widget.property("nullable"):
                widget.setSpecialValueText(self.tr("automatic"))
        if not self.main_svg: self.status.setText(self.tr("ready"))
        self.apply_responsive_layout(self.width())

    def apply_responsive_layout(self, available_width: int):
        """Adapt the form and preview to the current logical-pixel width."""
        if available_width <= 0: return
        compact = available_width < 1100
        if compact:
            left_width = max(300, min(500, int(available_width * 0.48)))
            self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
            preview_minimum = 220
            label_width = max(240, left_width - 30)
        else:
            widest = max((label.sizeHint().width() for label, _widget in self.rows.values()), default=250)
            left_width = min(max(widest + 285, 410), 760)
            self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
            preview_minimum = 420
            label_width = 16777215
        for label, _widget in self.rows.values():
            label.setWordWrap(compact); label.setMaximumWidth(label_width)
        self.left_panel.setMinimumWidth(left_width)
        self.main_view.setMinimumSize(preview_minimum, preview_minimum)
        self.ecliptic_view.setMinimumSize(preview_minimum, preview_minimum)
        self.splitter.setSizes([left_width, max(preview_minimum, available_width - left_width)])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.apply_responsive_layout(event.size().width())

    def _make_widget(self, action: argparse.Action) -> QWidget:
        default = action.default
        if default is None and action.dest in DEFAULT_REQUIRED: default = DEFAULT_REQUIRED[action.dest]
        if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction, argparse.BooleanOptionalAction)):
            w = QCheckBox(); w.setChecked(bool(default)); return w
        if action.choices:
            w = NoWheelComboBox()
            if default is None: w.addItem("", None); w.setProperty("hasAutomatic", True)
            for choice in action.choices: w.addItem(str(choice), choice)
            index = w.findData(default)
            if index >= 0: w.setCurrentIndex(index)
            return w
        if action.type is int:
            w = NoWheelSpinBox(); w.setRange(-1000000, 1000000); w.setValue(int(default or 0)); return w
        w = NoWheelDoubleSpinBox(); w.setDecimals(6); w.setRange(-1000000.0, 1000000.0); w.setSingleStep(0.1)
        w.setProperty("nullable", default is None)
        if default is None: w.setMinimum(-1000000.0); w.setValue(w.minimum())
        else: w.setValue(float(default))
        return w

    def _connect(self, widget: QWidget) -> None:
        signal = widget.toggled if isinstance(widget, QCheckBox) else widget.currentIndexChanged if isinstance(widget, QComboBox) else widget.valueChanged
        signal.connect(self.refresh_visibility)

    def apply_readme_defaults(self):
        heading = "Azimuthal Equidistant" if self.projection == AZIMUTHAL_EQUIDISTANT else "Stereographic"
        base_tokens = readme_example_tokens(heading, self.task)
        if base_tokens:
            parsed = parse_args(self.projection, base_tokens)
            for name in self.widgets: self.set_value(name, getattr(parsed, name))
        # The Ecliptic section is canonical for all ecliptic/date-ring controls.
        ecliptic_tokens = readme_example_tokens("Ecliptic", "draw-stereographic")
        if ecliptic_tokens:
            parsed = parse_args(STEREOGRAPHIC, ecliptic_tokens)
            explicit_options = {token for token in ecliptic_tokens if token.startswith("--")}
            for action in build_parser(STEREOGRAPHIC)._actions:
                if action.dest in ECLIPTIC_DEFAULT_DESTS and any(option in explicit_options for option in action.option_strings):
                    self.set_value(action.dest, getattr(parsed, action.dest))

    def value(self, name: str):
        w = self.widgets[name]
        if isinstance(w, QCheckBox): return w.isChecked()
        if isinstance(w, QComboBox): return w.currentData()
        if isinstance(w, QDoubleSpinBox) and w.property("nullable") and w.value() == w.minimum(): return None
        return w.value()

    def set_value(self, name: str, value) -> None:
        w = self.widgets[name]
        if isinstance(w, QCheckBox): w.setChecked(bool(value))
        elif isinstance(w, QComboBox):
            i = w.findData(value)
            if i >= 0: w.setCurrentIndex(i)
        elif value is None and w.property("nullable"): w.setValue(w.minimum())
        else: w.setValue(value)

    def refresh_visibility(self, *_):
        ecliptic_common = {"latitude", "center", "range_latitude", "diameter", "boundary_width", "rotate_180", "solar_motion_direction"}
        for name, row in self.rows.items():
            visible = DEPENDENCIES.get(name, lambda _v: True)(self.value)
            if self.mode == "main" and name in ECLIPTIC_DEFAULT_DESTS: visible = False
            elif self.mode == "ecliptic": visible = name in ECLIPTIC_DEFAULT_DESTS or name in ecliptic_common
            if self.mode == "ecliptic" and name == "ecliptic": visible = False
            if row[1].property("workspaceHidden"): visible = False
            row[0].setVisible(visible); row[1].setVisible(visible)

    def namespace(self) -> argparse.Namespace:
        values = {name: self.value(name) for name in self.widgets}
        # A hidden child switch must not keep its feature active when its parent is off.
        for name, (_label, widget) in self.rows.items():
            if widget.isHidden() and isinstance(widget, QCheckBox): values[name] = False
        args = argparse.Namespace(**values)
        if self.mode == "ecliptic": args.ecliptic = True
        elif self.mode == "main": args.ecliptic = False
        args.output = Path("preview.svg"); args.projection = self.projection
        return args

    def update_preview(self):
        if self.mode in ("main", "ecliptic"):
            args = self.namespace(); is_ecliptic = self.mode == "ecliptic"
            try: result = svg_bytes(args, ecliptic=True) if is_ecliptic else svg_bytes(args)
            except Exception as exc:
                key = "ecliptic_failed" if is_ecliptic else "main_failed"
                self.status.setText(self.tr(key, value=localized_error(exc, self.language()))); return
            if is_ecliptic:
                self.ecliptic_svg = result; self.ecliptic_view.load(QByteArray(result)); self.ecliptic_view.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
                self.status.setText(self.tr("ecliptic_updated"))
            else:
                self.main_svg = result; self.main_view.load(QByteArray(result)); self.main_view.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
                self.status.setText(self.tr("main_updated"))
            return
        current_view = self.preview_tabs.currentWidget()
        args = self.namespace()
        messages: list[str] = []
        try:
            main = svg_bytes(args)
        except Exception as exc:
            messages.append(self.tr("main_failed", value=localized_error(exc, self.language())))
        else:
            self.main_svg = main
            self.main_view.load(QByteArray(main))
            self.main_view.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
            messages.append(self.tr("main_updated"))
        if args.ecliptic:
            try:
                companion = svg_bytes(args, ecliptic=True)
            except Exception as exc:
                messages.append(self.tr("ecliptic_failed", value=localized_error(exc, self.language())))
            else:
                self.ecliptic_svg = companion
                self.ecliptic_view.load(QByteArray(companion))
                self.ecliptic_view.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
                self.preview_tabs.setTabEnabled(self.preview_tabs.indexOf(self.ecliptic_view), True)
                messages.append(self.tr("ecliptic_updated"))
        else:
            self.ecliptic_svg = None
            self.preview_tabs.setTabEnabled(self.preview_tabs.indexOf(self.ecliptic_view), False)
        current_index = self.preview_tabs.indexOf(current_view)
        if current_index >= 0 and self.preview_tabs.isTabEnabled(current_index):
            self.preview_tabs.setCurrentWidget(current_view)
        else:
            self.preview_tabs.setCurrentWidget(self.main_view)
        self.status.setText(" ".join(messages))

    def import_args(self, argv: list[str]):
        parsed = parse_args(self.projection, argv)
        for name in self.widgets: self.set_value(name, getattr(parsed, name))
        self.refresh_visibility(); self.status.setText(self.tr("imported"))

    def export_args(self) -> list[str]:
        result: list[str] = []
        for action in self.parser._actions:
            name = action.dest
            if name not in self.widgets or name == "output": continue
            widget = self.widgets[name]
            if widget.isHidden(): continue
            value = self.value(name)
            if isinstance(widget, QCheckBox):
                if value: result.append(action.option_strings[0])
                continue
            if value is None: continue
            result.extend((action.option_strings[0], str(value).lower() if isinstance(value, bool) else str(value)))
        if self.mode == "ecliptic" and "--ecliptic" not in result: result.append("--ecliptic")
        return result

    def export_config_text(self) -> str:
        return powershell_config(self.task, self.export_args())

    @staticmethod
    def _write_svg(svg: bytes, path: Path):
        path.write_bytes(svg)

    def _write_raster(self, svg: bytes, path: Path):
        renderer = QSvgRenderer(QByteArray(svg)); size = renderer.defaultSize()
        # Read the physical millimetre size and render it at the configured DPI.
        dpi = self.dpi()
        match = re.search(rb'<svg[^>]*width="([\d.]+)mm"[^>]*height="([\d.]+)mm"', svg)
        if match:
            width = max(1, round(float(match.group(1)) * dpi / 25.4))
            height = max(1, round(float(match.group(2)) * dpi / 25.4))
        else:
            width, height = max(1, size.width()), max(1, size.height())
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.white if path.suffix.lower() in (".jpg", ".jpeg") else Qt.GlobalColor.transparent)
        painter = QPainter(image); renderer.render(painter); painter.end()
        if not image.save(str(path), quality=95): raise OSError(str(path))

    def save(self, path: Path):
        selected_svg = self.ecliptic_svg if self.mode == "ecliptic" else self.main_svg
        if not selected_svg: raise ValueError(self.tr("need_preview"))
        path.parent.mkdir(parents=True, exist_ok=True)
        writer = self._write_svg if path.suffix.lower() == ".svg" else self._write_raster
        writer(selected_svg, path)
        if self.mode == "combined" and self.ecliptic_svg:
            companion = path.with_name(f"{path.stem}_ecliptic{path.suffix}")
            writer(self.ecliptic_svg, companion)
        self.save_path = path; self.status.setText(self.tr("saved", value=path))


class StarChartTab(QWidget):
    """Polar star-chart editor backed by the same parser and renderer as the CLI."""
    task = "draw-star-chart"

    def __init__(self, language, dpi=lambda: 300, cache: Path | None = None, fixed_projection: str | None = None):
        super().__init__()
        self.language, self.dpi = language, dpi
        self.fixed_projection = fixed_projection
        self.parser = build_star_parser()
        self.cache = Path(cache or default_data_cache())
        self.main_svg: bytes | None = None
        self.save_path: Path | None = None
        self.actions: dict[str, argparse.Action] = {}
        self.widgets: dict[str, QWidget] = {}
        self.rows: dict[str, tuple[QLabel, QWidget]] = {}

        form_host = QWidget(); self.form = QFormLayout(form_host)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setWidget(form_host)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for action in self.parser._actions:
            if not action.option_strings or action.dest in ("help", "output", "data_cache", "star_diameters"):
                continue
            self.actions[action.dest] = action
            label = QLabel()
            widget = self._make_widget(action)
            self._connect(action.dest, widget)
            self.widgets[action.dest] = widget; self.rows[action.dest] = (label, widget)
            self.form.addRow(label, widget)

        self.update_button = QPushButton(); self.update_button.clicked.connect(self.update_preview)
        self.left_panel = QWidget(); left = QVBoxLayout(self.left_panel); left.addWidget(self.scroll); left.addWidget(self.update_button)
        self.preview = QSvgWidget(); self.preview.setMinimumSize(420, 420)
        self.preview.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.status = QLabel(); self.status.setWordWrap(True)
        right = QWidget(); right_layout = QVBoxLayout(right); right_layout.addWidget(self.preview); right_layout.addWidget(self.status)
        self.splitter = QSplitter(); self.splitter.addWidget(self.left_panel); self.splitter.addWidget(right); self.splitter.setStretchFactor(1, 1)
        layout = QVBoxLayout(self); layout.addWidget(self.splitter)
        if self.fixed_projection: self.set_value("projection", self.fixed_projection)
        self.refresh_cultures(); self.retranslate(); self.refresh_visibility()

    def tr(self, key, **values): return UI[self.language()][key].format(**values)

    def _make_widget(self, action: argparse.Action) -> QWidget:
        default = action.default
        if isinstance(action, argparse.BooleanOptionalAction):
            widget = QCheckBox(); widget.setChecked(bool(default)); return widget
        if action.dest.endswith("_font"):
            widget = QFontComboBox(); widget.setCurrentFont(widget.font()); return widget
        if action.choices:
            widget = NoWheelComboBox()
            for choice in action.choices: widget.addItem(str(choice), choice)
            index = widget.findData(default)
            if index >= 0: widget.setCurrentIndex(index)
            return widget
        if action.dest == "sky_culture": return NoWheelComboBox()
        if action.type is int:
            widget = NoWheelSpinBox(); widget.setRange(1, 10000); widget.setValue(int(default)); return widget
        widget = NoWheelDoubleSpinBox(); widget.setDecimals(4); widget.setRange(-100000.0, 100000.0); widget.setSingleStep(0.1); widget.setValue(float(default)); return widget

    def _connect(self, name: str, widget: QWidget):
        signal = widget.toggled if isinstance(widget, QCheckBox) else widget.currentIndexChanged if isinstance(widget, QComboBox) else widget.valueChanged
        signal.connect(self.refresh_visibility)

    def value(self, name: str):
        widget = self.widgets[name]
        if isinstance(widget, QCheckBox): return widget.isChecked()
        if isinstance(widget, QFontComboBox): return widget.currentFont().family()
        if isinstance(widget, QComboBox): return widget.currentData()
        return widget.value()

    def set_value(self, name: str, value):
        widget = self.widgets[name]
        if isinstance(widget, QCheckBox): widget.setChecked(bool(value))
        elif isinstance(widget, QFontComboBox): widget.setCurrentFont(QFont(str(value)))
        elif isinstance(widget, QComboBox):
            index = widget.findData(value)
            if index >= 0: widget.setCurrentIndex(index)
        else: widget.setValue(value)

    def namespace(self):
        args = self.parser.parse_args([])
        for name in self.widgets: setattr(args, name, self.value(name))
        args.star_diameters = None
        if self.fixed_projection: args.projection = self.fixed_projection
        args.data_cache = self.cache; args.output = Path("preview.svg")
        return args

    def refresh_cultures(self):
        widget = self.widgets.get("sky_culture")
        if not isinstance(widget, QComboBox): return
        selected = widget.currentData(); widget.blockSignals(True); widget.clear()
        cultures = available_cultures(self.cache)
        if not cultures: cultures = [("modern", "Modern")]
        for identifier, name in cultures: widget.addItem(name, identifier)
        index = widget.findData(selected or "modern")
        widget.setCurrentIndex(max(0, index)); widget.blockSignals(False)

    def refresh_visibility(self, *_):
        lines = self.value("constellation_lines")
        stars = self.value("show_star_names")
        figures = self.value("show_constellation_names")
        dependencies = {
            "milky_way_width": self.value("milky_way"),
            "equator_width": self.value("equator"), "ecliptic_width": self.value("ecliptic"),
            "sky_culture": lines or stars or figures, "constellation_width": lines,
            "star_name_language": stars, "star_name_font": stars, "star_name_size": stars,
            "star_name_position": stars, "star_name_radial_offset": stars, "star_name_tangential_offset": stars,
            "constellation_name_language": figures, "constellation_name_font": figures,
            "constellation_name_size": figures, "constellation_name_position": figures,
            "constellation_name_radial_offset": figures, "constellation_name_tangential_offset": figures,
            "avoid_label_overlap": stars or figures,
        }
        for name, visible in dependencies.items():
            self.rows[name][0].setVisible(visible); self.rows[name][1].setVisible(visible)
        if self.fixed_projection:
            self.rows["projection"][0].setVisible(False); self.rows["projection"][1].setVisible(False)

    def retranslate(self):
        self.update_button.setText(self.tr("update"))
        for name, action in self.actions.items():
            option = action.option_strings[0]
            label = STAR_ARG_ZH.get(name, option) if self.language() == "zh" else option
            self.rows[name][0].setText(f"{label}（{option}）" if self.language() == "zh" else option)
            english = action.help or option
            if self.language() == "zh":
                tip = STAR_HELP_ZH.get(name, f"设置{STAR_ARG_ZH.get(name, option)}；数值将在更新预览时校验。")
            else: tip = english
            self.rows[name][0].setToolTip(tip); self.rows[name][1].setToolTip(tip)
            widget = self.rows[name][1]
            if isinstance(widget, QComboBox) and not isinstance(widget, QFontComboBox) and name != "sky_culture":
                for index in range(widget.count()):
                    value = str(widget.itemData(index))
                    if self.language() == "zh":
                        text = STAR_POSITION_ZH.get(value, value) if name.endswith("_position") else STAR_CHOICE_ZH.get(value, value)
                    else:
                        text = STAR_CHOICE_EN.get(value, value)
                    widget.setItemText(index, text)
        if self.main_svg is None: self.status.setText(self.tr("ready"))

    def update_preview(self):
        try:
            svg, stats = render_star_chart(self.namespace())
        except Exception as exc:
            self.status.setText(self.tr("error", value=localized_error(exc, self.language()))); return
        self.main_svg = svg; self.preview.load(QByteArray(svg)); self.preview.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.status.setText(self.tr("star_summary", stars=stats.stars, segments=stats.segments,
            labels=stats.star_labels + stats.figure_labels, hidden=stats.hidden_labels,
            missing=stats.missing_identifiers, degraded=stats.degraded_motion))

    def import_args(self, argv: list[str]):
        args = self.parser.parse_args(argv)
        if self.fixed_projection: args.projection = self.fixed_projection
        self.cache = Path(args.data_cache); self.refresh_cultures()
        if args.star_diameters:
            legacy = [float(item.strip()) for item in args.star_diameters.split(",") if item.strip()]
            if len(legacy) != args.magnitude_levels: raise ValueError("star-diameters count must equal magnitude-levels")
            args.star_diameter_max, args.star_diameter_min = legacy[0], legacy[-1]
        for name in self.widgets:
            self.set_value(name, getattr(args, name))
        self.refresh_visibility(); self.status.setText(self.tr("imported"))

    def export_args(self) -> list[str]:
        result = []
        for action in self.parser._actions:
            name = action.dest
            if name not in self.widgets or name in ("data_cache", "output"): continue
            value = self.value(name)
            if isinstance(action, argparse.BooleanOptionalAction):
                result.append(action.option_strings[0] if value else next(option for option in action.option_strings if option.startswith("--no-")))
            else: result.extend((action.option_strings[0], str(value)))
        result.extend(("--data-cache", str(self.cache)))
        return result

    def export_config_text(self): return powershell_config(self.task, self.export_args())

    def _write_raster(self, svg: bytes, path: Path):
        renderer = QSvgRenderer(QByteArray(svg)); match = re.search(rb'<svg[^>]*width="([\d.]+)mm"[^>]*height="([\d.]+)mm"', svg)
        if match:
            width = max(1, round(float(match.group(1)) * self.dpi() / 25.4)); height = max(1, round(float(match.group(2)) * self.dpi() / 25.4))
        else: width = max(1, renderer.defaultSize().width()); height = max(1, renderer.defaultSize().height())
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.white if path.suffix.lower() in (".jpg", ".jpeg") else Qt.GlobalColor.transparent)
        painter = QPainter(image); renderer.render(painter); painter.end()
        if not image.save(str(path), quality=95): raise OSError(str(path))

    def save(self, path: Path):
        if not self.main_svg: raise ValueError(self.tr("need_preview"))
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".svg": path.write_bytes(self.main_svg)
        elif path.suffix.lower() in (".png", ".jpg", ".jpeg"): self._write_raster(self.main_svg, path)
        else: raise ValueError(self.tr("unsupported", value=path.suffix))
        self.save_path = path; self.status.setText(self.tr("saved", value=path))

    def apply_responsive_layout(self, available_width: int):
        compact = available_width < 820
        widest = max((label.sizeHint().width() for label, _ in self.rows.values()), default=260)
        left_width = min(max(300 if compact else widest + 285, int(available_width * (.48 if compact else .40))), 760)
        self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows if compact else QFormLayout.RowWrapPolicy.DontWrapRows)
        self.left_panel.setMinimumWidth(left_width); preview_minimum = 220 if compact else 420
        self.preview.setMinimumSize(preview_minimum, preview_minimum); self.splitter.setSizes([left_width, max(preview_minimum, available_width - left_width)])

    def resizeEvent(self, event):
        super().resizeEvent(event); self.apply_responsive_layout(event.size().width())


BACK_LABELS = {
    'calendar_mode': '日期圈模式', 'rotation_direction': '黄经递增方向',
    'zodiac_zero': '白羊宫零点角度', 'angle_band_width': '角度及黄道圈宽度（mm）',
    'date_band_width': '日期圈宽度（mm）', 'ring_gap': '圈间距（mm）',
    'line_width': '主刻度线宽（mm）', 'minor_width': '次刻度线宽（mm）',
    'label_size': '刻度字号（mm）', 'upper_layout': '上半盘布局',
    'sincos_scale': 'sin/cos 倍数（内半径恒为60单位）', 'shadow_divisions': '影方每边单位数',
    'sincos_zero_radius': 'sin/cos 零值半径／内圆半径',
    'shadow_band_width': '影方刻度带宽（mm）', 'eot': '显示时差曲线 EOT',
    'shadow_label_band_width': '影方文字带宽（mm）', 'shadow_numbers': '显示影方数字',
    'eot_min_radius': 'EOT 最慢时半径／内圆半径', 'eot_max_radius': 'EOT 最快时半径／内圆半径',
    'eot_width': 'EOT 曲线线宽（mm）',
}
BACK_LABEL_GROUPS = {'angle':'角度数字', 'zodiac_degree':'黄道度数', 'zodiac_name':'黄道名称',
                     'day':'日期数字', 'month':'月份名称', 'hour':'小时数字',
                     'sincos':'sin/cos 名称', 'shadow_number':'影方数字', 'shadow_name':'影方名称'}
for _category, _title in BACK_LABEL_GROUPS.items():
    for _suffix, _label in {'font':'字体', 'size':'字号（mm，0=默认）', 'radial_offset':'径向偏移（mm，外正内负）',
                           'angular_offset':'圆周偏移（°，逆时针为正）', 'orientation':'文字朝向',
                           'rotation':'文字附加旋转（°）'}.items():
        BACK_LABELS[f'{_category}_label_{_suffix}'] = f'{_title}：{_label}'
BACK_CHOICES = {'concentric': '同心（按太阳黄经）', 'eccentric': '偏心（日期等距，近似拟合）',
                'hours': '完整白天12小时', 'hours-sincos': '半侧小时 + sin/cos',
                'clockwise': '顺时针', 'counterclockwise': '逆时针', 'both':'50和60同时显示',
                'auto':'自动保持可读', 'tangent':'沿圆周切向', 'radial':'沿径向', 'horizontal':'水平'}
UI['en'].update(back='Back', back_updated='Back updated; calendar maximum error: {error:.4f}°.', back_failed='Back preview failed: {value}')
UI['zh'].update(back='背面', back_updated='背面已更新；日期最大对齐误差：{error:.4f}°。', back_failed='背面预览失败：{value}')


class BackControls(QWidget):
    """Parser-backed controls; shared values are injected by the workspace."""
    _make_widget = StarChartTab._make_widget
    value = StarChartTab.value
    set_value = StarChartTab.set_value

    def __init__(self, language):
        super().__init__(); self.language = language; self.parser = build_back_parser()
        self.rows = {}; self.widgets = {}; self.actions = {}; self.main_svg = None
        self.form = QFormLayout(self); self.preview = QSvgWidget()
        self.label_category = NoWheelComboBox()
        for category in LABEL_GROUPS:self.label_category.addItem(category,category)
        self.rows['label_category']=(QLabel(),self.label_category)
        self.form.addRow(*self.rows['label_category'])
        for action in self.parser._actions:
            if action.dest in ('help', 'output', 'projection', 'diameter', 'boundary_width', 'epoch_year', 'eot_band_width'): continue
            label = QLabel(); widget = self._make_widget(action)
            if isinstance(widget,QFontComboBox):widget.setCurrentFont(QFont(action.default))
            self.actions[action.dest] = action; self.widgets[action.dest] = widget
            self.rows[action.dest] = (label, widget); self.form.addRow(label, widget)
        self.widgets['shadow_divisions'].setRange(1, 100)
        for name in ('eot_min_radius', 'eot_max_radius'):
            self.widgets[name].setRange(0, 1)
            self.widgets[name].setSingleStep(0.05)
        self.widgets['sincos_zero_radius'].setRange(0,.9999)
        self.widgets['sincos_zero_radius'].setSingleStep(.05)
        self.widgets['eot'].toggled.connect(self.refresh_visibility)
        self.widgets['upper_layout'].currentIndexChanged.connect(self.refresh_visibility)
        self.label_category.currentIndexChanged.connect(self.refresh_visibility)
        self.widgets['shadow_numbers'].toggled.connect(self.refresh_visibility)
        self.retranslate(); self.refresh_visibility()

    def refresh_visibility(self, *_):
        for name,row in self.rows.items():
            for category in LABEL_GROUPS:
                if name.startswith(category+'_label_'):
                    for widget in row:widget.setVisible(self.label_category.currentData()==category)
        for name, visible in {'eot_min_radius':self.value('eot'), 'eot_max_radius':self.value('eot'), 'eot_width':self.value('eot'),
                              'sincos_scale':self.value('upper_layout') == 'hours-sincos',
                              'sincos_zero_radius':self.value('upper_layout') == 'hours-sincos'}.items():
            for widget in self.rows[name]: widget.setVisible(visible)

    def retranslate(self):
        self.rows['label_category'][0].setText('文字设置类别' if self.language()=='zh' else 'Text settings category')
        for i,category in enumerate(LABEL_GROUPS):
            self.label_category.setItemText(i,BACK_LABEL_GROUPS[category] if self.language()=='zh' else category.replace('_',' ').title())
        for name, action in self.actions.items():
            label, widget = self.rows[name]
            label.setText(BACK_LABELS[name] if self.language() == 'zh' else action.option_strings[0])
            label.setToolTip(action.help or ''); widget.setToolTip(action.help or '')
            if name in ('eot_min_radius', 'eot_max_radius'):
                tip = ('最慢（全年最小时差）对应内圆半径的比例，默认0.95。0.5表示内圆半径的一半。' if name == 'eot_min_radius' else '最快（全年最大时差）对应内圆半径的比例，默认0.05，与参考图方向一致。0.5表示内圆半径的一半。') if self.language() == 'zh' else action.help
                label.setToolTip(tip); widget.setToolTip(tip)
            if isinstance(widget, QComboBox) and not isinstance(widget, QFontComboBox):
                for i in range(widget.count()):
                    value = str(widget.itemData(i))
                    widget.setItemText(i, BACK_CHOICES.get(value, value) if self.language() == 'zh' else value)

    def namespace(self):
        args = self.parser.parse_args([])
        for name in self.widgets: setattr(args, name, self.value(name))
        return args

    def import_args(self, argv):
        args = self.parser.parse_args(argv)
        validate_back(args)
        for name in self.widgets: self.set_value(name, getattr(args, name))
        self.refresh_visibility()

    def export_args(self, args):
        result = []
        for action in self.parser._actions:
            if action.dest in ('help', 'output', 'eot_band_width'): continue
            value = getattr(args, action.dest)
            if isinstance(action, argparse.BooleanOptionalAction):
                result.append(action.option_strings[0 if value else 1])
            else: result.extend((action.option_strings[0], str(value)))
        return result


RULER_LABELS = {
    'ruler_symmetry':'标尺对称方式', 'ruler_length_ratio':'标尺长度／全局外圆直径',
    'ruler_arm_width':'尺臂读数侧宽度（mm）', 'ruler_hub_radius':'中心圆台半径（mm）',
    'ruler_hole_radius':'轴孔半径（mm，0隐藏）', 'ruler_tip_length':'曲线尖端长度（mm）',
    'ruler_outline_width':'标尺外形线宽（mm）', 'ruler_tick_width':'刻度线宽（mm）',
    'ruler_tick_length':'主刻度长度（mm）', 'ruler_eot_step':'EOT 刻度间隔（分钟）',
    'ruler_sin_font':'0–60 数字字体', 'ruler_sin_size':'0–60 数字字号（mm）',
    'ruler_sin_label_offset':'0–60 数字离读数边偏移（mm）',
    'ruler_eot_font':'EOT 数字字体', 'ruler_eot_size':'EOT 数字字号（mm）',
    'ruler_eot_label_offset':'EOT 数字离读数边偏移（mm）',
}
UI['en'].update(ruler='Ruler',ruler_updated='Ruler updated; omitted ticks outside usable arm / in pivot hole: {count}.',ruler_failed='Ruler preview failed: {value}')
UI['zh'].update(ruler='标尺',ruler_updated='标尺已更新；超出可用尺身／落入轴孔而省略的刻度：{count}。',ruler_failed='标尺预览失败：{value}')


class RulerControls(QWidget):
    _make_widget=StarChartTab._make_widget
    value=StarChartTab.value
    set_value=StarChartTab.set_value
    export_args=BackControls.export_args

    def __init__(self,language):
        super().__init__();self.language=language;self.parser=build_ruler_parser()
        self.rows={};self.widgets={};self.actions={};self.main_svg=None
        self.form=QFormLayout(self);self.preview=QSvgWidget()
        for action in self.parser._actions:
            if not action.dest.startswith('ruler_'):continue
            widget=self._make_widget(action);label=QLabel()
            if isinstance(widget,QFontComboBox):widget.setCurrentFont(QFont(action.default))
            self.widgets[action.dest]=widget;self.rows[action.dest]=(label,widget);self.actions[action.dest]=action
            self.form.addRow(label,widget)
        self.retranslate()

    def namespace(self,back):
        args=self.parser.parse_args([])
        for name,value in vars(back).items():setattr(args,name,value)
        for name in self.widgets:setattr(args,name,self.value(name))
        return args

    def import_args(self,argv):
        args=self.parser.parse_args(argv);validate_ruler(args)
        for name in self.widgets:self.set_value(name,getattr(args,name))

    def retranslate(self):
        for name,action in self.actions.items():
            label,widget=self.rows[name];label.setText(RULER_LABELS[name] if self.language()=='zh' else action.option_strings[0])
            label.setToolTip(action.help);widget.setToolTip(action.help)
            if name=='ruler_symmetry':
                for i in range(widget.count()):
                    value=widget.itemData(i)
                    widget.setItemText(i,({'rotational':'旋转对称（两臂错侧）','axial':'轴对称（刻度在直径同侧）'}[value] if self.language()=='zh' else value))


class ProjectionWorkspace(QWidget):
    """Shared configuration with Main, Ecliptic, and Star Chart preview pages."""
    STAR_SHARED_PARAMETERS = {
        "center": "center",
        "range_declination": "range_latitude",
        "diameter": "diameter",
        "boundary_width": "boundary_width",
    }

    def __init__(self, task: str, projection: str, language, dpi=lambda: 300, cache: Path | None = None):
        super().__init__(); self.task = task; self.projection = projection; self.language = language; self.dpi = dpi
        self.projection_controls = ProjectionTab(task, projection, language, dpi)
        self.star_chart = StarChartTab(language, dpi, cache=cache, fixed_projection=projection)
        self.back = BackControls(language)
        self.ruler = RulerControls(language)
        self.projection_controls.set_value("ecliptic", True)
        self.projection_controls.rows["ecliptic"][1].setProperty("workspaceHidden", True)
        self.projection_controls.rows["ecliptic"][0].setVisible(False); self.projection_controls.rows["ecliptic"][1].setVisible(False)

        parameter_host = QWidget(); self.parameter_layout = QVBoxLayout(parameter_host)
        self.sections: list[QGroupBox] = []
        self.section_forms: list[QFormLayout] = []
        self.main_section, main_form = self._section()
        self.ecliptic_section, ecliptic_form = self._section()
        self.star_section, star_form = self._section()
        self.back_section, back_form = self._section()
        self.ruler_section, ruler_form = self._section()
        self.section_forms.extend((main_form, ecliptic_form, star_form, back_form, ruler_form))
        self.sections.extend((self.main_section, self.ecliptic_section, self.star_section, self.back_section, self.ruler_section))
        self.ruler_shared_note=QLabel();self.ruler_shared_note.setWordWrap(True);ruler_form.addRow(self.ruler_shared_note)
        for label,widget in self.ruler.rows.values():
            self.ruler.form.takeRow(label);ruler_form.addRow(label,widget)
        self.back_shared_note = QLabel(); self.back_shared_note.setWordWrap(True); back_form.addRow(self.back_shared_note)
        for label, widget in self.back.rows.values():
            self.back.form.takeRow(label); back_form.addRow(label, widget)

        for name, (label, widget) in self.projection_controls.rows.items():
            self.projection_controls.form.takeRow(label)
            target = ecliptic_form if name in ECLIPTIC_DEFAULT_DESTS else main_form
            target.addRow(label, widget)
        for name, (label, widget) in self.star_chart.rows.items():
            self.star_chart.form.takeRow(label); star_form.addRow(label, widget)
        self.projection_controls.rows["ecliptic"][0].setVisible(False); self.projection_controls.rows["ecliptic"][1].setVisible(False)
        for name in (*self.STAR_SHARED_PARAMETERS, "projection"):
            label, widget = self.star_chart.rows[name]
            widget.setProperty("workspaceHidden", True); label.setVisible(False); widget.setVisible(False)
        for name in ("rotation", "rotation_direction"):
            label, widget = self.star_chart.rows[name]
            widget.setProperty("workspaceHidden", True); label.setVisible(False); widget.setVisible(False)
        self._sync_shared_star_parameters()
        self.parameter_layout.addStretch(1)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setWidget(parameter_host)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.update_button = QPushButton(); self.update_button.clicked.connect(self.update_preview)
        left = QWidget(); left_layout = QVBoxLayout(left); left_layout.addWidget(self.scroll); left_layout.addWidget(self.update_button)
        self.left_panel = left

        self.pages = QTabWidget(); self.page_widgets = []
        preview_views = (self.projection_controls.main_view, self.projection_controls.ecliptic_view, self.star_chart.preview, self.back.preview, self.ruler.preview)
        # Main and Ecliptic were created as pages of ProjectionTab's legacy
        # preview QTabWidget.  Merely adding them to another layout reparents
        # them, but does not clear the explicit hidden state maintained by the
        # old tab widget.  Remove them first, then explicitly show every view
        # after attaching it to its workspace page.
        legacy_tabs = self.projection_controls.preview_tabs
        for view in preview_views[:2]:
            index = legacy_tabs.indexOf(view)
            if index >= 0: legacy_tabs.removeTab(index)
            view.setParent(None)
        for view in preview_views:
            page = QWidget(); page_layout = QVBoxLayout(page)
            view.setParent(page); page_layout.addWidget(view); view.show()
            self.pages.addTab(page, ""); self.page_widgets.append(page)
        self.pages.currentChanged.connect(self._page_changed)
        self.status = QLabel(); self.status.setWordWrap(True)
        right = QWidget(); right_layout = QVBoxLayout(right); right_layout.addWidget(self.pages); right_layout.addWidget(self.status)
        self.splitter = QSplitter(); self.splitter.addWidget(left); self.splitter.addWidget(right); self.splitter.setStretchFactor(1, 1)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.addWidget(self.splitter)
        self._save_paths: dict[int, Path] = {}
        self.retranslate(); self.apply_responsive_layout(self.width())

    def _section(self):
        box = QGroupBox(); form = QFormLayout(box); form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop); form.setVerticalSpacing(10)
        self.parameter_layout.addWidget(box); return box, form

    def current_index(self): return self.pages.currentIndex()

    def select_index(self, index: int): self.pages.setCurrentIndex(index)

    def _page_changed(self, index: int):
        if 0 <= index < len(self.sections): QTimer.singleShot(0, lambda: self.scroll.ensureWidgetVisible(self.sections[index], 0, 8))

    @property
    def save_path(self): return self._save_paths.get(self.current_index())

    @property
    def main_svg(self):
        if self.current_index() == 0: return self.projection_controls.main_svg
        if self.current_index() == 1: return self.projection_controls.ecliptic_svg
        if self.current_index() == 3: return self.back.main_svg
        if self.current_index() == 4: return self.ruler.main_svg
        return self.star_chart.main_svg

    def _sync_shared_star_parameters(self):
        """Make shared star-chart geometry follow the workspace main drawing."""
        for star_name, projection_name in self.STAR_SHARED_PARAMETERS.items():
            self.star_chart.set_value(star_name, self.projection_controls.value(projection_name))
        self.star_chart.set_value("projection", self.projection)
        direction = (self.projection_controls.value("ecliptic_rotation_direction") or
                     self.projection_controls.value("solar_motion_direction"))
        self.star_chart.set_value("rotation", 0.0)
        self.star_chart.set_value("rotation_direction", direction)

    def star_namespace(self):
        self._sync_shared_star_parameters()
        return self.star_chart.namespace()

    def back_namespace(self):
        args = self.back.namespace()
        args.projection = self.projection
        args.diameter = self.projection_controls.value('diameter')
        args.boundary_width = self.projection_controls.value('boundary_width')
        args.epoch_year = self.star_chart.value('epoch_year')
        return args

    def import_back(self, argv):
        args = build_back_parser().parse_args(argv)
        if args.projection != self.projection: raise ValueError('Back projection does not match workspace.')
        self.back.import_args(argv)

    def ruler_namespace(self):return self.ruler.namespace(self.back_namespace())

    def import_ruler(self,argv):
        args=build_ruler_parser().parse_args(argv)
        if args.projection!=self.projection:raise ValueError('Ruler projection does not match workspace.')
        self.ruler.import_args(argv)

    def update_preview(self):
        # One click refreshes the entire current projection workspace. Each
        # preview is committed independently so a failure preserves its last
        # valid image without preventing the other previews from updating.
        messages = []; args = self.projection_controls.namespace(); args.ecliptic = True
        for is_ecliptic in (False, True):
            try: svg = svg_bytes(args, ecliptic=True) if is_ecliptic else svg_bytes(args)
            except Exception as exc:
                key = "ecliptic_failed" if is_ecliptic else "main_failed"
                messages.append(UI[self.language()][key].format(value=localized_error(exc, self.language())))
            else:
                if is_ecliptic:
                    self.projection_controls.ecliptic_svg = svg; view = self.projection_controls.ecliptic_view; key = "ecliptic_updated"
                else:
                    self.projection_controls.main_svg = svg; view = self.projection_controls.main_view; key = "main_updated"
                view.load(QByteArray(svg)); view.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio); messages.append(UI[self.language()][key])
        try: star_svg, stats = render_star_chart(self.star_namespace())
        except Exception as exc:
            messages.append(UI[self.language()]["star_failed"].format(value=localized_error(exc, self.language())))
        else:
            self.star_chart.main_svg = star_svg; self.star_chart.preview.load(QByteArray(star_svg)); self.star_chart.preview.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
            messages.append(UI[self.language()]["star_summary"].format(stars=stats.stars, segments=stats.segments,
                labels=stats.star_labels + stats.figure_labels, hidden=stats.hidden_labels,
                missing=stats.missing_identifiers, degraded=stats.degraded_motion))
        try: back_svg, error = render_back(self.back_namespace())
        except Exception as exc:
            messages.append(UI[self.language()]['back_failed'].format(value=str(exc)))
        else:
            self.back.main_svg = back_svg; self.back.preview.load(QByteArray(back_svg))
            self.back.preview.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
            messages.append(UI[self.language()]['back_updated'].format(error=error))
        try:ruler_svg,skipped=render_ruler(self.ruler_namespace())
        except Exception as exc:messages.append(UI[self.language()]['ruler_failed'].format(value=str(exc)))
        else:
            self.ruler.main_svg=ruler_svg;self.ruler.preview.load(QByteArray(ruler_svg))
            self.ruler.preview.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
            messages.append(UI[self.language()]['ruler_updated'].format(count=skipped))
        self.status.setText(" ".join(messages))

    def save(self, path: Path):
        svg = self.main_svg
        if not svg: raise ValueError(UI[self.language()]["need_preview"])
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.current_index() == 2: self.star_chart.save(path)
        else:
            writer = self.projection_controls._write_svg if path.suffix.lower() == ".svg" else self.projection_controls._write_raster
            writer(svg, path)
        self._save_paths[self.current_index()] = path; self.status.setText(UI[self.language()]["saved"].format(value=path))

    def export_config_text(self):
        self._sync_shared_star_parameters()
        projection_args = self.projection_controls.export_args()
        if "--ecliptic" not in projection_args: projection_args.append("--ecliptic")
        return (f"# Astrolabe workspace: {self.projection}\n" + powershell_config(self.task, projection_args) + "\n" +
                powershell_config("draw-star-chart", self.star_chart.export_args()) + '\n' +
                powershell_config('draw-astrolabe-back', self.back.export_args(self.back_namespace())) + '\n' +
                powershell_config('draw-astrolabe-ruler', self.ruler.export_args(self.ruler_namespace())))

    def import_projection(self, argv: list[str]):
        self.projection_controls.import_args(argv); self.projection_controls.set_value("ecliptic", True)
        self.projection_controls.rows["ecliptic"][0].setVisible(False); self.projection_controls.rows["ecliptic"][1].setVisible(False)
        self._sync_shared_star_parameters()

    def import_star(self, argv: list[str]):
        self.star_chart.import_args(argv); self._sync_shared_star_parameters()

    def retranslate(self):
        self.main_section.setTitle(UI[self.language()]["main"]); self.ecliptic_section.setTitle(UI[self.language()]["ecliptic"]); self.star_section.setTitle(UI[self.language()]["star_chart"])
        self.back_section.setTitle(UI[self.language()]['back']); self.back.retranslate()
        self.ruler_section.setTitle(UI[self.language()]['ruler']);self.ruler.retranslate()
        self.ruler_shared_note.setText('外圆直径与线宽跟随主图；刻度跟随背面内圆、sin/cos 零值与 EOT 参数、星图年份。标尺水平绘制，左侧0–60，右侧EOT（分钟）。长度只改变外形，不缩放刻度。' if self.language()=='zh' else 'Global outline follows Main; scales follow the back inner circle, sin/cos zero and EOT ratios, and star-chart year. Horizontal ruler: 0–60 on the left, EOT minutes on the right. Length changes the outline, not scale calibration.')
        self.back_shared_note.setText('外径及外轮廓线宽跟随主图；年份跟随星图。日期取公历每日 UT 正午。偏心等距圈为近似拟合。EOT = 真太阳时 − 平太阳时，单位分钟。内圈半径恒为60标尺单位。' if self.language() == 'zh' else 'Diameter and outline follow Main; year follows Star Chart. Gregorian dates at noon UT. Eccentric calendar is an equal-spacing approximation. EOT = apparent − mean solar time (minutes). Inner radius always equals 60 ruler units.')
        for index, key in enumerate(("main", "ecliptic", "star_chart", "back", "ruler")): self.pages.setTabText(index, UI[self.language()][key])
        self.update_button.setText(UI[self.language()]["update"])
        self.projection_controls.retranslate(); self.star_chart.retranslate()
        if not self.main_svg: self.status.setText(UI[self.language()]["ready"])
        self.apply_responsive_layout(self.width())

    def apply_responsive_layout(self, width: int):
        if width <= 0: return
        compact = width < 1100
        all_rows = tuple(self.projection_controls.rows.values()) + tuple(self.star_chart.rows.values()) + tuple(self.back.rows.values()) + tuple(self.ruler.rows.values())
        widest = max((label.sizeHint().width() for label, _widget in all_rows), default=260)
        if compact: left_width = max(320, min(560, int(width * 0.52)))
        else: left_width = min(max(widest + 300, 440), 800)
        label_width = max(230, left_width - 52) if compact else max(220, left_width - 285)
        for form in self.section_forms:
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows if compact else QFormLayout.RowWrapPolicy.DontWrapRows)
            form.setVerticalSpacing(12 if compact else 8)
        for label, _widget in all_rows:
            label.setWordWrap(compact); label.setMaximumWidth(label_width if compact else 16777215)
            label.setMinimumWidth(label_width if compact else 0)
            label.setSizePolicy(QSizePolicy.Policy.Expanding if compact else QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            wrapped_height = label.heightForWidth(label_width) if compact else label.fontMetrics().height()
            label.setMinimumHeight(max(label.fontMetrics().height(), wrapped_height)); label.updateGeometry()
        self.left_panel.setMinimumWidth(left_width); preview = 220 if compact else 420
        for view in (self.projection_controls.main_view, self.projection_controls.ecliptic_view, self.star_chart.preview, self.back.preview, self.ruler.preview): view.setMinimumSize(preview, preview)
        self.splitter.setSizes([left_width, max(preview, width - left_width)])

    def refresh_cultures(self): self.star_chart.refresh_cultures()


class ImageCanvas(QLabel):
    def __init__(self):
        super().__init__(); self.setAlignment(Qt.AlignmentFlag.AlignCenter); self.setMinimumSize(420, 420)
        self.image: np.ndarray | None = None; self.points: list[tuple[float, float]] = []

    def set_image(self, image: np.ndarray | None): self.image = image; self.update_pixmap()

    def update_pixmap(self):
        if self.image is None: self.clear(); return
        pix = QPixmap.fromImage(qimage_from_bgr(self.image)).scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        canvas = QPixmap(self.size()); canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas); x=(self.width()-pix.width())//2; y=(self.height()-pix.height())//2; painter.drawPixmap(x,y,pix)
        if self.points:
            sx=pix.width()/self.image.shape[1]; sy=pix.height()/self.image.shape[0]; pen=QPen(Qt.GlobalColor.green, 2); painter.setPen(pen)
            mapped=[QPointF(x+px*sx,y+py*sy) for px,py in self.points]
            for i,p in enumerate(mapped): painter.drawEllipse(p,5,5); painter.drawText(p+QPointF(7,-7),str(i+1))
            for a,b in zip(mapped,mapped[1:]): painter.drawLine(a,b)
            if len(mapped)==4: painter.drawLine(mapped[-1],mapped[0])
        painter.end(); self.setPixmap(canvas)

    def resizeEvent(self, event): super().resizeEvent(event); self.update_pixmap()
    def mousePressEvent(self, event: QMouseEvent):
        if self.image is None or len(self.points)>=4: return
        iw,ih=self.image.shape[1],self.image.shape[0]; scale=min(self.width()/iw,self.height()/ih); dw,dh=iw*scale,ih*scale
        x=(event.position().x()-(self.width()-dw)/2)/scale; y=(event.position().y()-(self.height()-dh)/2)/scale
        if 0<=x<iw and 0<=y<ih: self.points.append((x,y)); self.update_pixmap()


class PerspectiveTab(QWidget):
    def __init__(self, language):
        super().__init__(); self.language=language; self.original=None; self.result=None; self.save_path: Path|None=None
        self.canvas=ImageCanvas(); self.status=QLabel()
        self.load_button=QPushButton(); self.load_button.clicked.connect(self.load_image)
        self.undo_button=QPushButton(); self.undo_button.clicked.connect(self.undo)
        self.reset_button=QPushButton(); self.reset_button.clicked.connect(self.reset)
        self.update_button=QPushButton(); self.update_button.clicked.connect(self.update_preview)
        buttons=QHBoxLayout(); [buttons.addWidget(x) for x in (self.load_button,self.undo_button,self.reset_button,self.update_button)]
        layout=QVBoxLayout(self); layout.addLayout(buttons); layout.addWidget(self.canvas); layout.addWidget(self.status)
        self.retranslate()
    def tr(self,key,**values):return UI[self.language()][key].format(**values)
    def retranslate(self):
        self.load_button.setText(self.tr("load"));self.undo_button.setText(self.tr("undo"));self.reset_button.setText(self.tr("reset"));self.update_button.setText(self.tr("rectify"))
        if self.original is None:self.status.setText(self.tr("pick4"))

    def load_image(self):
        name,_=QFileDialog.getOpenFileName(self,self.tr("load_title"),"",self.tr("images"))
        if not name:return
        data=np.fromfile(name,dtype=np.uint8); image=cv2.imdecode(data,cv2.IMREAD_COLOR)
        if image is None: QMessageBox.warning(self,self.tr("error",value="").rstrip(":： "),self.tr("read_failed")); return
        self.original=image; self.result=None; self.canvas.points=[]; self.canvas.set_image(image); self.status.setText(self.tr("pick4_short"))
    def undo(self):
        if self.canvas.points:self.canvas.points.pop();self.canvas.update_pixmap()
    def reset(self):
        self.result=None;self.canvas.points=[];self.canvas.set_image(self.original);self.status.setText(self.tr("reset_done"))
    def update_preview(self):
        if self.original is None or len(self.canvas.points)!=4:self.status.setText(self.tr("need4"));return
        try:self.result=rectify_mode_b(self.original,self.canvas.points)
        except Exception as exc:self.status.setText(self.tr("error",value=localized_error(exc,self.language())));return
        self.canvas.points=[];self.canvas.set_image(self.result);self.status.setText(self.tr("rectified"))
    def save(self,path:Path):
        if self.result is None:raise ValueError(self.tr("need_rectify"))
        ext=path.suffix.lower() or ".png"; ok,encoded=cv2.imencode(ext,self.result)
        if not ok:raise OSError(self.tr("unsupported",value=ext))
        path.parent.mkdir(parents=True,exist_ok=True);encoded.tofile(path);self.save_path=path;self.status.setText(self.tr("saved",value=path))


class ImportDialog(QDialog):
    def __init__(self,language,parent=None):
        super().__init__(parent);self.language=language;self.setWindowTitle(UI[language]["paste_title"]);self.resize(700,420);self.text=QTextEdit()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(UI[language]["ok"]);buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(UI[language]["cancel"])
        layout=QVBoxLayout(self);layout.addWidget(QLabel(UI[language]["paste_help"]));layout.addWidget(self.text);layout.addWidget(buttons)


class HelpDialog(QDialog):
    def __init__(self, language: str, parent=None):
        super().__init__(parent); self.setWindowTitle(UI[language]["gui_help"]); self.resize(760, 620)
        browser = QTextBrowser(); browser.setOpenExternalLinks(True); browser.setMarkdown(gui_help_markdown(language))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(UI[language]["close"])
        buttons.rejected.connect(self.reject); buttons.clicked.connect(self.accept)
        layout = QVBoxLayout(self); layout.addWidget(browser); layout.addWidget(buttons)


class AboutDialog(QDialog):
    def __init__(self, language: str, parent=None):
        super().__init__(parent); self.setWindowTitle(UI[language]["about"]); self.resize(680, 520)
        browser = QTextBrowser(); browser.setOpenExternalLinks(True); browser.setMarkdown(about_markdown(language))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(UI[language]["close"])
        buttons.rejected.connect(self.reject); buttons.clicked.connect(self.accept)
        layout = QVBoxLayout(self); layout.addWidget(browser); layout.addWidget(buttons)


class AstronomyDataDialog(QDialog):
    def __init__(self, language: str, cache: Path, changed, parent=None):
        super().__init__(parent); self.language = language; self.cache = cache; self.changed = changed
        self.setWindowTitle(UI[language]["data_title"]); self.resize(620, 240)
        self.location = QLabel(UI[language]["cache_location"].format(value=cache)); self.location.setWordWrap(True)
        self.status = QLabel(); self.status.setWordWrap(True)
        self.download_button = QPushButton(UI[language]["download_update"]); self.download_button.clicked.connect(self.download)
        self.clear_button = QPushButton(UI[language]["clear_cache"]); self.clear_button.clicked.connect(self.clear)
        self.open_button = QPushButton(UI[language]["open_cache"]); self.open_button.clicked.connect(self.open_folder)
        self.license_button = QPushButton(UI[language]["view_licenses"]); self.license_button.clicked.connect(self.view_licenses)
        buttons = QHBoxLayout(); buttons.addWidget(self.download_button); buttons.addWidget(self.clear_button); buttons.addWidget(self.open_button); buttons.addWidget(self.license_button)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close); close.button(QDialogButtonBox.StandardButton.Close).setText(UI[language]["close"]); close.rejected.connect(self.reject)
        layout = QVBoxLayout(self); layout.addWidget(self.location); layout.addWidget(self.status); layout.addLayout(buttons); layout.addWidget(close)
        self.refresh()

    def refresh(self):
        ready = self.cache.joinpath("hyg", "hygdata_v41.csv").exists() and bool(available_cultures(self.cache))
        errors = validate_star_cache(self.cache) if ready else []
        self.status.setText("\n".join(localized_error(error, self.language) for error in errors) if errors else UI[self.language]["cache_ready" if ready else "cache_missing"])

    def download(self):
        self.download_button.setEnabled(False); QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            download_star_data(self.cache, lambda message: (self.status.setText(message), QApplication.processEvents()))
            self.status.setText(UI[self.language]["download_done"]); self.changed()
        except Exception as exc:
            QMessageBox.warning(self, UI[self.language]["data_title"], localized_error(exc, self.language))
        finally:
            QApplication.restoreOverrideCursor(); self.download_button.setEnabled(True)

    def clear(self):
        if QMessageBox.question(self, UI[self.language]["data_title"], UI[self.language]["confirm_clear"]) != QMessageBox.StandardButton.Yes: return
        if self.cache.exists(): shutil.rmtree(self.cache)
        self.status.setText(UI[self.language]["clear_done"]); self.changed()

    def open_folder(self):
        self.cache.mkdir(parents=True, exist_ok=True); QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.cache)))

    def view_licenses(self):
        try: manifest = json.loads((self.cache / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError): manifest = {}
        culture_licenses = [str(path.relative_to(self.cache)) for path in self.cache.glob("stellarium/skycultures/*/LICENSE*")]
        text = [f"HYG {manifest.get('hyg', {}).get('version', '4.1')}: {manifest.get('hyg', {}).get('license', 'CC BY-SA 4.0')}",
                f"Stellarium {manifest.get('stellarium', {}).get('version', '26.1')}: {manifest.get('stellarium', {}).get('license', 'GPL-2.0 project')}"]
        if culture_licenses: text.extend(["", "Sky-culture license files:", *culture_licenses])
        if "milky_way" in manifest:
            text.extend(["", "Milky Way: " + manifest["milky_way"]["license"], manifest["milky_way"]["source"]])
        QMessageBox.information(self, UI[self.language]["licenses_title"], "\n".join(text))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.settings=QSettings("AstrolabeProjectionDrawers","GUI");self._language=self.settings.value("language","en")
        if self._language not in UI:self._language="en"
        self.setWindowTitle("Astrolabe Projection Drawers")
        screen=QApplication.primaryScreen();available=screen.availableGeometry() if screen is not None else None
        initial_width=min(1200,int(available.width()*0.95)) if available is not None else 1200
        initial_height=min(780,int(available.height()*0.90)) if available is not None else 780
        self.resize(max(640,initial_width),max(520,initial_height))
        self.tabs=QTabWidget();self.projection_tabs={}
        for task,projection in TASKS.items():
            tab=ProjectionWorkspace(task,projection,self.language,self.dpi);self.projection_tabs[task]=tab;self.tabs.addTab(tab,"")
        self.star_charts={workspace.projection:workspace.star_chart for workspace in self.projection_tabs.values()}
        self.perspective=PerspectiveTab(self.language);self.tabs.addTab(self.perspective,"");self.setCentralWidget(self.tabs)
        self.file_menu=self.menuBar().addMenu("");self.file_actions={}
        for key,slot,shortcut in (("import",self.import_config,"Ctrl+I"),("export_config",self.export_config,"Ctrl+E"),("save",self.save,"Ctrl+S"),("save_as",self.save_as,"Ctrl+Shift+S"),("exit",self.close,"Ctrl+Q")):
            action=QAction(self);action.setShortcut(shortcut);action.triggered.connect(slot);self.file_menu.addAction(action);self.file_actions[key]=action
        self.settings_menu=self.menuBar().addMenu("");self.language_menu=self.settings_menu.addMenu("")
        group=QActionGroup(self);group.setExclusive(True);self.language_actions={}
        for code,key in (("en","english"),("zh","chinese")):
            action=QAction(self);action.setCheckable(True);action.setData(code);action.setChecked(code==self._language);action.triggered.connect(lambda _checked,c=code:self.set_language(c));group.addAction(action);self.language_menu.addAction(action);self.language_actions[code]=(action,key)
        self.settings_menu.addSeparator();self.dpi_action=QAction(self);self.dpi_action.triggered.connect(self.set_dpi);self.settings_menu.addAction(self.dpi_action)
        self.data_action=QAction(self);self.data_action.triggered.connect(self.show_astronomy_data);self.settings_menu.addAction(self.data_action)
        self.help_menu=self.menuBar().addMenu("");self.gui_help_action=QAction(self);self.gui_help_action.setShortcut("F1");self.gui_help_action.triggered.connect(self.show_gui_help);self.help_menu.addAction(self.gui_help_action)
        self.about_action=QAction(self);self.about_action.triggered.connect(self.show_about);self.menuBar().addAction(self.about_action)
        self.retranslate()

    def language(self):return self._language
    def dpi(self):return int(self.settings.value("raster_dpi",300))
    def tr(self,key,**values):return UI[self._language][key].format(**values)
    def set_language(self,language):
        if language not in UI:return
        self._language=language;self.settings.setValue("language",language);self.retranslate()
    def set_dpi(self):
        value,ok=QInputDialog.getInt(self,self.tr("dpi_title"),self.tr("dpi_prompt"),self.dpi(),36,2400,1)
        if ok:self.settings.setValue("raster_dpi",value);self.settings.sync();self.retranslate()
    def show_astronomy_data(self):
        first=next(iter(self.star_charts.values()))
        AstronomyDataDialog(self._language,first.cache,lambda:[workspace.refresh_cultures() for workspace in self.projection_tabs.values()],self).exec()
    def retranslate(self):
        self.file_menu.setTitle(self.tr("file"));self.settings_menu.setTitle(self.tr("settings"));self.language_menu.setTitle(self.tr("language"))
        self.help_menu.setTitle(self.tr("help"));self.gui_help_action.setText(self.tr("gui_help"));self.about_action.setText(self.tr("about"))
        self.dpi_action.setText(f"{self.tr('dpi')}  ({self.dpi()} DPI)")
        self.data_action.setText(self.tr("astronomy_data"))
        for key,action in self.file_actions.items():action.setText(self.tr(key))
        for action,key in self.language_actions.values():action.setText(self.tr(key))
        self.tabs.setTabText(self.tabs.indexOf(self.projection_tabs["draw-azimuthal-equidistant"]),self.tr("azimuthal"))
        self.tabs.setTabText(self.tabs.indexOf(self.projection_tabs["draw-stereographic"]),self.tr("stereographic"))
        self.tabs.setTabText(self.tabs.indexOf(self.perspective),self.tr("perspective"))
        for tab in (*self.projection_tabs.values(),self.perspective):tab.retranslate()
        content_width=max(1,self.tabs.width())
        for tab in self.projection_tabs.values():tab.apply_responsive_layout(content_width)

    def show_gui_help(self):
        HelpDialog(self._language,self).exec()

    def show_about(self):
        AboutDialog(self._language,self).exec()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        content_width=max(1,event.size().width()-24)
        for tab in self.projection_tabs.values():tab.apply_responsive_layout(content_width)

    def current(self):
        return self.tabs.currentWidget()
    def import_config(self):
        box=QMessageBox(self);box.setWindowTitle(self.tr("import_title"));box.setText(self.tr("import_how"));file_button=box.addButton(self.tr("open_file"),QMessageBox.ButtonRole.AcceptRole);paste_button=box.addButton(self.tr("paste"),QMessageBox.ButtonRole.ActionRole);cancel_button=box.addButton(QMessageBox.StandardButton.Cancel);cancel_button.setText(self.tr("cancel"));box.exec()
        if box.clickedButton()==file_button:
            name,_=QFileDialog.getOpenFileName(self,self.tr("open_config"),"",self.tr("text_files"))
            if not name:return
            text=Path(name).read_text(encoding="utf-8")
        elif box.clickedButton()==paste_button:
            dialog=ImportDialog(self._language,self)
            if dialog.exec()!=QDialog.DialogCode.Accepted:return
            text=dialog.text.toPlainText()
        else:return
        try:
            commands=tokenize_workspace_config(text)
            if commands:
                projection_commands=[command for command in commands if command[0] in TASKS]
                star_commands=[command for command in commands if command[0]=="draw-star-chart"]
                if len(projection_commands)!=1 or len(star_commands)!=1:raise ValueError("Workspace configuration must contain one projection command and one star-chart command.")
                projection_command=projection_commands[0];workspace=self.projection_tabs[projection_command[0]]
                star_args=build_star_parser().parse_args(star_commands[0][1:])
                if star_args.projection!=workspace.projection:raise ValueError("Star-chart projection does not match the workspace projection.")
                workspace.import_projection(projection_command[1:]);workspace.import_star(star_commands[0][1:])
                back_commands=[command for command in commands if command[0]=="draw-astrolabe-back"]
                if len(back_commands)>1: raise ValueError("Workspace contains multiple back commands.")
                if back_commands: workspace.import_back(back_commands[0][1:])
                ruler_commands=[command for command in commands if command[0]=="draw-astrolabe-ruler"]
                if len(ruler_commands)>1:raise ValueError("Workspace contains multiple ruler commands.")
                if ruler_commands:workspace.import_ruler(ruler_commands[0][1:])
                workspace.status.setText(self.tr("imported"));self.tabs.setCurrentWidget(workspace);return
            tokens=tokenize_config(text);task=tokens[0] if tokens and tokens[0] in (*TASKS,"draw-star-chart","draw-astrolabe-back","draw-astrolabe-ruler") else None;argv=tokens[1:] if task else tokens
            if not task:
                current=self.current();task=getattr(current,"task",None) if hasattr(current,"import_args") else None
            if not task:raise ValueError(self.tr("task_missing"))
            if task=="draw-astrolabe-ruler":
                parsed=build_ruler_parser().parse_args(argv);workspace=next(item for item in self.projection_tabs.values() if item.projection==parsed.projection)
                validate_back(parsed);validate_ruler(parsed)
                workspace.projection_controls.set_value("diameter",parsed.diameter)
                workspace.projection_controls.set_value("boundary_width",parsed.boundary_width)
                workspace.star_chart.set_value("epoch_year",parsed.epoch_year)
                for name in workspace.back.widgets:workspace.back.set_value(name,getattr(parsed,name))
                workspace.back.refresh_visibility();workspace.import_ruler(argv);workspace.select_index(4)
            elif task=="draw-astrolabe-back":
                parsed=build_back_parser().parse_args(argv);workspace=next(item for item in self.projection_tabs.values() if item.projection==parsed.projection)
                workspace.projection_controls.set_value("diameter",parsed.diameter)
                workspace.projection_controls.set_value("boundary_width",parsed.boundary_width)
                workspace.star_chart.set_value("epoch_year",parsed.epoch_year)
                workspace.import_back(argv);workspace.select_index(3)
            elif task=="draw-star-chart":
                parsed=build_star_parser().parse_args(argv);workspace=next(item for item in self.projection_tabs.values() if item.projection==parsed.projection)
                workspace.import_star(argv);workspace.select_index(2)
            else:
                workspace=self.projection_tabs[task];parsed=parse_args(workspace.projection,argv);workspace.import_projection(argv);workspace.select_index(1 if parsed.ecliptic else 0)
            self.tabs.setCurrentWidget(workspace)
        except (Exception,SystemExit) as exc:QMessageBox.warning(self,self.tr("import_failed"),localized_error(exc,self._language) if str(exc) else self.tr("bad_args"))
    def save(self):
        tab=self.current();path=getattr(tab,"save_path",None)
        if path is None:self.save_as();return
        try:tab.save(path)
        except Exception as exc:QMessageBox.warning(self,self.tr("save_failed"),localized_error(exc,self._language))
    def export_config(self):
        tab=self.current()
        if not hasattr(tab,"export_config_text"):
            QMessageBox.information(self,self.tr("export_title"),self.tr("projection_only"));return
        name,_=QFileDialog.getSaveFileName(self,self.tr("export_title"),f"{tab.task}.txt",self.tr("config_files"))
        if not name:return
        path=Path(name)
        if path.suffix.lower() != ".txt": path=path.with_suffix(".txt")
        try:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(tab.export_config_text(),encoding="utf-8")
            tab.status.setText(self.tr("exported",value=path))
        except Exception as exc:QMessageBox.warning(self,self.tr("export_failed"),localized_error(exc,self._language))
    def save_as(self):
        tab=self.current();filters="SVG (*.svg);;PNG (*.png);;JPEG (*.jpg)" if hasattr(tab,"main_svg") else "PNG (*.png);;JPEG (*.jpg)"
        name,_=QFileDialog.getSaveFileName(self,self.tr("save_title"),"",filters)
        if not name:return
        try:tab.save(Path(name))
        except Exception as exc:QMessageBox.warning(self,self.tr("save_failed"),localized_error(exc,self._language))


def main():
    app=QApplication(sys.argv);window=MainWindow();window.show();sys.exit(app.exec())


if __name__=="__main__":main()
