"""
停止标志模块
用于在翻译工作流中传递停止信号
当用户点击"停止"按钮时，所有相关模块能够检测到并优雅地终止
"""

import threading
from typing import Optional, Callable


class StopFlag:
    """
    线程安全的停止标志类

    用于在多线程环境中传递停止信号。
    当用户请求停止时，所有检查此标志的代码都应该优雅地终止。

    使用示例:
        stop_flag = StopFlag()

        # 在工作线程中检查
        if stop_flag.is_stop_requested():
            return None

        # 在GUI中设置停止标志
        stop_flag.request_stop()
    """

    def __init__(self):
        """初始化停止标志"""
        self._stop_requested = False
        self._lock = threading.Lock()

    def request_stop(self) -> None:
        """请求停止（线程安全）"""
        with self._lock:
            self._stop_requested = True

    def is_stop_requested(self) -> bool:
        """
        检查是否已请求停止（线程安全）

        Returns:
            bool: True表示已请求停止，False表示未请求停止
        """
        with self._lock:
            return self._stop_requested

    def reset(self) -> None:
        """重置停止标志（线程安全）"""
        with self._lock:
            self._stop_requested = False

    def __bool__(self) -> bool:
        """支持直接布尔判断"""
        return self.is_stop_requested()


class StopFlagHolder:
    """
    停止标志持有者基类

    为需要检查停止标志的类提供统一的接口。
    子类可以通过重写 _check_stop() 方法来实现自定义的停止检查逻辑。

    使用示例:
        class MyProcessor(StopFlagHolder):
            def process(self):
                # 长时间操作前检查
                if self._check_stop():
                    return None

                # 执行操作...

                # 长时间操作后检查
                if self._check_stop():
                    return None

                return result
    """

    def __init__(self, stop_flag: Optional[StopFlag] = None):
        """
        初始化停止标志持有者

        Args:
            stop_flag: 停止标志对象，如果为None则创建一个默认的标志
        """
        self._stop_flag = stop_flag if stop_flag is not None else StopFlag()

    def set_stop_flag(self, stop_flag: StopFlag) -> None:
        """
        设置停止标志

        Args:
            stop_flag: 停止标志对象
        """
        self._stop_flag = stop_flag

    def get_stop_flag(self) -> StopFlag:
        """
        获取停止标志

        Returns:
            StopFlag: 停止标志对象
        """
        return self._stop_flag

    def _check_stop(self, on_stop_callback: Optional[Callable[[], None]] = None) -> bool:
        """
        检查是否已请求停止

        Args:
            on_stop_callback: 当检测到停止时执行的回调函数

        Returns:
            bool: True表示已请求停止，False表示未请求停止
        """
        if self._stop_flag.is_stop_requested():
            if on_stop_callback:
                on_stop_callback()
            return True
        return False

    def request_stop(self) -> None:
        """请求停止"""
        self._stop_flag.request_stop()

    def reset_stop_flag(self) -> None:
        """重置停止标志"""
        self._stop_flag.reset()
