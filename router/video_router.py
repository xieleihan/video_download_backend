import logging
import os
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.video_service import VideoService
from utils.wopan import WopanUploader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video", tags=["video"])


class VideoDownloadRequest(BaseModel):
    """视频下载请求模型"""
    video_url: str = Field(..., description="视频链接", example="https://www.youtube.com/watch?v=xxx")
    type: str = Field(..., description="视频类型: youtube, tiktok, twitter", example="youtube")


class VideoDownloadResponse(BaseModel):
    """视频下载响应模型"""
    status: str
    file_path: str
    extension: str
    file_size: int
    message: str
    upload_result: Dict[str, Any] = None


class WopanUploadRequest(BaseModel):
    """Wopan 上传请求模型"""
    file_path: str = Field(..., description="本地文件路径", example="D:\\frontend\\video_download_backend\\temp\\youtube\\video.mp4")
    directory_id: str = Field("0", description="目标目录 ID，默认为根目录", example="0")


class WopanUploadResponse(BaseModel):
    """Wopan 上传响应模型"""
    status: str
    message: str
    data: Dict[str, Any] = None


@router.post("/download", response_model=VideoDownloadResponse)
async def download_video(request: VideoDownloadRequest) -> Dict[str, Any]:
    """
    下载视频接口
    
    - **video_url**: 视频链接
    - **type**: 视频类型 (youtube/tiktok/twitter)
    """
    try:
        if not request.video_url:
            raise HTTPException(status_code=400, detail="video_url 不能为空")
        
        if request.type.lower() not in ["youtube", "tiktok", "twitter"]:
            raise HTTPException(status_code=400, detail="type 只支持: youtube, tiktok, twitter")
        
        logger.info(f"接收到视频下载请求: type={request.type}, url={request.video_url}")
        
        result = await VideoService.download_and_save(
            request.video_url, 
            request.type
        )
        return result
    
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"参数验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        logger.error(f"文件错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"下载失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"视频下载失败: {str(e)}")


@router.post("/wopan/upload", response_model=WopanUploadResponse)
async def upload_to_wopan(request: WopanUploadRequest) -> Dict[str, Any]:
    """
    上传文件到联通网盘接口
    
    - **file_path**: 本地文件路径
    - **directory_id**: 目标目录 ID (可选，默认为根目录 "0")
    """
    try:
        access_token = os.getenv("WOPAN_ACCESS_TOKEN")
        if not access_token:
            raise HTTPException(status_code=500, detail="未在 .env 文件中找到 WOPAN_ACCESS_TOKEN")

        if not request.file_path:
            raise HTTPException(status_code=400, detail="file_path 不能为空")
        
        logger.info(f"接收到 Wopan 上传请求: file_path={request.file_path}, directory_id={request.directory_id}")
        
        uploader = WopanUploader(access_token)
        result = uploader.upload(request.file_path, request.directory_id)
        
        return {
            "status": "success",
            "message": "文件上传到联通网盘成功",
            "data": result
        }
    
    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {str(e)}")
        raise HTTPException(status_code=400, detail=f"文件不存在: {str(e)}")
    except Exception as e:
        logger.error(f"上传到联通网盘失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
