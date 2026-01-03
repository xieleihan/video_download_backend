import os
import uuid
import re
from pathlib import Path
from typing import Tuple
import logging
from enum import Enum
from time import sleep

try:
    from yt_dlp import YoutubeDL
except ImportError:
    YoutubeDL = None

logger = logging.getLogger(__name__)


class VideoType(str, Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    TWITTER = "twitter"


def download_video(video_url: str, video_type: str) -> Tuple[str, str]:
    """
    下载视频文件
    
    Args:
        video_url: 视频链接
        video_type: 视频类型 (youtube/tiktok/twitter)
        
    Returns:
        Tuple[视频文件路径, 文件扩展名]
    """
    try:
        video_type = VideoType(video_type.lower())
    except ValueError:
        raise ValueError(f"不支持的视频类型: {video_type}")
    
    # 创建目标目录
    temp_dir = Path(__file__).parent.parent / "temp" / video_type.value
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取视频标题
    video_title = _get_video_title(video_url)
    # 清理标题中的非法文件名字符
    safe_title = _sanitize_filename(video_title)
    # 生成唯一文件名：title_uuid的前8位
    uuid_short = str(uuid.uuid4())[:8]
    file_id = f"{safe_title}_{uuid_short}"
    
    if video_type == VideoType.YOUTUBE:
        return _download_youtube(video_url, temp_dir, file_id)
    elif video_type == VideoType.TIKTOK:
        return _download_tiktok(video_url, temp_dir, file_id)
    elif video_type == VideoType.TWITTER:
        return _download_twitter(video_url, temp_dir, file_id)


def _download_youtube(video_url: str, temp_dir: Path, file_id: str) -> Tuple[str, str]:
    """下载 YouTube 视频 (1080p 有声音)"""
    if YoutubeDL is None:
        raise RuntimeError("yt-dlp 未安装，请运行: pip install yt-dlp")
    
    output_template = str(temp_dir / file_id) + ".%(ext)s"
    
    ydl_opts = {
        'format': 'bestvideo[height>=1080][ext=mp4]+bestaudio[ext=m4a]/best[height>=1080]/best',
        'merge_output_format': 'mp4',
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': False,
        'socket_timeout': 60,  # 增加超时到 60 秒
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        'retries': 3,  # 添加重试机制
        'fragment_retries': 3,
        'skip_unavailable_fragments': True,  # 跳过不可用的分片
        'extractor_args': {
            'youtube': {
                'skip': ['webpage']  # 跳过网页信息获取，加速
            }
        },
        'socket_timeout': 60,
        'force_generic_extractor': False,
        'no_check_certificate': True,  # 禁用 SSL 证书验证（最后手段）
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with YoutubeDL(ydl_opts) as ydl:
                logger.info(f"开始下载 YouTube 视频 (尝试 {attempt + 1}/{max_retries}): {video_url}")
                info = ydl.extract_info(video_url, download=True)
                ext = info.get('ext', 'mp4')
                file_path = str(temp_dir / f"{file_id}.{ext}")
                logger.info(f"YouTube 视频下载完成: {file_path}")
                return file_path, ext
        except Exception as e:
            error_msg = str(e)
            if 'SSL' in error_msg or 'UNEXPECTED_EOF' in error_msg:
                if attempt < max_retries - 1:
                    logger.warning(f"SSL 连接错误，{attempt + 1} 秒后重试: {error_msg}")
                    sleep(attempt + 1)  # 递进式延迟
                    continue
            logger.error(f"下载 YouTube 视频失败: {error_msg}")
            raise


def _download_tiktok(video_url: str, temp_dir: Path, file_id: str) -> Tuple[str, str]:
    """下载 TikTok 视频"""
    if YoutubeDL is None:
        raise RuntimeError("yt-dlp 未安装，请运行: pip install yt-dlp")
    
    output_template = str(temp_dir / file_id) + ".%(ext)s"
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': False,
        'socket_timeout': 60,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        'retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': True,
        'no_check_certificate': True,
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with YoutubeDL(ydl_opts) as ydl:
                logger.info(f"开始下载 TikTok 视频 (尝试 {attempt + 1}/{max_retries}): {video_url}")
                info = ydl.extract_info(video_url, download=True)
                ext = info.get('ext', 'mp4')
                file_path = str(temp_dir / f"{file_id}.{ext}")
                logger.info(f"TikTok 视频下载完成: {file_path}")
                return file_path, ext
        except Exception as e:
            error_msg = str(e)
            if 'SSL' in error_msg or 'UNEXPECTED_EOF' in error_msg:
                if attempt < max_retries - 1:
                    logger.warning(f"SSL 连接错误，{attempt + 1} 秒后重试: {error_msg}")
                    sleep(attempt + 1)
                    continue
            logger.error(f"下载 TikTok 视频失败: {error_msg}")
            raise


def _download_twitter(video_url: str, temp_dir: Path, file_id: str) -> Tuple[str, str]:
    """下载 Twitter 视频"""
    if YoutubeDL is None:
        raise RuntimeError("yt-dlp 未安装，请运行: pip install yt-dlp")
    
    output_template = str(temp_dir / file_id) + ".%(ext)s"
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': False,
        'socket_timeout': 60,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        'retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': True,
        'no_check_certificate': True,
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with YoutubeDL(ydl_opts) as ydl:
                logger.info(f"开始下载 Twitter 视频 (尝试 {attempt + 1}/{max_retries}): {video_url}")
                info = ydl.extract_info(video_url, download=True)
                ext = info.get('ext', 'mp4')
                file_path = str(temp_dir / f"{file_id}.{ext}")
                logger.info(f"Twitter 视频下载完成: {file_path}")
                return file_path, ext
        except Exception as e:
            error_msg = str(e)
            if 'SSL' in error_msg or 'UNEXPECTED_EOF' in error_msg:
                if attempt < max_retries - 1:
                    logger.warning(f"SSL 连接错误，{attempt + 1} 秒后重试: {error_msg}")
                    sleep(attempt + 1)
                    continue
            logger.error(f"下载 Twitter 视频失败: {error_msg}")
            raise


def _get_video_title(video_url: str) -> str:
    """获取视频标题"""
    if YoutubeDL is None:
        raise RuntimeError("yt-dlp 未安装，请运行: pip install yt-dlp")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 60,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        'retries': 2,
        'no_check_certificate': True,
    }
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                title = info.get('title', 'video')
                logger.info(f"获取视频标题: {title}")
                return title
        except Exception as e:
            error_msg = str(e)
            if 'SSL' in error_msg or 'UNEXPECTED_EOF' in error_msg:
                if attempt < max_retries - 1:
                    logger.warning(f"获取标题时 SSL 错误，重试: {error_msg}")
                    sleep(2)
                    continue
            logger.warning(f"获取视频标题失败，使用默认值: {error_msg}")
            return 'video'
    
    return 'video'


def _sanitize_filename(filename: str, max_length: int = 50) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        max_length: 最大长度限制
        
    Returns:
        清理后的文件名
    """
    import re
    # 移除非法字符：/ \ : * ? " < > |
    sanitized = re.sub(r'[/\\:*?"<>|]', '', filename)
    # 替换空格为下划线
    sanitized = sanitized.replace(' ', '_')
    # 移除多余下划线
    sanitized = re.sub(r'_+', '_', sanitized)
    # 限制长度
    sanitized = sanitized[:max_length]
    # 移除末尾下划线
    sanitized = sanitized.rstrip('_')
    
    return sanitized if sanitized else 'video'
