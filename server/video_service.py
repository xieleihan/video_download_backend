import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from utils.download import download_video
from utils.wopan import WopanUploader

logger = logging.getLogger(__name__)


class VideoService:
    """视频下载服务"""
    
    @staticmethod
    async def download_and_save(
        video_url: str, 
        video_type: str
    ) -> Dict[str, Any]:
        """
        下载视频并保存，可选上传到联通网盘
        
        Args:
            video_url: 视频链接
            video_type: 视频类型 (youtube/tiktok/twitter)
            
        Returns:
            Dict 包含下载结果
        """
        try:
            file_path, ext = download_video(video_url, video_type)
            
            # 验证文件是否存在
            if not Path(file_path).exists():
                raise FileNotFoundError(f"文件未找到: {file_path}")
            
            # 获取文件大小
            file_size = Path(file_path).stat().st_size
            
            result = {
                "status": "success",
                "file_path": file_path,
                "extension": ext,
                "file_size": file_size,
                "message": "视频下载成功"
            }

            wopan_access_token = os.getenv("WOPAN_ACCESS_TOKEN")

            # 如果提供了 token，则上传到联通网盘
            if wopan_access_token:
                try:
                    uploader = WopanUploader(wopan_access_token)
                    upload_res = uploader.upload(file_path)
                    result["upload_result"] = upload_res
                    result["message"] += "，并成功上传到联通网盘"
                except Exception as e:
                    logger.error(f"上传到联通网盘失败: {e}")
                    result["upload_result"] = {"error": str(e)}
                    result["message"] += f"，但上传到联通网盘失败: {str(e)}"
            
            return result
        except Exception as e:
            logger.error(f"视频下载失败: {str(e)}")
            raise
