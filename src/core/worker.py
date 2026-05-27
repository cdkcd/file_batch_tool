from PyQt5.QtCore import QThread, pyqtSignal
from src.utils.file_operations import (
    batch_rename, batch_convert_image, batch_compress,
    batch_classify, batch_watermark, batch_modify_file_time,
    batch_extract_exif, batch_copy_move
)


class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finish_signal = pyqtSignal(bool)

    def __init__(self, task_type, params):
        super().__init__()
        self.task_type = task_type
        self.params = params

    def run(self):
        def log_callback(msg):
            if msg.startswith("progress:"):
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
                    find_str=self.params["find_str"],
                    replace_str=self.params["replace_str"],
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