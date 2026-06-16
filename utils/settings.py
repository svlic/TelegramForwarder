import os
import logging

from utils.file_creator import create_default_configs

logger = logging.getLogger(__name__)
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')


def _load_config_lines(filename, warning_message):
    file_path = os.path.join(CONFIG_DIR, filename)
    try:
        if not os.path.exists(file_path):
            create_default_configs()

        with open(file_path, 'r', encoding='utf-8') as file:
            lines = [line.strip() for line in file if line.strip()]
            if lines:
                return lines
    except (FileNotFoundError, IOError) as error:
        logger.warning(f"{filename} 加载失败: {error}，{warning_message}")

    return None


def load_summary_times():
    """加载总结时间列表"""
    return _load_config_lines('summary_times.txt', '使用默认时间列表') or ['00:00', '06:00', '12:00', '18:00']


def load_delay_times():
    """加载延迟时间列表"""
    return _load_config_lines('delay_times.txt', '使用默认时间列表') or [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def load_max_media_size():
    """加载媒体大小限制"""
    return _load_config_lines('max_media_size.txt', '使用默认大小限制') or [5, 10, 15, 20, 50, 100, 200, 300, 500, 1024, 2048]


def load_media_extensions():
    """加载媒体扩展名"""
    return _load_config_lines('media_extensions.txt', '使用默认扩展名') or ['无扩展名', 'txt', 'jpg', 'png', 'gif', 'mp4', 'mp3', 'wav', 'ogg', 'flac', 'aac', 'wma', 'm4a', 'm4v', 'mov', 'avi', 'mkv', 'webm', 'mpg', 'mpeg', 'mpe', 'mp2', 'mpc', 'oga', '3gp', '3g2', '3gpp', '3gpp2', 'amr', 'awb', 'caf', 'm4b', 'm4p', 'm4r', 'opus', 'spx', 'vorbis', 'ac3', 'dts', 'dtshd']
