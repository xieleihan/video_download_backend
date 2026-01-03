import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.video_service import VideoService

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
        
        result = await VideoService.download_and_save(request.video_url, request.type)
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
