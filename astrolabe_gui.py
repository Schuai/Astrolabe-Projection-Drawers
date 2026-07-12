from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QByteArray, QPointF, QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFileDialog, QFormLayout, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QSplitter, QTabWidget, QTextEdit, QInputDialog,
    QVBoxLayout, QWidget,
    QTextBrowser,
)

from draw_projection import (
    AZIMUTHAL_EQUIDISTANT, STEREOGRAPHIC, build_parser, parse_args, svg_bytes,
)
from perspective_corrector import rectify_mode_b


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
        "main": "Main", "ecliptic": "Ecliptic", "ready": "Set the arguments, then click Update Preview.",
        "updated": "Preview updated.", "updated_pair": "Main and Ecliptic previews updated.", "error": "Error: {value}",
        "main_updated": "Main preview updated.", "ecliptic_updated": "Ecliptic preview updated.",
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
        "help": "Help", "gui_help": "GUI Usage", "close": "Close",
        "dpi": "Raster Export DPI…", "dpi_title": "Raster Export DPI", "dpi_prompt": "DPI for PNG and JPEG export:",
    },
    "zh": {
        "file": "文件", "settings": "设置", "language": "语言",
        "english": "English", "chinese": "中文", "import": "导入配置…", "export_config": "导出配置…",
        "save": "保存", "save_as": "另存为…", "exit": "退出",
        "azimuthal": "等距方位投影", "stereographic": "球极投影", "perspective": "透视校正",
        "update": "更新预览", "main": "主图", "ecliptic": "黄道图",
        "ready": "设置参数后点击“更新预览”。", "updated": "预览已更新。", "updated_pair": "主图和黄道图预览已更新。", "error": "错误：{value}",
        "main_updated": "主图预览已更新。", "ecliptic_updated": "黄道图预览已更新。",
        "main_failed": "主图预览更新失败：{value}", "ecliptic_failed": "黄道图预览更新失败：{value}",
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
        "help": "帮助", "gui_help": "GUI 使用说明", "close": "关闭",
        "dpi": "栅格导出 DPI…", "dpi_title": "栅格导出 DPI", "dpi_prompt": "PNG 和 JPEG 导出 DPI：",
    },
}

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
        text = Path(__file__).with_name("README.md").read_text(encoding="utf-8")
    except OSError:
        return {}
    result: dict[str, str] = {}
    for option, description in re.findall(r"^- `(--[\w-]+)` (.+)$", text, re.MULTILINE):
        result[option] = description.strip()
    return result


README_HELP_EN = read_readme_help()


def read_readme_gui_section() -> str:
    try:
        text = Path(__file__).with_name("README.md").read_text(encoding="utf-8")
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

前两个标签页分别对应等距方位投影和球极投影。基础参数始终显示；只有启用父功能后，相关的从属参数才会出现。将鼠标悬停在参数名称上可查看说明。设置完成后，点击 **更新预览** 进行绘制，预览不会覆盖已有文件。

启用黄道输出后，预览区的 **黄道图** 标签会启用，并显示独立的伴随图。

在透视校正标签页中载入图片，依次点击四个角点，再点击 **更新预览 / 校正**。执行校正前可以撤销选点或重置。

使用 **文件 > 导入配置** 可以打开 README、TXT 或 PowerShell 文件，也可以粘贴 `pixi run` 命令、PowerShell `@(...)` 参数列表或纯命令行参数。导入操作只解析文本，不会执行其中的命令。

使用 **文件 > 导出配置** 可以把当前绘图标签页的有效参数保存为 `.txt`。导出的文件可以再次导入。

使用 **保存** 或 **另存为** 可输出 SVG、透明背景 PNG 或白色背景 JPEG。可在 **设置 > 栅格导出 DPI** 中调整栅格分辨率，默认为 300 DPI。启用黄道图时，会同时保存带 `_ecliptic` 后缀的伴随文件。

应用默认使用英文。可通过 **设置 > 语言** 在英文和中文之间切换；修改立即全局生效，并会保存到下次启动。
"""


def gui_help_markdown(language: str) -> str:
    return README_GUI_ZH if language == "zh" else README_GUI_EN

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


def localized_error(error: object, language: str) -> str:
    message = str(error)
    if language != "zh": return message
    if message in ERROR_ZH: return ERROR_ZH[message]
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
    task_match = re.search(r"pixi\s+run\s+(draw-(?:azimuthal-equidistant|stereographic))", text)
    task = task_match.group(1) if task_match else ""
    tokens = re.findall(r'"([^"\r\n]*)"|\'([^\'\r\n]*)\'|(--?[A-Za-z][\w-]*|[-+]?\d+(?:\.\d+)?|north|south|clockwise|counterclockwise|solid|dashed)', text)
    flat = [next(part for part in match if part) for match in tokens]
    start = next((i for i, token in enumerate(flat) if token.startswith("--")), len(flat))
    return ([task] if task else []) + flat[start:]


def readme_example_tokens(heading: str, task: str) -> list[str]:
    """Return args from a runnable command in a named README section."""
    try:
        text = Path(__file__).with_name("README.md").read_text(encoding="utf-8")
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
    def __init__(self, task: str, projection: str, language, dpi=lambda: 300):
        super().__init__()
        self.task, self.projection = task, projection
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
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(form_host)
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
        self.left_panel = QWidget(); ll = QVBoxLayout(self.left_panel); ll.addWidget(scroll); ll.addWidget(self.update_button)

        self.preview_tabs = QTabWidget()
        self.main_view = QSvgWidget(); self.main_view.setMinimumSize(420, 420)
        self.ecliptic_view = QSvgWidget(); self.ecliptic_view.setMinimumSize(420, 420)
        self.main_view.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.ecliptic_view.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.preview_tabs.addTab(self.main_view, "")
        self.preview_tabs.addTab(self.ecliptic_view, "")
        self.preview_tabs.setTabEnabled(self.preview_tabs.indexOf(self.ecliptic_view), False)
        self.status = QLabel(); self.status.setWordWrap(True)
        right = QWidget(); rl = QVBoxLayout(right); rl.addWidget(self.preview_tabs); rl.addWidget(self.status)
        self.splitter = QSplitter(); self.splitter.addWidget(self.left_panel); self.splitter.addWidget(right); self.splitter.setStretchFactor(1, 1)
        layout = QVBoxLayout(self); layout.addWidget(self.splitter)
        self.apply_readme_defaults()
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
        widest = max((label.sizeHint().width() for label, _widget in self.rows.values()), default=250)
        desired = min(max(widest + 285, 410), 760)
        self.left_panel.setMinimumWidth(desired)
        self.splitter.setSizes([desired, max(500, self.splitter.width() - desired)])

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
        for name, row in self.rows.items():
            visible = DEPENDENCIES.get(name, lambda _v: True)(self.value)
            row[0].setVisible(visible); row[1].setVisible(visible)

    def namespace(self) -> argparse.Namespace:
        values = {name: self.value(name) for name in self.widgets}
        # A hidden child switch must not keep its feature active when its parent is off.
        for name, (_label, widget) in self.rows.items():
            if widget.isHidden() and isinstance(widget, QCheckBox): values[name] = False
        args = argparse.Namespace(**values)
        args.output = Path("preview.svg"); args.projection = self.projection
        return args

    def update_preview(self):
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
        if not self.main_svg: raise ValueError(self.tr("need_preview"))
        path.parent.mkdir(parents=True, exist_ok=True)
        writer = self._write_svg if path.suffix.lower() == ".svg" else self._write_raster
        writer(self.main_svg, path)
        if self.ecliptic_svg:
            companion = path.with_name(f"{path.stem}_ecliptic{path.suffix}")
            writer(self.ecliptic_svg, companion)
        self.save_path = path; self.status.setText(self.tr("saved", value=path))


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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.settings=QSettings("AstrolabeProjectionDrawers","GUI");self._language=self.settings.value("language","en")
        if self._language not in UI:self._language="en"
        self.setWindowTitle("Astrolabe Projection Drawers");self.resize(1200,780)
        self.tabs=QTabWidget();self.projection_tabs={}
        for task,projection in TASKS.items():
            tab=ProjectionTab(task,projection,self.language,self.dpi);self.projection_tabs[task]=tab;self.tabs.addTab(tab,"")
        self.perspective=PerspectiveTab(self.language);self.tabs.addTab(self.perspective,"");self.setCentralWidget(self.tabs)
        self.file_menu=self.menuBar().addMenu("");self.file_actions={}
        for key,slot,shortcut in (("import",self.import_config,"Ctrl+I"),("export_config",self.export_config,"Ctrl+E"),("save",self.save,"Ctrl+S"),("save_as",self.save_as,"Ctrl+Shift+S"),("exit",self.close,"Ctrl+Q")):
            action=QAction(self);action.setShortcut(shortcut);action.triggered.connect(slot);self.file_menu.addAction(action);self.file_actions[key]=action
        self.settings_menu=self.menuBar().addMenu("");self.language_menu=self.settings_menu.addMenu("")
        group=QActionGroup(self);group.setExclusive(True);self.language_actions={}
        for code,key in (("en","english"),("zh","chinese")):
            action=QAction(self);action.setCheckable(True);action.setData(code);action.setChecked(code==self._language);action.triggered.connect(lambda _checked,c=code:self.set_language(c));group.addAction(action);self.language_menu.addAction(action);self.language_actions[code]=(action,key)
        self.settings_menu.addSeparator();self.dpi_action=QAction(self);self.dpi_action.triggered.connect(self.set_dpi);self.settings_menu.addAction(self.dpi_action)
        self.help_menu=self.menuBar().addMenu("");self.gui_help_action=QAction(self);self.gui_help_action.setShortcut("F1");self.gui_help_action.triggered.connect(self.show_gui_help);self.help_menu.addAction(self.gui_help_action)
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
    def retranslate(self):
        self.file_menu.setTitle(self.tr("file"));self.settings_menu.setTitle(self.tr("settings"));self.language_menu.setTitle(self.tr("language"))
        self.help_menu.setTitle(self.tr("help"));self.gui_help_action.setText(self.tr("gui_help"))
        self.dpi_action.setText(f"{self.tr('dpi')}  ({self.dpi()} DPI)")
        for key,action in self.file_actions.items():action.setText(self.tr(key))
        for action,key in self.language_actions.values():action.setText(self.tr(key))
        self.tabs.setTabText(self.tabs.indexOf(self.projection_tabs["draw-azimuthal-equidistant"]),self.tr("azimuthal"))
        self.tabs.setTabText(self.tabs.indexOf(self.projection_tabs["draw-stereographic"]),self.tr("stereographic"))
        self.tabs.setTabText(self.tabs.indexOf(self.perspective),self.tr("perspective"))
        for tab in (*self.projection_tabs.values(),self.perspective):tab.retranslate()
        if self._language == "zh":
            left_width = max(tab.left_panel.minimumWidth() for tab in self.projection_tabs.values())
            screen = QApplication.primaryScreen()
            target = left_width + 620
            if screen is not None: target = min(target, screen.availableGeometry().width())
            if self.width() < target: self.resize(target, self.height())

    def show_gui_help(self):
        HelpDialog(self._language,self).exec()

    def current(self):return self.tabs.currentWidget()
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
            tokens=tokenize_config(text);task=tokens[0] if tokens and tokens[0] in TASKS else None;argv=tokens[1:] if task else tokens
            if not task:
                current=self.current();task=current.task if isinstance(current,ProjectionTab) else None
            if not task:raise ValueError(self.tr("task_missing"))
            tab=self.projection_tabs[task];tab.import_args(argv);self.tabs.setCurrentWidget(tab)
        except (Exception,SystemExit) as exc:QMessageBox.warning(self,self.tr("import_failed"),localized_error(exc,self._language) if str(exc) else self.tr("bad_args"))
    def save(self):
        tab=self.current();path=getattr(tab,"save_path",None)
        if path is None:self.save_as();return
        try:tab.save(path)
        except Exception as exc:QMessageBox.warning(self,self.tr("save_failed"),localized_error(exc,self._language))
    def export_config(self):
        tab=self.current()
        if not isinstance(tab,ProjectionTab):
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
        tab=self.current();filters="SVG (*.svg);;PNG (*.png);;JPEG (*.jpg)" if isinstance(tab,ProjectionTab) else "PNG (*.png);;JPEG (*.jpg)"
        name,_=QFileDialog.getSaveFileName(self,self.tr("save_title"),"",filters)
        if not name:return
        try:tab.save(Path(name))
        except Exception as exc:QMessageBox.warning(self,self.tr("save_failed"),localized_error(exc,self._language))


def main():
    app=QApplication(sys.argv);window=MainWindow();window.show();sys.exit(app.exec())


if __name__=="__main__":main()
