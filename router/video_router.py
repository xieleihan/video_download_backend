import logging
import os
import uuid
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
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


@router.post("/wopan/file-upload")
async def upload_file_to_wopan(
    file: UploadFile = File(...),
    directory_id: str = Form("0")
) -> Dict[str, Any]:
    """
    浏览器文件上传到联通网盘接口

    - **file**: 上传的文件
    - **directory_id**: 目标目录 ID (可选，默认为根目录 "0")
    """
    try:
        access_token = os.getenv("WOPAN_ACCESS_TOKEN")
        if not access_token:
            raise HTTPException(status_code=500, detail="未配置 WOPAN_ACCESS_TOKEN")

        # 保存到临时目录
        temp_dir = Path(__file__).parent.parent / "temp" / "uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 保留原始文件名，用 uuid 防冲突
        suffix = Path(file.filename).suffix
        safe_name = f"{uuid.uuid4().hex}{suffix}"
        temp_path = temp_dir / safe_name

        with open(temp_path, "wb") as f:
            while chunk := await file.read(8 * 1024 * 1024):
                f.write(chunk)

        logger.info(f"文件已保存到临时路径: {temp_path}")

        # 上传到联通网盘（使用原始文件名）
        # 临时重命名以保留原始文件名
        original_path = temp_dir / file.filename
        renamed = False
        if not original_path.exists():
            temp_path.rename(original_path)
            renamed = True
            upload_path = original_path
        else:
            upload_path = temp_path

        try:
            uploader = WopanUploader(access_token)
            result = uploader.upload(str(upload_path), directory_id)
        finally:
            # 清理临时文件
            upload_path.unlink(missing_ok=True)
            if renamed and temp_path.exists():
                temp_path.unlink(missing_ok=True)

        return {
            "status": "success",
            "message": f"文件 {file.filename} 上传到联通网盘成功",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
