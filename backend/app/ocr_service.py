from functools import lru_cache
from threading import Lock

import cv2
import easyocr
import numpy as np


class OcrService:
    def __init__(self) -> None:
        self._reader: easyocr.Reader | None = None
        self._lock = Lock()

    def _get_reader(self) -> easyocr.Reader:
        if self._reader is None:
            with self._lock:
                if self._reader is None:
                    self._reader = easyocr.Reader(["ko", "en"], gpu=False)
        return self._reader

    def read(self, image_bytes: bytes) -> list[str]:
        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("이미지 파일을 해석할 수 없습니다.")
        return self._get_reader().readtext(image, detail=0, paragraph=False)


@lru_cache(maxsize=1)
def get_ocr_service() -> OcrService:
    return OcrService()

