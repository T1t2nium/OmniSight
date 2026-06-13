"""Motion detection for video frames — skip unchanged frames to reduce AI calls.

PR 5: FrameMotionDetector compares consecutive JPEG frames using pixel-
difference thresholding. Frames with insignificant change are skipped
before being forwarded to the AI pipeline, saving bandwidth and CPU.
"""

from __future__ import annotations

import base64
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FrameMotionDetector:
    """Detect motion between consecutive frames via mean pixel difference.

    Decodes base64 JPEG → grayscale → resize → absdiff → mean score.
    If score < threshold, the frame is considered unchanged.

    The first frame (no previous reference) always returns True.
    On any decode error, returns True (fail-open — don't block pipeline).
    """

    def __init__(self, threshold: float = 15.0, resize_width: int = 160) -> None:
        self._threshold = threshold
        self._resize_width = resize_width
        self._prev_gray: np.ndarray | None = None
        self._skip_count: int = 0

    @property
    def skip_count(self) -> int:
        """Number of frames skipped since last reset."""
        return self._skip_count

    def is_significant_change(self, jpeg_b64: str) -> bool:
        """Return True if this frame differs enough from the previous one."""
        try:
            jpeg_bytes = base64.b64decode(jpeg_b64)
            np_arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if bgr is None:
                return True  # undecodable — assume change
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

            h, w = gray.shape
            scale = self._resize_width / w
            new_h = int(h * scale)
            gray_resized = cv2.resize(gray, (self._resize_width, max(new_h, 1)))

            if self._prev_gray is None:
                self._prev_gray = gray_resized
                return True

            diff = cv2.absdiff(self._prev_gray, gray_resized)
            mean_diff = float(diff.mean())
            self._prev_gray = gray_resized

            if mean_diff < self._threshold:
                self._skip_count += 1
                return False
            return True
        except Exception:
            logger.debug("Motion detection error (benign)", exc_info=True)
            return True  # fail-open

    def reset(self) -> None:
        """Clear state — call when a new conversation begins."""
        self._prev_gray = None
        self._skip_count = 0
