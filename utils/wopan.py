import json
import base64
import time
import os
import logging
import requests
import pyaes
import random
import string
import math

logger = logging.getLogger(__name__)

class WopanUploader:
    UPLOAD_URL = "https://tjupload.pan.wo.cn/openapi/client/upload2C"
    CHUNK_SIZE = 8 * 1024 * 1024  # 8MB chunks (Aligned with SDK)
    IV = b"wNSOYIB1k1DjY5lA"

    def __init__(self, access_token: str):
        self.access_token = access_token

    def _get_file_type(self, filename: str) -> str:
        """Get file type code based on extension"""
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        if ext in ['jpg', 'jpeg', 'png', 'bmp', 'gif']: return "1"
        if ext in ['mp4', 'mkv', 'avi', 'mov', 'flv']: return "2"
        if ext in ['mp3', 'wav', 'flac']: return "3"
        if ext in ['doc', 'docx', 'pdf', 'txt']: return "4"
        return "5" # Default/Other

    def _encrypt_file_info(self, file_info: dict) -> str:
        """Encrypt file info using AES-128-CBC"""
        try:
            key = self.access_token[:16].encode('utf-8')
            json_str = json.dumps(file_info, separators=(',', ':')).encode('utf-8')
            
            # Use pyaes's built-in Encrypter with automatic PKCS7 padding
            aes_mode = pyaes.AESModeOfOperationCBC(key, iv=self.IV)
            encrypter = pyaes.Encrypter(aes_mode)
            encrypted = encrypter.feed(json_str)
            encrypted += encrypter.feed()  # Finalize with padding
            
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def upload(self, file_path: str, directory_id: str = "0") -> dict:
        """
        Upload file to Wopan with chunked upload support
        
        Args:
            file_path: Path to the file to upload
            directory_id: Target directory ID (default "0" for root)
            
        Returns:
            API response dict
        """
        file_path = str(file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        logger.info(f"Starting upload to Wopan: {file_name} ({file_size} bytes)")

        # Calculate number of chunks needed (Standard ceil logic)
        total_parts = math.ceil(file_size / self.CHUNK_SIZE)
        if total_parts == 0:
            total_parts = 1
            
        logger.info(f"File will be uploaded in {total_parts} chunks (Chunk size: {self.CHUNK_SIZE} bytes)")

        batch_no = time.strftime("%Y%m%d%H%M%S")
        # Generate uniqueId once for the entire upload session
        unique_id = f"{int(time.time() * 1000)}_{''.join(random.choices(string.ascii_letters, k=6))}"
        
        try:
            with open(file_path, "rb") as f:
                for part_index in range(1, total_parts + 1):
                    # Read chunk
                    chunk_data = f.read(self.CHUNK_SIZE)
                    
                    part_size = len(chunk_data)
                    
                    # Prepare file info
                    file_info = {
                        "spaceType": "0",
                        "directoryId": directory_id,
                        "batchNo": batch_no,
                        "fileName": file_name,
                        "fileSize": file_size,
                        "fileType": self._get_file_type(file_name),
                        # SDK omits empty fields, but let's keep minimal required
                    }
                    
                    encrypted_file_info = self._encrypt_file_info(file_info)
                    
                    headers = {
                        "Origin": "https://pan.wo.cn",
                        "Referer": "https://pan.wo.cn/",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                    
                    # Multipart data (Order matters in some strict servers, though requests handles it)
                    data = {
                        "uniqueId": unique_id,
                        "accessToken": self.access_token,
                        "fileName": file_name,
                        "psToken": "undefined",
                        "fileSize": str(file_size),
                        "totalPart": str(total_parts),
                        "channel": "wocloud",
                        "directoryId": directory_id,
                        "fileInfo": encrypted_file_info,
                        "partSize": str(part_size),
                        "partIndex": str(part_index)
                    }
                    
                    files = {
                        "file": (file_name, chunk_data, "application/octet-stream")
                    }
                    
                    logger.info(f"Uploading part {part_index}/{total_parts} ({part_size} bytes)...")
                    
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            response = requests.post(
                                self.UPLOAD_URL, 
                                headers=headers, 
                                data=data, 
                                files=files,
                                timeout=120 # Increased timeout for larger chunks
                            )
                            response.raise_for_status()
                            result = response.json()
                            
                            if result.get("code") == "0000":
                                logger.info(f"Part {part_index} uploaded successfully")
                                # Check if we got a file ID (fid) in the response data
                                # This confirms the server has finalized the file
                                if result.get("data", {}).get("fid"):
                                    logger.info(f"Upload completed with FID: {result['data']['fid']}")
                                    return result
                                
                                if part_index == total_parts:
                                    # If it's the last part but no FID, something might be wrong, 
                                    # but we'll return the result anyway as per current logic.
                                    # However, the "ghost file" issue suggests we should be wary.
                                    logger.warning(f"Upload finished but no FID returned in last part. Response: {result}")
                                    return result
                                break
                            else:
                                logger.error(f"Part {part_index} upload failed with API error: {result}")
                                if attempt < max_retries - 1:
                                    logger.info(f"Retrying part {part_index} (attempt {attempt + 2}/{max_retries})...")
                                    time.sleep(2)
                                    continue
                                raise Exception(f"Wopan API Error: {result.get('msg', 'Unknown error')}")
                        except requests.exceptions.RequestException as e:
                            logger.warning(f"Part {part_index} upload attempt {attempt + 1} failed: {e}")
                            if attempt < max_retries - 1:
                                logger.info(f"Retrying part {part_index} (attempt {attempt + 2}/{max_retries})...")
                                time.sleep(2 ** attempt)  # Exponential backoff
                                continue
                            raise
                    
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            raise
