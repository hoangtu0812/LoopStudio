"""
Logger - Sử dụng logging thay vì print.
Cấu hình format chuẩn, dễ debug.
"""
import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Tạo logger với format chuẩn."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger
