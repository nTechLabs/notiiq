from functools import lru_cache
import os
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
                    model_storage_directory = os.getenv(
                        "EASYOCR_MODEL_STORAGE_DIRECTORY"
                    )
                    download_enabled = (
                        os.getenv("EASYOCR_DOWNLOAD_ENABLED", "true").lower()
                        == "true"
                    )
                    self._reader = easyocr.Reader(
                        ["ko", "en"],
                        gpu=False,
                        model_storage_directory=model_storage_directory,
                        download_enabled=download_enabled,
                    )
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

