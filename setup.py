from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="file-batch-tool",
    version="1.1.0",
    author="the-life",
    author_email="3331648097@qq.com",
    description="轻量文件批量处理工具，支持重命名、图片转换、压缩、分类、加水印等",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitee.com/the-life/file_batch_tool",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "Pillow>=10.0.0",
        "PyQt5>=5.15.0",
    ],
    entry_points={
        "console_scripts": [
            "file-batch-tool=file_batch_tool.main_window:run"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
    keywords=["file batch", "rename", "image convert", "watermark", "compress"],
    zip_safe=False,
)