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
"""

import os
import sys
import re
import argparse
import zipfile
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from PIL import Image, ImageDraw, ImageFont

# 解决PIL处理大图片的DecompressionBombWarning
Image.MAX_IMAGE_PIXELS = None

# --- 批量重命名 ---
def batch_rename(args):
    file_list = [f for f in Path(args.dir).glob("*") if f.is_file()]
    if not file_list:
        print(f"❌ 目录 {args.dir} 下未找到文件")
        return

    pattern = re.compile(args.pattern) if args.pattern else None
    rename_count = 0

    print(f"📝 开始批量重命名，共找到 {len(file_list)} 个文件")
    for file_path in tqdm(file_list):
        old_name = file_path.name
        new_name = old_name

        if pattern:
            new_name = pattern.sub(args.replace, new_name)
        if args.prefix:
            new_name = args.prefix + new_name
        if args.suffix:
            name, ext = os.path.splitext(new_name)
            new_name = f"{name}{args.suffix}{ext}"

        if new_name == old_name:
            continue

        new_path = file_path.parent / new_name
        if new_path.exists():
            print(f"\n⚠️ 文件 {new_path} 已存在，跳过")
            continue

        file_path.rename(new_path)
        rename_count += 1

    print(f"✅ 重命名完成，共处理 {rename_count} 个文件")

# --- 批量转换图片格式（终极修复版）---
def batch_convert_image(args):
    """批量转换图片格式（全兼容版）"""
    # 支持的图片格式
    SUPPORT_FORMATS = ["jpg", "jpeg", "png", "webp"]
    # 目标格式统一为小写
    target_format = args.to_format.lower()
    
    # 获取目标目录下的图片文件
    img_list = []
    for ext in SUPPORT_FORMATS:
        img_list.extend(Path(args.dir).glob(f"*.{ext}"))
        img_list.extend(Path(args.dir).glob(f"*.{ext.upper()}"))  # 兼容大写扩展名
    img_list = [f for f in img_list if f.is_file()]

    if not img_list:
        print(f"❌ 目录 {args.dir} 下未找到支持的图片文件（{SUPPORT_FORMATS}）")
        return

    convert_count = 0
    print(f"🖼️ 开始批量转换图片格式，共找到 {len(img_list)/2} 张图片")
    
    for img_path in tqdm(img_list):
        try:
            # 打开图片并处理模式
            with Image.open(img_path) as img:
                # 1. 处理JPG不支持透明通道的问题
                if target_format in ["jpg", "jpeg"]:
                    # 转换为RGB模式，透明区域填充白色
                    if img.mode in ("RGBA", "P"):
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        # 处理mask兼容问题
                        mask = img.split()[-1] if img.mode == "RGBA" else None
                        bg.paste(img, (0, 0), mask)
                        img = bg
                    else:
                        img = img.convert("RGB")
                else:
                    # PNG/WebP保留透明通道
                    img = img.convert("RGBA") if img.mode != "RGBA" else img

                # 2. 拼接新文件名（避免重复）
                new_name = f"{img_path.stem}_converted.{target_format}"
                new_path = img_path.parent / new_name
                
                # 3. 兼容Pillow的格式参数
                format_map = {
                    "jpg": "JPEG",
                    "jpeg": "JPEG",
                    "png": "PNG",
                    "webp": "WEBP"
                }
                save_format = format_map.get(target_format, target_format.upper())

                # 4. 保存图片（处理权限问题）
                img.save(new_path, save_format, quality=95)
                convert_count += 1
                
        except PermissionError:
            print(f"\n⚠️ 无权限写入 {new_path}，请关闭该文件后重试")
        except Exception as e:
            print(f"\n⚠️ 处理 {img_path.name} 失败：{str(e)}")
            continue

    print(f"✅ 图片转换完成，共成功处理 {convert_count/2} 张图片")

# --- 批量压缩文件 ---
def batch_compress(args):
    file_list = [f for f in Path(args.dir).glob("*") if f.is_file()]
    if args.exclude:
        exclude_exts = [ext.strip() for ext in args.exclude.split(",")]
        file_list = [f for f in file_list if f.suffix.lstrip(".") not in exclude_exts]

    if not file_list:
        print(f"❌ 目录 {args.dir} 下未找到可压缩的文件")
        return

    zip_name = args.output if args.output else f"{args.dir}_compressed.zip"
    zip_path = Path(zip_name)
    if zip_path.exists():
        print(f"❌ ZIP包 {zip_path} 已存在，请更换输出文件名")
        return

    print(f"📦 开始批量压缩文件，共找到 {len(file_list)} 个文件")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in tqdm(file_list):
            zipf.write(file_path, arcname=file_path.name)

    print(f"✅ 压缩完成！ZIP包已保存至：{zip_path.absolute()}")

# --- 批量文件分类 ---
def batch_classify(args):
    file_list = [f for f in Path(args.dir).glob("*") if f.is_file()]
    if not file_list:
        print(f"❌ 目录 {args.dir} 下无文件")
        return

    classify_dir = Path(args.dir) / "classified"
    classify_dir.mkdir(exist_ok=True)
    count = 0

    print(f"📂 开始批量分类，共 {len(file_list)} 个文件")
    for file_path in tqdm(file_list):
        if args.mode == "ext":
            ext = file_path.suffix.lstrip(".").lower() or "no_ext"
            target_dir = classify_dir / ext
        elif args.mode == "date":
            ctime = datetime.fromtimestamp(file_path.stat().st_ctime)
            date_str = ctime.strftime("%Y-%m")
            target_dir = classify_dir / date_str
        else:
            print(f"⚠️ 不支持的分类模式：{args.mode}")
            return

        target_dir.mkdir(exist_ok=True)
        try:
            file_path.rename(target_dir / file_path.name)
            count += 1
        except Exception as e:
            print(f"\n⚠️ 移动 {file_path.name} 失败：{str(e)}")
            continue

    print(f"✅ 分类完成，共处理 {count} 个文件，已归档至 {classify_dir}")

# --- 图片批量加水印 ---
def batch_watermark(args):
    SUPPORT_FORMATS = ["jpg", "jpeg", "png", "webp"]
    img_list = []
    for ext in SUPPORT_FORMATS:
        img_list.extend(Path(args.dir).glob(f"*.{ext}"))
    img_list = [f for f in img_list if f.is_file()]

    if not img_list:
        print(f"❌ 目录 {args.dir} 下无支持的图片")
        return

    count = 0
    print(f"🔖 开始批量添加水印，共 {len(img_list)} 张图片")

    if args.type == "text":
        color = eval(args.color) if args.color else (255, 255, 255, 128)
        try:
            font = ImageFont.truetype(args.font, args.size) if args.font else ImageFont.load_default()
        except:
            font = ImageFont.load_default()
    elif args.type == "image":
        try:
            watermark_img = Image.open(args.watermark_path).convert("RGBA")
            watermark_img = watermark_img.resize((args.size, args.size), Image.Resampling.LANCZOS)
            alpha = watermark_img.split()[3]
            alpha = alpha.point(lambda p: p * args.opacity / 255)
            watermark_img.putalpha(alpha)
        except Exception as e:
            print(f"❌ 加载图片水印失败：{str(e)}")
            return
    else:
        print(f"⚠️ 不支持的水印类型：{args.type}")
        return

    for img_path in tqdm(img_list):
        try:
            img = Image.open(img_path).convert("RGBA")
            draw = ImageDraw.Draw(img)
            width, height = img.size

            if args.type == "text":
                text_bbox = draw.textbbox((0, 0), args.content, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                pos = (width - text_width - 20, height - text_height - 20)
                draw.text(pos, args.content, font=font, fill=color)
            elif args.type == "image":
                pos = (width - args.size - 20, height - args.size - 20)
                img.paste(watermark_img, pos, mask=watermark_img)

            new_path = img_path.parent / f"watermarked_{img_path.name}"
            if img_path.suffix.lower() in (".jpg", ".jpeg"):
                img.convert("RGB").save(new_path, "JPEG")
            else:
                img.save(new_path, img_path.suffix[1:].upper())
            count += 1
        except Exception as e:
            print(f"\n⚠️ 处理 {img_path.name} 失败：{str(e)}")
            continue

    print(f"✅ 水印添加完成，共处理 {count} 张图片")


# ========== 子命令帮助说明（核心：自定义子命令解释） ==========
SUBCOMMAND_HELP = {
    "总帮助": """
📁 文件批量处理工具 - 使用手册
========================================
【核心功能】：批量处理文件/图片，支持重命名、格式转换、压缩、分类、加水印
【使用方式】：输入 子命令 + 参数 即可执行，示例：rename -d D:\照片 --prefix 风景_
【支持子命令】：
  1. rename      - 批量重命名文件（支持前缀/后缀/正则替换）
  2. convert-img - 批量转换图片格式（jpg/png/webp互转）
  3. compress    - 批量压缩文件为ZIP（支持排除指定扩展名）
  4. classify    - 批量分类文件（按扩展名/创建日期）
  5. watermark   - 批量添加图片水印（文字/图片水印）
【辅助指令】：
  - -h/help              查看总帮助
  - 子命令 -h            查看指定子命令的详细用法（如 rename -h）
  - exit/quit            退出工具
""",
    "rename": """
🔧 子命令：rename（批量重命名文件）
========================================
【功能】：给指定目录下的文件批量加前缀/后缀，或通过正则替换文件名
【使用场景】：整理照片、文档，统一文件名格式
【必选参数】：-d/--dir 目标目录（如 -d D:\旅行照片）
【可选参数】：
  --prefix   文件名前缀（如 --prefix 2024_）
  --suffix   文件名后缀（如 --suffix _高清）
  -p/--pattern  正则匹配模式（如 -p 'img_(\\d+)'）
  -r/--replace  正则替换内容（如 -r 'photo_\\1'）
【完整示例】：
  1. 简单加前缀：rename -d D:\照片 --prefix 风景_
  2. 加后缀：rename -d D:\文档 --suffix _v1
  3. 正则替换：rename -d D:\截图 -p '截图(\\d+)' -r 'screenshot_\\1'
""",
    "convert-img": """
🔧 子命令：convert-img（批量转换图片格式）
========================================
【功能】：将指定目录下的所有图片转换为目标格式（jpg/png/webp）
【使用场景】：图片格式统一、减小图片体积（webp格式）
【必选参数】：
  -d/--dir       图片目录（如 -d D:\手机照片）
  -f/--to-format 目标格式（如 -f png）
【完整示例】：
  1. 转PNG格式：convert-img -d D:\jpg图片 -f png
  2. 转WebP格式：convert-img -d D:\照片 -f webp
""",
    "compress": """
🔧 子命令：compress（批量压缩文件为ZIP）
========================================
【功能】：将指定目录下的文件压缩为ZIP包，支持排除指定扩展名文件
【使用场景】：打包文件、节省存储空间
【必选参数】：-d/--dir 目标目录（如 -d D:\待压缩文件）
【可选参数】：
  -o/--output  压缩包保存路径（如 -o D:\压缩包.zip，默认：目录名_compressed.zip）
  --exclude    排除的扩展名（逗号分隔，如 --exclude zip,log,tmp）
【完整示例】：
  1. 基础压缩：compress -d D:\工作文件
  2. 指定输出名：compress -d D:\照片 -o 2024旅行照片.zip
  3. 排除指定文件：compress -d D:\下载 --exclude zip,exe
""",
    "classify": """
🔧 子命令：classify（批量分类文件）
========================================
【功能】：按扩展名/创建日期将文件分类到不同子文件夹
【使用场景】：整理杂乱的下载文件夹、桌面文件
【必选参数】：
  -d/--dir  目标目录（如 -d D:\下载）
  -m/--mode 分类模式（ext=按扩展名，date=按创建日期）
【完整示例】：
  1. 按扩展名分类：classify -d D:\杂乱文件 -m ext
     → 会生成：txt文件/、jpg文件/、exe文件/ 等子文件夹
  2. 按日期分类：classify -d D:\照片 -m date
     → 会生成：2024-01/、2024-02/ 等子文件夹
""",
    "watermark": """
🔧 子命令：watermark（批量添加图片水印）
========================================
【功能】：给指定目录下的所有图片添加文字/图片水印
【使用场景】：图片版权保护、添加标识
【必选参数】：
  -d/--dir    图片目录（如 -d D:\作品图片）
  -t/--type   水印类型（text=文字水印，image=图片水印）
【可选参数（text类型）】：
  -c/--content  水印文字（如 -c 我的作品）
  -s/--size     文字大小（默认24，如 -s 32）
  -color        文字颜色（RGBA，默认(255,255,255,128)）
  -o/--opacity  透明度（0-255，默认128）
【可选参数（image类型）】：
  -w/--watermark-path  水印图片路径（如 -w D:\水印.png）
  -s/--size            水印图片尺寸（默认24）
  -o/--opacity         透明度（0-255，默认128）
【完整示例】：
  1. 文字水印：watermark -d D:\图片 -t text -c 原创作品 -s 32
  2. 图片水印：watermark -d D:\图片 -t image -w D:\logo.png -o 100
"""
}

# ========== 主函数 ==========
def parse_command(args_list):
    """仅解析子命令和参数，不处理-h，交给交互式逻辑统一处理"""
    parser = argparse.ArgumentParser(add_help=False)
    subparsers = parser.add_subparsers(dest="command")

    # 仅定义参数结构，不处理任何help
    parser_rename = subparsers.add_parser("rename", add_help=False)
    parser_rename.add_argument("-d", "--dir")
    parser_rename.add_argument("-p", "--pattern")
    parser_rename.add_argument("-r", "--replace")
    parser_rename.add_argument("--prefix")
    parser_rename.add_argument("--suffix")
    parser_rename.add_argument("-h", "--help", action="store_true")  # 仅标记，不处理

    parser_img = subparsers.add_parser("convert-img", add_help=False)
    parser_img.add_argument("-d", "--dir")
    parser_img.add_argument("-f", "--to-format")
    parser_img.add_argument("-h", "--help", action="store_true")

    parser_zip = subparsers.add_parser("compress", add_help=False)
    parser_zip.add_argument("-d", "--dir")
    parser_zip.add_argument("-o", "--output")
    parser_zip.add_argument("--exclude")
    parser_zip.add_argument("-h", "--help", action="store_true")

    parser_classify = subparsers.add_parser("classify", add_help=False)
    parser_classify.add_argument("-d", "--dir")
    parser_classify.add_argument("-m", "--mode")
    parser_classify.add_argument("-h", "--help", action="store_true")

    parser_watermark = subparsers.add_parser("watermark", add_help=False)
    parser_watermark.add_argument("-d", "--dir")
    parser_watermark.add_argument("-t", "--type")
    parser_watermark.add_argument("-c", "--content")
    parser_watermark.add_argument("-f", "--font")
    parser_watermark.add_argument("-s", "--size", type=int)
    parser_watermark.add_argument("-color")
    parser_watermark.add_argument("-o", "--opacity", type=int)
    parser_watermark.add_argument("-w", "--watermark-path")
    parser_watermark.add_argument("-h", "--help", action="store_true")

    try:
        args = parser.parse_args(args_list)
        return args
    except:
        return None

# ========== 执行功能函数 ==========
def execute_command(args):
    """执行实际功能，参数校验"""
    if not args.command:
        print(SUBCOMMAND_HELP["总帮助"])
        return

    # 基础路径校验
    if hasattr(args, "dir") and args.dir and not Path(args.dir).exists():
        print(f"❌ 目录 {args.dir} 不存在")
        return

    # 水印参数校验
    if args.command == "watermark":
        if args.type == "text" and not args.content:
            print(f"❌ 请指定文字水印内容：-c 你的水印文字")
            return
        if args.type == "image" and not args.watermark_path:
            print(f"❌ 请指定图片水印路径：-w 你的水印图片路径")
            return

    # 执行功能
    try:
        if args.command == "rename":
            batch_rename(args)
        elif args.command == "convert-img":
            batch_convert_image(args)
        elif args.command == "compress":
            batch_compress(args)
        elif args.command == "classify":
            batch_classify(args)
        elif args.command == "watermark":
            batch_watermark(args)
        print("\n✅ 执行完成！")
    except Exception as e:
        print(f"\n❌ 执行失败：{str(e)}")

# ========== 交互式模式（核心：统一输出自定义帮助解释） ==========
def interactive_mode():
    """交互式模式：所有帮助指令均输出自定义的子命令解释"""
    print("=" * 60)
    print("        📁 文件批量处理工具 - 交互式模式        ")
    print("=" * 60)
    print("💡 指令说明：")
    print("   → help / -h           查看总帮助（自定义解释）")
    print("   → help 子命令 / 子命令 -h  查看子命令详细解释（如 help rename 或 rename -h）")
    print("   → exit/quit           退出工具")
    print("=" * 60 + "\n")

    while True:
        user_input = input(">>> ").strip()
        if not user_input:
            continue

        # 退出指令
        if user_input.lower() in ["exit", "quit"]:
            print("\n👋 感谢使用，再见！")
            sys.exit(0)

        input_parts = user_input.split()
        target_subcmd = None
        is_help_cmd = False

        # ========== 统一识别所有帮助指令 ==========
        # 情况1：单独输入 -h/--help/help → 总帮助
        if len(input_parts) == 1 and input_parts[0].lower() in ["-h", "--help", "help"]:
            is_help_cmd = True
        # 情况2：help 子命令（如 help rename）→ 子命令帮助
        elif input_parts[0].lower() == "help" and len(input_parts) >= 2:
            is_help_cmd = True
            target_subcmd = input_parts[1]
        # 情况3：子命令 -h（如 rename -h）→ 子命令帮助
        else:
            args = parse_command(input_parts)
            if args and hasattr(args, "help") and args.help:
                is_help_cmd = True
                target_subcmd = args.command

        # ========== 处理帮助指令（输出自定义解释） ==========
        if is_help_cmd:
            # 显示指定子命令的自定义解释
            if target_subcmd and target_subcmd in SUBCOMMAND_HELP:
                print(SUBCOMMAND_HELP[target_subcmd])
            # 子命令不存在的提示
            elif target_subcmd and target_subcmd not in SUBCOMMAND_HELP:
                print(f"❌ 不支持的子命令：{target_subcmd}")
                print(f"✅ 支持的子命令：rename/convert-img/compress/classify/watermark")
            # 显示总帮助
            else:
                print(SUBCOMMAND_HELP["总帮助"])
            print("\n" + "-" * 60 + "\n")
            continue

        # ========== 执行普通命令 ==========
        args = parse_command(input_parts)
        if args:
            execute_command(args)
        else:
            print(f"\n❌ 命令格式错误！输入 help 或 -h 查看帮助")
        print("\n" + "-" * 60 + "\n")

# ========== 程序入口 ==========
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 命令行模式：同样输出自定义帮助解释
        args = parse_command(sys.argv[1:])
        if args and hasattr(args, "help") and args.help:
            if args.command in SUBCOMMAND_HELP:
                print(SUBCOMMAND_HELP[args.command])
            else:
                print(SUBCOMMAND_HELP["总帮助"])
        else:
            execute_command(args)
    else:
        # 双击exe：进入交互式模式
        interactive_mode()