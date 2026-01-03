from typing import Union
from datetime import datetime
import uvicorn
import logging

from fastapi import FastAPI

from router.video_router import router as video_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cloudflare Speed Test API",
    description="视频下载服务 API",
    version="1.0.0"
)

# 注册路由
app.include_router(video_router)

@app.get("/healthy")
def healthy() -> Union[dict, str]:
    return {
        "status": "ok",
        "message": "Service is healthy",
        "time": datetime.now().isoformat() 
    }

if __name__ == "__main__":
    logger.info("Starting the FastAPI server...")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )