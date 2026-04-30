import os
import sys
import io

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import json
import numpy as np
from typing import List, Tuple, Optional
from PIL import Image

import cv2
from config import settings

# OpenCV 内置的 LBPH 人脸识别器
LBPH_RECOGNIZER = cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8, threshold=100.0)


class FaceService:
    """人脸识别服务 - 基于 OpenCV LBPH"""

    def __init__(self):
        self.threshold = settings.FACE_SIMILARITY_THRESHOLD
        self._models = {}  # 缓存每个成员的识别模型
        self._trained = False

    def encode_image(self, image_data: bytes) -> List[float]:
        """提取图像直方图特征（用于比对）"""
        try:
            image = Image.open(io.BytesIO(image_data))
            image_array = np.array(image)

            # 转换为灰度图
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_array

            # 使用 LBP 算子提取局部二值模式直方图
            lbp = self._compute_lbp(gray)

            # 返回直方图特征向量 (128维，与 face_recognition 库兼容)
            hist, _ = np.histogram(lbp.ravel(), bins=128, range=(0, 256))
            hist = hist.astype(np.float32)
            hist = cv2.normalize(hist, hist).flatten()

            return hist.tolist()

        except Exception as e:
            raise ValueError(f"人脸特征提取失败: {str(e)}")

    def _compute_lbp(self, gray_image):
        """计算局部二值模式"""
        h, w = gray_image.shape
        lbp = np.zeros((h, w), dtype=np.uint8)

        for i in range(1, h - 1):
            for j in range(1, w - 1):
                center = gray_image[i, j]
                code = 0
                code |= (gray_image[i - 1, j - 1] > center) << 7
                code |= (gray_image[i - 1, j] > center) << 6
                code |= (gray_image[i - 1, j + 1] > center) << 5
                code |= (gray_image[i + 1, j - 1] > center) << 4
                code |= (gray_image[i + 1, j] > center) << 3
                code |= (gray_image[i + 1, j + 1] > center) << 2
                code |= (gray_image[i, j - 1] > center) << 1
                code |= (gray_image[i, j + 1] > center) << 0
                lbp[i, j] = code

        return lbp

    def encode_image_file(self, file_path: str) -> List[float]:
        """从文件提取特征"""
        try:
            with open(file_path, 'rb') as f:
                image_data = f.read()
            return self.encode_image(image_data)
        except Exception as e:
            raise ValueError(f"人脸特征提取失败: {str(e)}")

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))

    def compare_faces(self, encoding: List[float], face_list: List[Tuple[int, str, List[float]]]) -> Tuple[bool, Optional[int], Optional[str], float]:
        """比对人脸特征"""
        if not face_list:
            return False, None, None, 0.0

        best_confidence = 0.0
        best_member_id = None
        best_member_name = None

        for member_id, name, stored_encoding in face_list:
            confidence = self.cosine_similarity(encoding, stored_encoding)
            if confidence > best_confidence:
                best_confidence = confidence
                best_member_id = member_id
                best_member_name = name

        matched = best_confidence >= self.threshold
        return matched, best_member_id, best_member_name, best_confidence

    def get_recognition_type(self, confidence: float) -> str:
        """根据置信度确定识别类型"""
        if confidence >= self.threshold:
            return "known"
        elif confidence >= 0.4:
            return "pending_review"
        else:
            return "unknown"


face_service = FaceService()
