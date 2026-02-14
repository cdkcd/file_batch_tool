#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件批量处理工具
支持功能：
1. 批量重命名（正则替换、前缀/后缀）
2. 批量转换图片格式（jpg/png/webp）
3. 批量压缩文件（ZIP）
4. 批量文件分类（按扩展名/日期归档）
5. 图片批量加水印（文字/图片水印）
6. 批量修改文件时间（新增）
7. 批量提取图片EXIF信息（新增）
8. 批量复制/移动文件（新增）
"""

import os
import sys
import re
import zipfile
import csv
import time
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ExifTags
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QFileDialog,
    QSpinBox, QDoubleSpinBox, QGroupBox, QMessageBox, QProgressBar, QDateTimeEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont

# 解决PIL处理大图片的DecompressionBombWarning
Image.MAX_IMAGE_PIXELS = None


# ===================== 功能函数（修复统计逻辑） =====================
def batch_rename(dir_path, prefix="", suffix="", pattern="", replace="", log_callback=None):
    """批量重命名"""

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    # 严格获取目录下的文件，排除子文件夹，精准去重
    dir_path_obj = Path(dir_path)
    if not dir_path_obj.is_dir():
        log(f"❌ 路径 {dir_path} 不是有效目录")
        return False

    # 仅获取文件，彻底排除文件夹，避免把文件夹当作文件统计
    file_list = [f for f in dir_path_obj.glob("*") if f.is_file()]
    file_count = len(file_list)

    # 空目录精准判断，直接返回
    if file_count == 0:
        log(f"❌ 目录 {dir_path} 下未找到任何文件")
        return False

    # 正则预编译，增加异常捕获（避免正则语法错误导致整个任务崩溃）
    pattern_compile = None
    if pattern.strip():
        try:
            pattern_compile = re.compile(pattern)
        except re.error as e:
            log(f"❌ 正则表达式语法错误：{str(e)}")
            return False

    rename_count = 0  # 实际成功重命名的文件数
    skip_count = 0  # 跳过的文件数（同名/无修改）

    log(f"📝 开始批量重命名，共扫描到 {file_count} 个有效文件")
    for idx, file_path in enumerate(file_list):
        old_name = file_path.name
        name, ext = os.path.splitext(old_name)  # 提前拆分主名和扩展名，避免重复处理
        new_main_name = name
        new_ext = ext

        # 1. 正则替换（仅替换主名，避免扩展名被修改）
        if pattern_compile:
            new_main_name = pattern_compile.sub(replace, new_main_name)

        # 2. 添加前缀/后缀（仅对主名操作，保护扩展名）
        if prefix:
            new_main_name = prefix + new_main_name
        if suffix:
            new_main_name = new_main_name + suffix

        # 拼接新文件名
        new_name = new_main_name + new_ext
        # 新老名称一致，直接跳过
        if new_name == old_name:
            skip_count += 1
            continue

        new_path = file_path.parent / new_name
        # 目标文件已存在，跳过并日志提示
        if new_path.exists():
            log(f"⚠️ 跳过 {old_name}：新文件名 {new_name} 已存在")
            skip_count += 1
            continue

        # 执行重命名，增加异常捕获（权限/文件占用）
        try:
            file_path.rename(new_path)
            rename_count += 1
            log(f"✅ 重命名：{old_name} → {new_name}")
        except PermissionError:
            log(f"⚠️ 跳过 {old_name}：无操作权限/文件被占用")
            skip_count += 1
        except Exception as e:
            log(f"⚠️ 跳过 {old_name}：重命名失败 - {str(e)}")
            skip_count += 1

        # 实时更新进度（按总文件数计算，精准到1%）
        if log_callback:
            progress = int((idx + 1) / file_count * 100)
            log(f"progress:{progress}")

    # 最终统计日志，清晰展示结果
    log(f"\n✅ 重命名任务结束 | 总文件：{file_count} | 成功重命名：{rename_count} | 跳过：{skip_count}")
    return rename_count > 0  # 至少成功一个才返回True


def batch_convert_image(dir_path, to_format, log_callback=None):
    """批量转换图片格式（适配GUI日志输出）- 修复统计错误"""

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    SUPPORT_FORMATS = ["jpg", "jpeg", "png", "webp"]
    target_format = to_format.lower()

    img_list = []
    for ext in SUPPORT_FORMATS:
        img_list.extend(Path(dir_path).glob(f"*.{ext}"))
        img_list.extend(Path(dir_path).glob(f"*.{ext.upper()}"))
    # 去重 + 仅保留文件
    img_list = list({f for f in img_list if f.is_file()})
    img_count = len(img_list)

    if img_count == 0:
        log(f"❌ 目录 {dir_path} 下未找到支持的图片文件（{SUPPORT_FORMATS}）")
        return False

    convert_count = 0
    log(f"🖼️ 开始批量转换图片格式，共找到 {img_count} 张图片")

    for idx, img_path in enumerate(img_list):
        try:
            with Image.open(img_path) as img:
                if target_format in ["jpg", "jpeg"]:
                    if img.mode in ("RGBA", "P"):
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        mask = img.split()[-1] if img.mode == "RGBA" else None
                        bg.paste(img, (0, 0), mask)
                        img = bg
                    else:
                        img = img.convert("RGB")
                else:
                    img = img.convert("RGBA") if img.mode != "RGBA" else img

                new_name = f"{img_path.stem}_converted.{target_format}"
                new_path = img_path.parent / new_name

                format_map = {
                    "jpg": "JPEG",
                    "jpeg": "JPEG",
                    "png": "PNG",
                    "webp": "WEBP"
                }
                save_format = format_map.get(target_format, target_format.upper())
                img.save(new_path, save_format, quality=95)
                convert_count += 1

        except PermissionError:
            log(f"\n⚠️ 无权限写入 {new_path}，请关闭该文件后重试")
        except Exception as e:
            log(f"\n⚠️ 处理 {img_path.name} 失败：{str(e)}")
            continue

        # 更新进度
        if log_callback:
            progress = int((idx + 1) / img_count * 100)
            log(f"progress:{progress}")

    log(f"✅ 图片转换完成，共成功处理 {convert_count} 张图片")
    return True


def batch_compress(dir_path, output="", exclude="", log_callback=None):
    """批量压缩文件（适配GUI日志输出）"""

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    file_list = [f for f in Path(dir_path).glob("*") if f.is_file()]
    if exclude:
        exclude_exts = [ext.strip() for ext in exclude.split(",")]
        file_list = [f for f in file_list if f.suffix.lstrip(".") not in exclude_exts]

    file_count = len(file_list)
    if file_count == 0:
        log(f"❌ 目录 {dir_path} 下未找到可压缩的文件")
        return False

    zip_name = output if output else f"{dir_path}_compressed.zip"
    zip_path = Path(zip_name)
    if zip_path.exists():
        log(f"❌ ZIP包 {zip_path} 已存在，请更换输出文件名")
        return False

    log(f"📦 开始批量压缩文件，共找到 {file_count} 个文件")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for idx, file_path in enumerate(file_list):
            zipf.write(file_path, arcname=file_path.name)
            # 更新进度
            if log_callback:
                progress = int((idx + 1) / file_count * 100)
                log(f"progress:{progress}")

    log(f"✅ 压缩完成！ZIP包已保存至：{zip_path.absolute()}")
    return True


def batch_classify(dir_path, mode, log_callback=None):
    """批量文件分类（适配GUI日志输出）"""

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    file_list = [f for f in Path(dir_path).glob("*") if f.is_file()]
    file_count = len(file_list)
    if file_count == 0:
        log(f"❌ 目录 {dir_path} 下无文件")
        return False

    classify_dir = Path(dir_path) / "classified"
    classify_dir.mkdir(exist_ok=True)
    count = 0

    log(f"📂 开始批量分类，共 {file_count} 个文件")
    for idx, file_path in enumerate(file_list):
        if mode == "ext":
            ext = file_path.suffix.lstrip(".").lower() or "no_ext"
            target_dir = classify_dir / ext
        elif mode == "date":
            ctime = datetime.fromtimestamp(file_path.stat().st_ctime)
            date_str = ctime.strftime("%Y-%m")
            target_dir = classify_dir / date_str
        else:
            log(f"⚠️ 不支持的分类模式：{mode}")
            return False

        target_dir.mkdir(exist_ok=True)
        try:
            file_path.rename(target_dir / file_path.name)
            count += 1
        except Exception as e:
            log(f"\n⚠️ 移动 {file_path.name} 失败：{str(e)}")
            continue

        # 更新进度
        if log_callback:
            progress = int((idx + 1) / file_count * 100)
            log(f"progress:{progress}")

    log(f"✅ 分类完成，共处理 {count} 个文件，已归档至 {classify_dir}")
    return True


def batch_watermark(dir_path, type_, content="", font="", size=24, color="(255,255,255,128)",
                    opacity=128, watermark_path="", log_callback=None):
    """图片批量加水印（适配GUI日志输出）- 修复统计错误"""

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    SUPPORT_FORMATS = ["jpg", "jpeg", "png", "webp"]
    img_list = []
    for ext in SUPPORT_FORMATS:
        img_list.extend(Path(dir_path).glob(f"*.{ext}"))
    # 去重 + 仅保留文件
    img_list = list({f for f in img_list if f.is_file()})
    img_count = len(img_list)

    if img_count == 0:
        log(f"❌ 目录 {dir_path} 下无支持的图片")
        return False

    count = 0
    log(f"🔖 开始批量添加水印，共 {img_count} 张图片")

    if type_ == "text":
        color_tuple = eval(color) if color else (255, 255, 255, 128)
        try:
            font_obj = ImageFont.truetype(font, size) if font else ImageFont.load_default()
        except:
            font_obj = ImageFont.load_default()
    elif type_ == "image":
        try:
            watermark_img = Image.open(watermark_path).convert("RGBA")
            watermark_img = watermark_img.resize((size, size), Image.Resampling.LANCZOS)
            alpha = watermark_img.split()[3]
            alpha = alpha.point(lambda p: p * opacity / 255)
            watermark_img.putalpha(alpha)
        except Exception as e:
            log(f"❌ 加载图片水印失败：{str(e)}")
            return False
    else:
        log(f"⚠️ 不支持的水印类型：{type_}")
        return False

    for idx, img_path in enumerate(img_list):
        try:
            img = Image.open(img_path).convert("RGBA")
            draw = ImageDraw.Draw(img)
            width, height = img.size

            if type_ == "text":
                text_bbox = draw.textbbox((0, 0), content, font=font_obj)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                pos = (width - text_width - 20, height - text_height - 20)
                draw.text(pos, content, font=font_obj, fill=color_tuple)
            elif type_ == "image":
                pos = (width - size - 20, height - size - 20)
                img.paste(watermark_img, pos, mask=watermark_img)

            new_path = img_path.parent / f"watermarked_{img_path.name}"
            if img_path.suffix.lower() in (".jpg", ".jpeg"):
                img.convert("RGB").save(new_path, "JPEG")
            else:
                img.save(new_path, img_path.suffix[1:].upper())
            count += 1
        except Exception as e:
            log(f"\n⚠️ 处理 {img_path.name} 失败：{str(e)}")
            continue

        # 更新进度
        if log_callback:
            progress = int((idx + 1) / img_count * 100)
            log(f"progress:{progress}")

    log(f"✅ 水印添加完成，共处理 {count} 张图片")
    return True


# ===================== 新增功能函数（修复统计逻辑） =====================
def batch_modify_file_time(dir_path, target_time, time_type="both", log_callback=None):
    """
    批量修改文件时间（新增）
    :param dir_path: 目标目录
    :param target_time: 目标时间（datetime对象）
    :param time_type: 修改类型 - create(创建时间)/modify(修改时间)/both(两者)
    :param log_callback: 日志回调
    """

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    file_list = [f for f in Path(dir_path).glob("*") if f.is_file()]
    file_count = len(file_list)
    if file_count == 0:
        log(f"❌ 目录 {dir_path} 下未找到文件")
        return False

    target_timestamp = datetime.timestamp(target_time)
    modify_count = 0
    log(f"🕒 开始批量修改文件时间，共找到 {file_count} 个文件")

    for idx, file_path in enumerate(file_list):
        try:
            # Windows和Linux的时间修改差异处理
            if time_type in ["create", "both"]:
                if sys.platform == "win32":
                    os.utime(file_path, (target_timestamp, target_timestamp))
                else:
                    # Linux下修改创建时间需要借助os.system（简化版）
                    os.system(f"touch -t {target_time.strftime('%Y%m%d%H%M.%S')} {file_path}")

            if time_type in ["modify", "both"]:
                os.utime(file_path, (os.path.getatime(file_path), target_timestamp))

            modify_count += 1
        except PermissionError:
            log(f"\n⚠️ 无权限修改 {file_path.name} 时间，请关闭该文件后重试")
        except Exception as e:
            log(f"\n⚠️ 处理 {file_path.name} 失败：{str(e)}")
            continue

        # 更新进度
        if log_callback:
            progress = int((idx + 1) / file_count * 100)
            log(f"progress:{progress}")

    log(f"✅ 时间修改完成，共处理 {modify_count} 个文件")
    return True


def batch_extract_exif(dir_path, output_csv, log_callback=None):
    """
    批量提取图片EXIF信息（新增）- 修复统计错误
    :param dir_path: 图片目录
    :param output_csv: 输出CSV文件路径
    :param log_callback: 日志回调
    """

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    SUPPORT_FORMATS = ["jpg", "jpeg", "png", "webp"]
    img_list = []
    for ext in SUPPORT_FORMATS:
        img_list.extend(Path(dir_path).glob(f"*.{ext}"))
        img_list.extend(Path(dir_path).glob(f"*.{ext.upper()}"))
    # 去重 + 仅保留文件
    img_list = list({f for f in img_list if f.is_file()})
    img_count = len(img_list)

    if img_count == 0:
        log(f"❌ 目录 {dir_path} 下未找到支持的图片文件")
        return False

    # 准备CSV表头
    headers = ["文件名", "路径", "宽度", "高度", "拍摄时间", "设备型号", "分辨率", "GPS信息"]
    extract_count = 0
    log(f"📷 开始提取EXIF信息，共找到 {img_count} 张图片")

    try:
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

            for idx, img_path in enumerate(img_list):
                try:
                    exif_data = {}
                    with Image.open(img_path) as img:
                        # 基础信息
                        exif_data["文件名"] = img_path.name
                        exif_data["路径"] = str(img_path.absolute())
                        exif_data["宽度"] = img.width
                        exif_data["高度"] = img.height
                        exif_data["分辨率"] = f"{img.width}x{img.height}"
                        exif_data["拍摄时间"] = ""
                        exif_data["设备型号"] = ""
                        exif_data["GPS信息"] = ""

                        # 提取EXIF
                        exif = img.getexif()
                        if exif:
                            # 映射EXIF标签
                            exif_tag_map = {v: k for k, v in ExifTags.TAGS.items()}
                            for tag_id, value in exif.items():
                                tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                                # 拍摄时间
                                if tag_name == "DateTimeOriginal":
                                    exif_data["拍摄时间"] = value
                                # 设备型号
                                elif tag_name == "Model":
                                    exif_data["设备型号"] = value
                                # GPS信息（简化）
                                elif tag_name == "GPSInfo":
                                    exif_data["GPS信息"] = "有GPS数据" if value else ""

                        writer.writerow(exif_data)
                        extract_count += 1
                except Exception as e:
                    log(f"\n⚠️ 提取 {img_path.name} EXIF失败：{str(e)}")
                    continue

                # 更新进度
                if log_callback:
                    progress = int((idx + 1) / img_count * 100)
                    log(f"progress:{progress}")

    except PermissionError:
        log(f"\n❌ 无权限写入CSV文件：{output_csv}")
        return False
    except Exception as e:
        log(f"\n❌ CSV写入失败：{str(e)}")
        return False

    log(f"✅ EXIF提取完成，共处理 {extract_count} 张图片，结果已保存至：{output_csv}")
    return True


def batch_copy_move(dir_path, target_dir, mode="copy", exclude="", log_callback=None):
    """
    批量复制/移动文件（新增）
    :param dir_path: 源目录
    :param target_dir: 目标目录
    :param mode: copy(复制)/move(移动)
    :param exclude: 排除的扩展名（逗号分隔）
    :param log_callback: 日志回调
    """

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    file_list = [f for f in Path(dir_path).glob("*") if f.is_file()]
    if exclude:
        exclude_exts = [ext.strip() for ext in exclude.split(",")]
        file_list = [f for f in file_list if f.suffix.lstrip(".") not in exclude_exts]
    file_count = len(file_list)

    if file_count == 0:
        log(f"❌ 目录 {dir_path} 下未找到可处理的文件")
        return False

    target_path = Path(target_dir)
    target_path.mkdir(exist_ok=True, parents=True)
    process_count = 0

    log(f"📤 开始批量{mode}文件，共找到 {file_count} 个文件")
    for idx, file_path in enumerate(file_list):
        try:
            dest_path = target_path / file_path.name
            if dest_path.exists():
                # 重命名避免覆盖（加数字后缀）
                dest_path = target_path / f"{file_path.stem}_{int(time.time())}{file_path.suffix}"

            if mode == "copy":
                import shutil
                shutil.copy2(file_path, dest_path)
            else:  # move
                file_path.rename(dest_path)

            process_count += 1
        except PermissionError:
            log(f"\n⚠️ 无权限操作 {file_path.name}，请关闭该文件后重试")
        except Exception as e:
            log(f"\n⚠️ 处理 {file_path.name} 失败：{str(e)}")
            continue

        # 更新进度
        if log_callback:
            progress = int((idx + 1) / file_count * 100)
            log(f"progress:{progress}")

    log(f"✅ 批量{mode}完成，共处理 {process_count} 个文件，目标目录：{target_path.absolute()}")
    return True


# ===================== 线程类（扩展支持新增任务） =====================
class WorkerThread(QThread):
    """后台执行任务的线程，避免界面卡死"""
    log_signal = pyqtSignal(str)  # 日志信号
    progress_signal = pyqtSignal(int)  # 进度信号
    finish_signal = pyqtSignal(bool)  # 完成信号

    def __init__(self, task_type, params):
        super().__init__()
        self.task_type = task_type
        self.params = params

    def run(self):
        """执行具体任务"""

        def log_callback(msg):
            if msg.startswith("progress:"):
                # 解析进度值
                progress = int(msg.split(":")[1])
                self.progress_signal.emit(progress)
            else:
                self.log_signal.emit(msg)

        try:
            if self.task_type == "rename":
                result = batch_rename(
                    dir_path=self.params["dir"],
                    prefix=self.params["prefix"],
                    suffix=self.params["suffix"],
                    pattern=self.params["pattern"],
                    replace=self.params["replace"],
                    log_callback=log_callback
                )
            elif self.task_type == "convert_img":
                result = batch_convert_image(
                    dir_path=self.params["dir"],
                    to_format=self.params["to_format"],
                    log_callback=log_callback
                )
            elif self.task_type == "compress":
                result = batch_compress(
                    dir_path=self.params["dir"],
                    output=self.params["output"],
                    exclude=self.params["exclude"],
                    log_callback=log_callback
                )
            elif self.task_type == "classify":
                result = batch_classify(
                    dir_path=self.params["dir"],
                    mode=self.params["mode"],
                    log_callback=log_callback
                )
            elif self.task_type == "watermark":
                result = batch_watermark(
                    dir_path=self.params["dir"],
                    type_=self.params["type"],
                    content=self.params["content"],
                    font=self.params["font"],
                    size=self.params["size"],
                    color=self.params["color"],
                    opacity=self.params["opacity"],
                    watermark_path=self.params["watermark_path"],
                    log_callback=log_callback
                )
            # 新增任务类型
            elif self.task_type == "modify_time":
                result = batch_modify_file_time(
                    dir_path=self.params["dir"],
                    target_time=self.params["target_time"],
                    time_type=self.params["time_type"],
                    log_callback=log_callback
                )
            elif self.task_type == "extract_exif":
                result = batch_extract_exif(
                    dir_path=self.params["dir"],
                    output_csv=self.params["output_csv"],
                    log_callback=log_callback
                )
            elif self.task_type == "copy_move":
                result = batch_copy_move(
                    dir_path=self.params["dir"],
                    target_dir=self.params["target_dir"],
                    mode=self.params["mode"],
                    exclude=self.params["exclude"],
                    log_callback=log_callback
                )
            else:
                result = False
                self.log_signal.emit("❌ 不支持的任务类型")
            self.finish_signal.emit(result)
        except Exception as e:
            self.log_signal.emit(f"❌ 任务执行异常：{str(e)}")
            self.finish_signal.emit(False)


# ===================== 主界面类（扩展新增标签页） =====================
class FileToolMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        # 窗口基本设置
        self.setWindowTitle("文件批量处理工具 - PyQt5版")
        self.setGeometry(100, 100, 1000, 700)
        self.setFont(QFont("微软雅黑", 9))

        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 添加各功能标签页
        self.init_rename_tab()
        self.init_convert_img_tab()
        self.init_compress_tab()
        self.init_classify_tab()
        self.init_watermark_tab()
        # 新增标签页
        self.init_modify_time_tab()
        self.init_extract_exif_tab()
        self.init_copy_move_tab()

    # ===================== 标签页初始化 =====================
    def init_rename_tab(self):
        """批量重命名标签页"""
        tab = QWidget()
        self.tab_widget.addTab(tab, "批量重命名")

        # 布局
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 1. 目录选择
        dir_group = QGroupBox("目标目录")
        dir_layout = QHBoxLayout(dir_group)
        self.rename_dir_edit = QLineEdit()
        self.rename_dir_edit.setPlaceholderText("请选择要重命名的文件目录")
        dir_btn = QPushButton("选择目录")
        dir_btn.clicked.connect(lambda: self.select_dir(self.rename_dir_edit))
        dir_layout.addWidget(self.rename_dir_edit)
        dir_layout.addWidget(dir_btn)
        layout.addWidget(dir_group)

        # 2. 重命名参数
        param_group = QGroupBox("重命名参数")
        param_layout = QVBoxLayout(param_group)

        # 前缀
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel("文件名前缀："))
        self.rename_prefix_edit = QLineEdit()
        self.rename_prefix_edit.setPlaceholderText("例如：风景_")
        prefix_layout.addWidget(self.rename_prefix_edit)
        param_layout.addLayout(prefix_layout)

        # 后缀
        suffix_layout = QHBoxLayout()
        suffix_layout.addWidget(QLabel("文件名后缀："))
        self.rename_suffix_edit = QLineEdit()
        self.rename_suffix_edit.setPlaceholderText("例如：_高清")
        suffix_layout.addWidget(self.rename_suffix_edit)
        param_layout.addLayout(suffix_layout)

        # 正则替换
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel("正则匹配："))
        self.rename_pattern_edit = QLineEdit()
        self.rename_pattern_edit.setPlaceholderText(r"例如：img_(\d+)")
        pattern_layout.addWidget(self.rename_pattern_edit)
        param_layout.addLayout(pattern_layout)

        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("替换为："))
        self.rename_replace_edit = QLineEdit()
        self.rename_replace_edit.setPlaceholderText(r"例如：photo_\1")
        replace_layout.addWidget(self.rename_replace_edit)
        param_layout.addLayout(replace_layout)

        layout.addWidget(param_group)

        # 3. 执行按钮和进度条
        btn_layout = QHBoxLayout()
        self.rename_run_btn = QPushButton("开始重命名")
        self.rename_run_btn.clicked.connect(self.run_rename)
        btn_layout.addWidget(self.rename_run_btn)

        self.rename_progress = QProgressBar()
        self.rename_progress.setRange(0, 100)
        self.rename_progress.setValue(0)
        btn_layout.addWidget(self.rename_progress)
        layout.addLayout(btn_layout)

        # 4. 日志输出
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)
        self.rename_log_edit = QTextEdit()
        self.rename_log_edit.setReadOnly(True)
        log_layout.addWidget(self.rename_log_edit)
        layout.addWidget(log_group)

    def init_convert_img_tab(self):
        """图片格式转换标签页"""
        tab = QWidget()
        self.tab_widget.addTab(tab, "图片格式转换")

        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 目录选择
        dir_group = QGroupBox("图片目录")
        dir_layout = QHBoxLayout(dir_group)
        self.convert_dir_edit = QLineEdit()
        self.convert_dir_edit.setPlaceholderText("请选择要转换的图片目录")
        dir_btn = QPushButton("选择目录")
        dir_btn.clicked.connect(lambda: self.select_dir(self.convert_dir_edit))
        dir_layout.addWidget(self.convert_dir_edit)
        dir_layout.addWidget(dir_btn)
        layout.addWidget(dir_group)

        # 目标格式
        format_group = QGroupBox("转换参数")
        format_layout = QHBoxLayout(format_group)
        format_layout.addWidget(QLabel("目标格式："))
        self.convert_format_combo = QComboBox()
        self.convert_format_combo.addItems(["jpg", "png", "webp"])
        format_layout.addWidget(self.convert_format_combo)
        layout.addWidget(format_group)

        # 执行按钮和进度条
        btn_layout = QHBoxLayout()
        self.convert_run_btn = QPushButton("开始转换")
        self.convert_run_btn.clicked.connect(self.run_convert_img)
        btn_layout.addWidget(self.convert_run_btn)

        self.convert_progress = QProgressBar()
        self.convert_progress.setRange(0, 100)
        self.convert_progress.setValue(0)
        btn_layout.addWidget(self.convert_progress)
        layout.addLayout(btn_layout)

        # 日志输出
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)
        self.convert_log_edit = QTextEdit()
        self.convert_log_edit.setReadOnly(True)
        log_layout.addWidget(self.convert_log_edit)
        layout.addWidget(log_group)

    def init_compress_tab(self):
        """文件压缩标签页"""
        tab = QWidget()
        self.tab_widget.addTab(tab, "文件压缩")

        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 目录选择
        dir_group = QGroupBox("目标目录")
        dir_layout = QHBoxLayout(dir_group)
        self.compress_dir_edit = QLineEdit()
        self.compress_dir_edit.setPlaceholderText("请选择要压缩的文件目录")
        dir_btn = QPushButton("选择目录")
        dir_btn.clicked.connect(lambda: self.select_dir(self.compress_dir_edit))
        dir_layout.addWidget(self.compress_dir_edit)
        dir_layout.addWidget(dir_btn)
        layout.addWidget(dir_group)

        # 输出路径
        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout(output_group)

        output_layout1 = QHBoxLayout()
        output_layout1.addWidget(QLabel("压缩包路径："))
        self.compress_output_edit = QLineEdit()
        self.compress_output_edit.setPlaceholderText("默认：目录名_compressed.zip")
        output_btn = QPushButton("选择保存位置")
        output_btn.clicked.connect(lambda: self.select_save_file(self.compress_output_edit, "ZIP压缩包 (*.zip)"))
        output_layout1.addWidget(self.compress_output_edit)
        output_layout1.addWidget(output_btn)
        output_layout.addLayout(output_layout1)

        exclude_layout = QHBoxLayout()
        exclude_layout.addWidget(QLabel("排除扩展名："))
        self.compress_exclude_edit = QLineEdit()
        self.compress_exclude_edit.setPlaceholderText("例如：zip,log,tmp（逗号分隔）")
        exclude_layout.addWidget(self.compress_exclude_edit)
        output_layout.addLayout(exclude_layout)

        layout.addWidget(output_group)

        # 执行按钮和进度条
        btn_layout = QHBoxLayout()
        self.compress_run_btn = QPushButton("开始压缩")
        self.compress_run_btn.clicked.connect(self.run_compress)
        btn_layout.addWidget(self.compress_run_btn)

        self.compress_progress = QProgressBar()
        self.compress_progress.setRange(0, 100)
        self.compress_progress.setValue(0)
        btn_layout.addWidget(self.compress_progress)
        layout.addLayout(btn_layout)

        # 日志输出
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)
        self.compress_log_edit = QTextEdit()
        self.compress_log_edit.setReadOnly(True)
        log_layout.addWidget(self.compress_log_edit)
        layout.addWidget(log_group)

    def init_classify_tab(self):
        """文件分类标签页"""
        tab = QWidget()
        self.tab_widget.addTab(tab, "文件分类")

        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 目录选择
        dir_group = QGroupBox("目标目录")
        dir_layout = QHBoxLayout(dir_group)
        self.classify_dir_edit = QLineEdit()
        self.classify_dir_edit.setPlaceholderText("请选择要分类的文件目录")
        dir_btn = QPushButton("选择目录")
        dir_btn.clicked.connect(lambda: self.select_dir(self.classify_dir_edit))
        dir_layout.addWidget(self.classify_dir_edit)
        dir_layout.addWidget(dir_btn)
        layout.addWidget(dir_group)

        # 分类模式
        mode_group = QGroupBox("分类模式")
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.addWidget(QLabel("分类方式："))
        self.classify_mode_combo = QComboBox()
        self.classify_mode_combo.addItems(["ext（按扩展名）", "date（按创建日期）"])
        mode_layout.addWidget(self.classify_mode_combo)
        layout.addWidget(mode_group)

        # 执行按钮和进度条
        btn_layout = QHBoxLayout()
        self.classify_run_btn = QPushButton("开始分类")
        self.classify_run_btn.clicked.connect(self.run_classify)
        btn_layout.addWidget(self.classify_run_btn)

        self.classify_progress = QProgressBar()
        self.classify_progress.setRange(0, 100)
        self.classify_progress.setValue(0)
        btn_layout.addWidget(self.classify_progress)
        layout.addLayout(btn_layout)

        # 日志输出
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)
        self.classify_log_edit = QTextEdit()
        self.classify_log_edit.setReadOnly(True)
        log_layout.addWidget(self.classify_log_edit)
        layout.addWidget(log_group)

    def init_watermark_tab(self):
        """图片加水印标签页"""
        tab = QWidget()
        self.tab_widget.addTab(tab, "图片加水印")

        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 目录选择
        dir_group = QGroupBox("图片目录")
        dir_layout = QHBoxLayout(dir_group)
        self.watermark_dir_edit = QLineEdit()
        self.watermark_dir_edit.setPlaceholderText("请选择要加水印的图片目录")
        dir_btn = QPushButton("选择目录")
        dir_btn.clicked.connect(lambda: self.select_dir(self.watermark_dir_edit))
        dir_layout.addWidget(self.watermark_dir_edit)
        dir_layout.addWidget(dir_btn)
        layout.addWidget(dir_group)

        # 水印类型
        type_group = QGroupBox("水印类型")
        type_layout = QHBoxLayout(type_group)
        type_layout.addWidget(QLabel("水印类型："))
        self.watermark_type_combo = QComboBox()
        self.watermark_type_combo.addItems(["text（文字水印）", "image（图片水印）"])
        self.watermark_type_combo.currentTextChanged.connect(self.switch_watermark_type)
        type_layout.addWidget(self.watermark_type_combo)
        layout.addWidget(type_group)

        # ========== 修复点1：文字水印参数 ==========
        self.text_watermark_group = QGroupBox("文字水印参数")
        text_layout = QVBoxLayout(self.text_watermark_group)

        # 水印文字
        content_layout = QHBoxLayout()
        content_layout.addWidget(QLabel("水印文字："))
        self.watermark_content_edit = QLineEdit()
        self.watermark_content_edit.setPlaceholderText("例如：我的作品")
        content_layout.addWidget(self.watermark_content_edit)
        text_layout.addLayout(content_layout)

        # 字体文件
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("字体文件："))
        self.watermark_font_edit = QLineEdit()
        self.watermark_font_edit.setPlaceholderText("可选，默认字体")
        font_btn = QPushButton("选择字体")
        font_btn.clicked.connect(lambda: self.select_file(self.watermark_font_edit, "字体文件 (*.ttf *.otf)"))
        font_layout.addWidget(self.watermark_font_edit)
        font_layout.addWidget(font_btn)
        text_layout.addLayout(font_layout)

        # 文字大小 + 颜色（修复核心：每个addWidget只传一个控件，用addStretch()填充空白）
        size_color_layout = QHBoxLayout()
        # 文字大小部分
        size_color_layout.addWidget(QLabel("文字大小："))
        self.watermark_size_spin = QSpinBox()
        self.watermark_size_spin.setRange(8, 100)
        self.watermark_size_spin.setValue(24)
        size_color_layout.addWidget(self.watermark_size_spin)

        # 颜色部分（添加分隔，避免控件挤在一起）
        size_color_layout.addWidget(QLabel("  颜色(RGBA)："))
        self.watermark_color_edit = QLineEdit()
        self.watermark_color_edit.setPlaceholderText("例如：(255,255,255,128)")
        self.watermark_color_edit.setText("(255,255,255,128)")
        size_color_layout.addWidget(self.watermark_color_edit)

        # 填充空白（优化布局）
        size_color_layout.addStretch()
        text_layout.addLayout(size_color_layout)

        # 透明度
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("透明度："))
        self.watermark_opacity_spin = QSpinBox()
        self.watermark_opacity_spin.setRange(0, 255)
        self.watermark_opacity_spin.setValue(128)
        opacity_layout.addWidget(self.watermark_opacity_spin)
        opacity_layout.addStretch()
        text_layout.addLayout(opacity_layout)

        layout.addWidget(self.text_watermark_group)

        # ========== 修复点2：图片水印参数（统一布局规范） ==========
        self.image_watermark_group = QGroupBox("图片水印参数")
        image_layout = QVBoxLayout(self.image_watermark_group)
        self.image_watermark_group.setVisible(False)

        # 水印图片路径
        watermark_path_layout = QHBoxLayout()
        watermark_path_layout.addWidget(QLabel("水印图片："))
        self.watermark_path_edit = QLineEdit()
        self.watermark_path_edit.setPlaceholderText("请选择水印图片")
        watermark_path_btn = QPushButton("选择图片")
        watermark_path_btn.clicked.connect(
            lambda: self.select_file(self.watermark_path_edit, "图片文件 (*.png *.jpg *.webp)"))
        watermark_path_layout.addWidget(self.watermark_path_edit)
        watermark_path_layout.addWidget(watermark_path_btn)
        image_layout.addLayout(watermark_path_layout)

        # 水印尺寸 + 透明度（修复布局挤在一起的问题）
        img_size_opacity_layout = QHBoxLayout()
        img_size_opacity_layout.addWidget(QLabel("水印尺寸："))
        self.watermark_img_size_spin = QSpinBox()
        self.watermark_img_size_spin.setRange(10, 500)
        self.watermark_img_size_spin.setValue(50)
        img_size_opacity_layout.addWidget(self.watermark_img_size_spin)

        img_size_opacity_layout.addWidget(QLabel("  透明度："))
        self.watermark_img_opacity_spin = QSpinBox()
        self.watermark_img_opacity_spin.setRange(0, 255)
        self.watermark_img_opacity_spin.setValue(128)
        img_size_opacity_layout.addWidget(self.watermark_img_opacity_spin)
        img_size_opacity_layout.addStretch()
        image_layout.addLayout(img_size_opacity_layout)

        layout.addWidget(self.image_watermark_group)

        # 执行按钮和进度条
        btn_layout = QHBoxLayout()
        self.watermark_run_btn = QPushButton("开始加水印")
        self.watermark_run_btn.clicked.connect(self.run_watermark)
        btn_layout.addWidget(self.watermark_run_btn)

        self.watermark_progress = QProgressBar()
        self.watermark_progress.setRange(0, 100)
        self.watermark_progress.setValue(0)
        btn_layout.addWidget(self.watermark_progress)
        layout.addLayout(btn_layout)

        # 日志输出
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)
        self.watermark_log_edit = QTextEdit()
        self.watermark_log_edit.setReadOnly(True)
        log_layout.addWidget(self.watermark_log_edit)
        layout.addWidget(log_group)

    # ===================== 新增标签页初始化 =====================
    def init_modify_time_tab(self):
        """批量修改文件时间标签页（新增）"""
        tab = QWidget()
        self.tab_widget.addTab(tab, "批量修改文件时间")

        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 目录选择
        dir_group = QGroupBox("目标目录")
        dir_layout = QHBoxLayout(dir_group)
        self.modify_time_dir_edit = QLineEdit()
        self.modify_time_dir_edit.setPlaceholderText("请选择要修改时间的文件目录")
        dir_btn = QPushButton("选择目录")
        dir_btn.clicked.connect(lambda: self.select_dir(self.modify_time_dir_edit))
        dir_layout.addWidget(self.modify_time_dir_edit)
        dir_layout.addWidget(dir_btn)
        layout.addWidget(dir_group)

        # 时间设置
        time_group = QGroupBox("时间参数")
        time_layout = QVBoxLayout(time_group)

        # 目标时间
        time_layout1 = QHBoxLayout()
        time_layout1.addWidget(QLabel("目标时间："))
        self.modify_time_datetime = QDateTimeEdit()
        self.modify_time_datetime.setDateTime(QDateTime.currentDateTime())
        self.modify_time_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        time_layout1.addWidget(self.modify_time_datetime)
        time_layout1.addStretch()
        time_layout.addLayout(time_layout1)

        # 修改类型
        time_layout2 = QHBoxLayout()
        time_layout2.addWidget(QLabel("修改类型："))
        self.modify_time_type_combo = QComboBox()
        self.modify_time_type_combo.addItems(["both（创建+修改）", "create（仅创建）", "modify（仅修改）"])
        time_layout2.addWidget(self.modify_time_type_combo)
        time_layout2.addStretch()
        time_layout.addLayout(time_layout2)

        layout.addWidget(time_group)

        # 执行按钮和进度条
        btn_layout = QHBoxLayout()
        self.modify_time_run_btn = QPushButton("开始修改")
        self.modify_time_run_btn.clicked.connect(self.run_modify_time)
        btn_layout.addWidget(self.modify_time_run_btn)

        self.modify_time_progress = QProgressBar()
        self.modify_time_progress.setRange(0, 100)
        self.modify_time_progress.setValue(0)
        btn_layout.addWidget(self.modify_time_progress)
        layout.addLayout(btn_layout)

        # 日志输出
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)
        self.modify_time_log_edit = QTextEdit()
        self.modify_time_log_edit.setReadOnly(True)
        log_layout.addWidget(self.modify_time_log_edit)
        layout.addWidget(log_group)

    def init_extract_exif_tab(self):
        """提取图片EXIF信息标签页（新增）"""
        tab = QWidget()
        self.tab_widget.addTab(tab, "提取图片EXIF信息")

        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 目录选择
        dir_group = QGroupBox("图片目录")
        dir_layout = QHBoxLayout(dir_group)
        self.extract_exif_dir_edit = QLineEdit()
        self.extract_exif_dir_edit.setPlaceholderText("请选择要提取EXIF的图片目录")
        dir_btn = QPushButton("选择目录")
        dir_btn.clicked.connect(lambda: self.select_dir(self.extract_exif_dir_edit))
        dir_layout.addWidget(self.extract_exif_dir_edit)
        dir_layout.addWidget(dir_btn)
        layout.addWidget(dir_group)

        # 输出设置
        output_group = QGroupBox("输出设置")
        output_layout = QHBoxLayout(output_group)
        output_layout.addWidget(QLabel("CSV保存路径："))
        self.extract_exif_output_edit = QLineEdit()
        self.extract_exif_output_edit.setPlaceholderText("默认：目录名_exif.csv")
        output_btn = QPushButton("选择保存位置")
        output_btn.clicked.connect(lambda: self.select_save_file(self.extract_exif_output_edit, "CSV文件 (*.csv)"))
        output_layout.addWidget(self.extract_exif_output_edit)
        output_layout.addWidget(output_btn)
        layout.addWidget(output_group)

        # 执行按钮和进度条
        btn_layout = QHBoxLayout()
        self.extract_exif_run_btn = QPushButton("开始提取")
        self.extract_exif_run_btn.clicked.connect(self.run_extract_exif)
        btn_layout.addWidget(self.extract_exif_run_btn)

        self.extract_exif_progress = QProgressBar()
        self.extract_exif_progress.setRange(0, 100)
        self.extract_exif_progress.setValue(0)
        btn_layout.addWidget(self.extract_exif_progress)
        layout.addLayout(btn_layout)

        # 日志输出
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)
        self.extract_exif_log_edit = QTextEdit()
        self.extract_exif_log_edit.setReadOnly(True)
        log_layout.addWidget(self.extract_exif_log_edit)
        layout.addWidget(log_group)

    def init_copy_move_tab(self):
        """批量复制/移动文件标签页（新增）"""
        tab = QWidget()
        self.tab_widget.addTab(tab, "批量复制/移动文件")

        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 源目录
        src_group = QGroupBox("源目录")
        src_layout = QHBoxLayout(src_group)
        self.copy_move_src_edit = QLineEdit()
        self.copy_move_src_edit.setPlaceholderText("请选择要复制/移动的文件目录")
        src_btn = QPushButton("选择目录")
        src_btn.clicked.connect(lambda: self.select_dir(self.copy_move_src_edit))
        src_layout.addWidget(self.copy_move_src_edit)
        src_layout.addWidget(src_btn)
        layout.addWidget(src_group)

        # 目标目录
        dest_group = QGroupBox("目标目录")
        dest_layout = QHBoxLayout(dest_group)
        self.copy_move_dest_edit = QLineEdit()
        self.copy_move_dest_edit.setPlaceholderText("请选择目标目录")
        dest_btn = QPushButton("选择目录")
        dest_btn.clicked.connect(lambda: self.select_dir(self.copy_move_dest_edit))
        dest_layout.addWidget(self.copy_move_dest_edit)
        dest_layout.addWidget(dest_btn)
        layout.addWidget(dest_group)

        # 操作参数
        param_group = QGroupBox("操作参数")
        param_layout = QVBoxLayout(param_group)

        # 操作类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("操作类型："))
        self.copy_move_mode_combo = QComboBox()
        self.copy_move_mode_combo.addItems(["copy（复制）", "move（移动）"])
        type_layout.addWidget(self.copy_move_mode_combo)
        type_layout.addStretch()
        param_layout.addLayout(type_layout)

        # 排除扩展名
        exclude_layout = QHBoxLayout()
        exclude_layout.addWidget(QLabel("排除扩展名："))
        self.copy_move_exclude_edit = QLineEdit()
        self.copy_move_exclude_edit.setPlaceholderText("例如：zip,log,tmp（逗号分隔）")
        exclude_layout.addWidget(self.copy_move_exclude_edit)
        exclude_layout.addStretch()
        param_layout.addLayout(exclude_layout)

        layout.addWidget(param_group)

        # 执行按钮和进度条
        btn_layout = QHBoxLayout()
        self.copy_move_run_btn = QPushButton("开始执行")
        self.copy_move_run_btn.clicked.connect(self.run_copy_move)
        btn_layout.addWidget(self.copy_move_run_btn)

        self.copy_move_progress = QProgressBar()
        self.copy_move_progress.setRange(0, 100)
        self.copy_move_progress.setValue(0)
        btn_layout.addWidget(self.copy_move_progress)
        layout.addLayout(btn_layout)

        # 日志输出
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)
        self.copy_move_log_edit = QTextEdit()
        self.copy_move_log_edit.setReadOnly(True)
        log_layout.addWidget(self.copy_move_log_edit)
        layout.addWidget(log_group)

    # ===================== 通用工具函数（保留+适配） =====================
    def select_dir(self, line_edit):
        """选择目录并填充到输入框"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择目录")
        if dir_path:
            line_edit.setText(dir_path)

    def select_file(self, line_edit, filter_str):
        """选择文件并填充到输入框"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", filter_str)
        if file_path:
            line_edit.setText(file_path)

    def select_save_file(self, line_edit, filter_str):
        """选择保存文件路径"""
        file_path, _ = QFileDialog.getSaveFileName(self, "选择保存位置", "", filter_str)
        if file_path:
            line_edit.setText(file_path)

    def switch_watermark_type(self):
        """切换水印类型显示对应的参数面板"""
        if "text" in self.watermark_type_combo.currentText():
            self.text_watermark_group.setVisible(True)
            self.image_watermark_group.setVisible(False)
        else:
            self.text_watermark_group.setVisible(False)
            self.image_watermark_group.setVisible(True)

    def clear_log_and_progress(self, log_edit, progress_bar):
        """清空日志和进度条"""
        log_edit.clear()
        progress_bar.setValue(0)

    def append_log(self, log_edit, msg):
        """追加日志"""
        log_edit.append(msg)
        # 滚动到最后一行
        log_edit.moveCursor(log_edit.textCursor().End)

    # ===================== 任务执行函数 =====================
    def run_rename(self):
        """执行批量重命名"""
        # 严格校验目录
        dir_path = self.rename_dir_edit.text().strip()
        if not dir_path or not Path(dir_path).is_dir():
            QMessageBox.warning(self, "警告", "请选择**有效的本地目录**！")
            return

        # 清空日志和进度
        self.clear_log_and_progress(self.rename_log_edit, self.rename_progress)
        # 禁用按钮，防止重复点击
        self.rename_run_btn.setEnabled(False)

        # 构造参数（统一去除首尾空格，避免无效前缀/后缀）
        params = {
            "dir": dir_path,
            "prefix": self.rename_prefix_edit.text().strip(),
            "suffix": self.rename_suffix_edit.text().strip(),
            "pattern": self.rename_pattern_edit.text().strip(),
            "replace": self.rename_replace_edit.text().strip()
        }

        # 创建线程执行
        self.rename_thread = WorkerThread("rename", params)
        self.rename_thread.log_signal.connect(lambda msg: self.append_log(self.rename_log_edit, msg))
        self.rename_thread.progress_signal.connect(self.rename_progress.setValue)
        self.rename_thread.finish_signal.connect(lambda res: self.task_finish(res, self.rename_run_btn))
        self.rename_thread.start()

    def run_convert_img(self):
        """执行图片格式转换"""
        dir_path = self.convert_dir_edit.text().strip()
        if not dir_path or not Path(dir_path).exists():
            QMessageBox.warning(self, "警告", "请选择有效的图片目录！")
            return

        self.clear_log_and_progress(self.convert_log_edit, self.convert_progress)
        self.convert_run_btn.setEnabled(False)

        params = {
            "dir": dir_path,
            "to_format": self.convert_format_combo.currentText()
        }

        self.convert_thread = WorkerThread("convert_img", params)
        self.convert_thread.log_signal.connect(lambda msg: self.append_log(self.convert_log_edit, msg))
        self.convert_thread.progress_signal.connect(self.convert_progress.setValue)
        self.convert_thread.finish_signal.connect(lambda res: self.task_finish(res, self.convert_run_btn))
        self.convert_thread.start()

    def run_compress(self):
        """执行文件压缩"""
        dir_path = self.compress_dir_edit.text().strip()
        if not dir_path or not Path(dir_path).exists():
            QMessageBox.warning(self, "警告", "请选择有效的目标目录！")
            return

        self.clear_log_and_progress(self.compress_log_edit, self.compress_progress)
        self.compress_run_btn.setEnabled(False)

        params = {
            "dir": dir_path,
            "output": self.compress_output_edit.text().strip(),
            "exclude": self.compress_exclude_edit.text().strip()
        }

        self.compress_thread = WorkerThread("compress", params)
        self.compress_thread.log_signal.connect(lambda msg: self.append_log(self.compress_log_edit, msg))
        self.compress_thread.progress_signal.connect(self.compress_progress.setValue)
        self.compress_thread.finish_signal.connect(lambda res: self.task_finish(res, self.compress_run_btn))
        self.compress_thread.start()

    def run_classify(self):
        """执行文件分类"""
        dir_path = self.classify_dir_edit.text().strip()
        if not dir_path or not Path(dir_path).exists():
            QMessageBox.warning(self, "警告", "请选择有效的目标目录！")
            return

        self.clear_log_and_progress(self.classify_log_edit, self.classify_progress)
        self.classify_run_btn.setEnabled(False)

        # 解析分类模式
        mode_text = self.classify_mode_combo.currentText()
        mode = "ext" if "ext" in mode_text else "date"

        params = {
            "dir": dir_path,
            "mode": mode
        }

        self.classify_thread = WorkerThread("classify", params)
        self.classify_thread.log_signal.connect(lambda msg: self.append_log(self.classify_log_edit, msg))
        self.classify_thread.progress_signal.connect(self.classify_progress.setValue)
        self.classify_thread.finish_signal.connect(lambda res: self.task_finish(res, self.classify_run_btn))
        self.classify_thread.start()

    def run_watermark(self):
        """执行图片加水印"""
        dir_path = self.watermark_dir_edit.text().strip()
        if not dir_path or not Path(dir_path).exists():
            QMessageBox.warning(self, "警告", "请选择有效的图片目录！")
            return

        # 校验水印参数
        type_text = self.watermark_type_combo.currentText()
        if "text" in type_text and not self.watermark_content_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入文字水印内容！")
            return
        if "image" in type_text and not self.watermark_path_edit.text().strip():
            QMessageBox.warning(self, "警告", "请选择水印图片！")
            return

        self.clear_log_and_progress(self.watermark_log_edit, self.watermark_progress)
        self.watermark_run_btn.setEnabled(False)

        # 构造参数
        params = {
            "dir": dir_path,
            "type": "text" if "text" in type_text else "image",
            "content": self.watermark_content_edit.text().strip(),
            "font": self.watermark_font_edit.text().strip(),
            "size": self.watermark_size_spin.value() if "text" in type_text else self.watermark_img_size_spin.value(),
            "color": self.watermark_color_edit.text().strip(),
            "opacity": self.watermark_opacity_spin.value() if "text" in type_text else self.watermark_img_opacity_spin.value(),
            "watermark_path": self.watermark_path_edit.text().strip()
        }

        self.watermark_thread = WorkerThread("watermark", params)
        self.watermark_thread.log_signal.connect(lambda msg: self.append_log(self.watermark_log_edit, msg))
        self.watermark_thread.progress_signal.connect(self.watermark_progress.setValue)
        self.watermark_thread.finish_signal.connect(lambda res: self.task_finish(res, self.watermark_run_btn))
        self.watermark_thread.start()

    # ===================== 新增任务执行函数 =====================
    def run_modify_time(self):
        """执行批量修改文件时间"""
        dir_path = self.modify_time_dir_edit.text().strip()
        if not dir_path or not Path(dir_path).exists():
            QMessageBox.warning(self, "警告", "请选择有效的目标目录！")
            return

        self.clear_log_and_progress(self.modify_time_log_edit, self.modify_time_progress)
        self.modify_time_run_btn.setEnabled(False)

        # 解析参数
        target_time = self.modify_time_datetime.dateTime().toPyDateTime()
        time_type = self.modify_time_type_combo.currentText().split("（")[0]

        params = {
            "dir": dir_path,
            "target_time": target_time,
            "time_type": time_type
        }

        self.modify_time_thread = WorkerThread("modify_time", params)
        self.modify_time_thread.log_signal.connect(lambda msg: self.append_log(self.modify_time_log_edit, msg))
        self.modify_time_thread.progress_signal.connect(self.modify_time_progress.setValue)
        self.modify_time_thread.finish_signal.connect(lambda res: self.task_finish(res, self.modify_time_run_btn))
        self.modify_time_thread.start()

    def run_extract_exif(self):
        """执行提取EXIF信息"""
        dir_path = self.extract_exif_dir_edit.text().strip()
        if not dir_path or not Path(dir_path).exists():
            QMessageBox.warning(self, "警告", "请选择有效的图片目录！")
            return

        # 处理默认输出路径
        output_csv = self.extract_exif_output_edit.text().strip()
        if not output_csv:
            output_csv = f"{dir_path}_exif.csv"

        self.clear_log_and_progress(self.extract_exif_log_edit, self.extract_exif_progress)
        self.extract_exif_run_btn.setEnabled(False)

        params = {
            "dir": dir_path,
            "output_csv": output_csv
        }

        self.extract_exif_thread = WorkerThread("extract_exif", params)
        self.extract_exif_thread.log_signal.connect(lambda msg: self.append_log(self.extract_exif_log_edit, msg))
        self.extract_exif_thread.progress_signal.connect(self.extract_exif_progress.setValue)
        self.extract_exif_thread.finish_signal.connect(lambda res: self.task_finish(res, self.extract_exif_run_btn))
        self.extract_exif_thread.start()

    def run_copy_move(self):
        """执行批量复制/移动文件"""
        src_dir = self.copy_move_src_edit.text().strip()
        dest_dir = self.copy_move_dest_edit.text().strip()
        if not src_dir or not Path(src_dir).exists():
            QMessageBox.warning(self, "警告", "请选择有效的源目录！")
            return
        if not dest_dir:
            QMessageBox.warning(self, "警告", "请选择有效的目标目录！")
            return

        self.clear_log_and_progress(self.copy_move_log_edit, self.copy_move_progress)
        self.copy_move_run_btn.setEnabled(False)

        # 解析参数
        mode = self.copy_move_mode_combo.currentText().split("（")[0]
        exclude = self.copy_move_exclude_edit.text().strip()

        params = {
            "dir": src_dir,
            "target_dir": dest_dir,
            "mode": mode,
            "exclude": exclude
        }

        self.copy_move_thread = WorkerThread("copy_move", params)
        self.copy_move_thread.log_signal.connect(lambda msg: self.append_log(self.copy_move_log_edit, msg))
        self.copy_move_thread.progress_signal.connect(self.copy_move_progress.setValue)
        self.copy_move_thread.finish_signal.connect(lambda res: self.task_finish(res, self.copy_move_run_btn))
        self.copy_move_thread.start()

    def task_finish(self, result, btn):
        """任务完成后启用按钮并提示"""
        btn.setEnabled(True)
        if result:
            QMessageBox.information(self, "成功", "任务执行完成！")
        else:
            QMessageBox.critical(self, "失败", "任务执行失败，请查看日志！")


# ===================== 程序入口 =====================
if __name__ == "__main__":
    # 解决高DPI显示问题
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    window = FileToolMainWindow()
    window.show()
    sys.exit(app.exec_())