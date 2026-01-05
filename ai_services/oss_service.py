"""
OSS服务模块
处理阿里云OSS文件上传和管理
"""

import time
import os
from pathlib import Path
from typing import Optional
from .base_service import BaseAIService
from config import (
    OSS_ENDPOINT,
    OSS_ACCESS_KEY_ID,
    OSS_ACCESS_KEY_SECRET,
    OSS_BUCKET_NAME,
    PROJECT_ROOT,
)


class OSSService(BaseAIService):
    """OSS文件服务"""
    
    def __init__(self):
        """初始化OSS服务"""
        super().__init__("OSS")
        
        # OSS客户端
        self._bucket = None
        self._initialized = False
    
    def initialize(self) -> None:
        """初始化OSS服务"""
        if self._initialized:
            return
        
        self._validate_oss_config()
        self._init_oss_client()
        
        self._initialized = True
        self.logger.info("OSS服务初始化完成")
    
    def _validate_oss_config(self) -> None:
        """验证OSS配置"""
        required_vars = {
            "OSS_ACCESS_KEY_ID": OSS_ACCESS_KEY_ID,
            "OSS_ACCESS_KEY_SECRET": OSS_ACCESS_KEY_SECRET,
            "OSS_BUCKET_NAME": OSS_BUCKET_NAME,
        }
        missing_vars = [name for name, value in required_vars.items() if not value]
        
        if missing_vars:
            import sys
            error_msg = f"\n{'='*60}\n"
            error_msg += f"错误: OSS功能需要设置以下环境变量:\n"
            for var in missing_vars:
                error_msg += f"  - {var}\n"
            error_msg += f"\n"
            
            if sys.platform == "win32":
                error_msg += f"Windows 设置方式:\n"
                for var in missing_vars:
                    error_msg += f"  setx {var} \"your_value_here\"\n"
            else:
                error_msg += f"Linux/Mac 设置方式:\n"
                error_msg += f"  在 ~/.bashrc 或 ~/.zshrc 中添加:\n"
                for var in missing_vars:
                    error_msg += f"  export {var}=your_value_here\n"
            
            error_msg += f"\n设置后需要重启终端或应用程序\n"
            error_msg += f"{'='*60}\n"
            raise ValueError(error_msg)
    
    def _init_oss_client(self) -> None:
        """初始化OSS客户端"""
        import oss2
        
        try:
            auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
            # 注意：endpoint不要加https://前缀
            self._bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
            self.logger.info(f"OSS连接配置 - Endpoint: {OSS_ENDPOINT}, Bucket: {OSS_BUCKET_NAME}")
        except Exception as e:
            raise Exception(f"OSS客户端初始化失败: {str(e)}") from e
    
    def upload_file(self, file_path: str, expiration: int = 3600) -> str:
        """上传文件到OSS
        
        Args:
            file_path: 本地文件路径
            expiration: 签名URL过期时间（秒），默认3600秒（1小时）
            
        Returns:
            OSS公开访问URL
            
        Raises:
            ValueError: 文件路径非法或超出大小限制
            SecurityError: 路径遍历攻击检测
        """
        # 安全检查1: 验证文件存在且可读
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise ValueError(f"文件不存在: {file_path}")
        if not file_path_obj.is_file():
            raise ValueError(f"不是有效文件: {file_path}")
        
        # 安全检查2: 验证文件大小（限制100MB）
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
        file_size = file_path_obj.stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(
                f"文件过大: {file_size / 1024 / 1024:.2f}MB (限制: {MAX_FILE_SIZE / 1024 / 1024}MB)"
            )
        if file_size == 0:
            raise ValueError("文件为空")
        
        # 安全检查3: 防止路径遍历攻击
        try:
            resolved_path = file_path_obj.resolve()
            project_root_resolved = Path(PROJECT_ROOT).resolve()
            # 确保文件在项目目录内
            resolved_path.relative_to(project_root_resolved)
        except (ValueError, RuntimeError) as e:
            from common.security import SecurityError
            raise SecurityError(f"检测到路径遍历攻击: {file_path}") from e
        
        # 生成规范的对象名
        object_name = self._generate_object_name(file_path_obj)
        
        self.logger.info(f"上传文件: {file_path_obj.name} -> {object_name}")
        
        # 上传文件（为Fun-ASR设置公共读权限）
        try:
            # 设置文件ACL为公共读（Fun-ASR要求）
            headers = {"x-oss-object-acl": "public-read"}
            result = self._bucket.put_object_from_file(
                object_name, str(resolved_path), headers=headers
            )
            self.logger.info(f"上传成功 - RequestID: {result.request_id}")
            self.logger.info("文件权限: 公共读（Fun-ASR要求）")
        except Exception as e:
            raise Exception(f"OSS上传失败: {str(e)}") from e
        
        # 生成公开URL（Fun-ASR要求文件公共可读）
        public_url = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{object_name}"
        
        self.logger.info(f"文件上传成功 (大小: {file_size / 1024:.2f}KB)")
        self.logger.info(f"公开URL: {public_url}")
        self.logger.info(f"原始路径: {object_name}")
        
        return public_url
    
    def _generate_object_name(self, file_path: Path) -> str:
        """生成OSS对象名
        
        Args:
            file_path: 文件路径对象
            
        Returns:
            OSS对象名
        """
        # 生成规范的对象名（遵循项目规范：video_translate/audio/{timestamp}_{filename}）
        timestamp = int(time.time() * 1000)  # 使用毫秒时间戳
        original_filename = file_path.name
        # 移除中文字符，只保留ASCII字符和数字
        safe_filename = "".join(
            c if c.isalnum() or c in "._-" else "_" for c in original_filename
        )
        object_name = f"video_translate/audio/{timestamp}_{safe_filename}"
        
        # 安全检查：确保对象名不包含..
        if ".." in object_name:
            from common.security import SecurityError
            raise SecurityError(f"对象名包含非法字符: {object_name}")
        
        return object_name
    
    def delete_file(self, object_name: str) -> bool:
        """删除OSS文件
        
        Args:
            object_name: OSS对象名
            
        Returns:
            删除是否成功
        """
        try:
            self._bucket.delete_object(object_name)
            self.logger.info(f"文件删除成功: {object_name}")
            return True
        except Exception as e:
            self.logger.error(f"文件删除失败: {object_name}, 错误: {e}")
            return False
    
    def file_exists(self, object_name: str) -> bool:
        """检查OSS文件是否存在
        
        Args:
            object_name: OSS对象名
            
        Returns:
            文件是否存在
        """
        try:
            return self._bucket.object_exists(object_name)
        except Exception as e:
            self.logger.error(f"检查文件存在性失败: {object_name}, 错误: {e}")
            return False
    
    def get_file_info(self, object_name: str) -> Optional[dict]:
        """获取OSS文件信息
        
        Args:
            object_name: OSS对象名
            
        Returns:
            文件信息字典，如果获取失败则返回None
        """
        try:
            head = self._bucket.head_object(object_name)
            return {
                "content_length": head.content_length,
                "content_type": head.content_type,
                "last_modified": head.last_modified,
                "etag": head.etag,
            }
        except Exception as e:
            self.logger.error(f"获取文件信息失败: {object_name}, 错误: {e}")
            return None
    
    def list_files(self, prefix: str = "", max_keys: int = 100) -> list:
        """列出OSS文件
        
        Args:
            prefix: 文件名前缀
            max_keys: 最大返回数量
            
        Returns:
            文件列表
        """
        try:
            objects = self._bucket.list_objects(prefix, max_keys=max_keys)
            file_list = []
            for obj in objects.object_list:
                file_list.append({
                    "key": obj.key,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                })
            return file_list
        except Exception as e:
            self.logger.error(f"列出文件失败: {e}")
            return []
