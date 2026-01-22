"""
NSFW Image Detector Module
Uses NudeNet for lightweight and fast NSFW detection.
"""

import logging
from pathlib import Path
from typing import Dict, Any
import os
import tempfile

logger = logging.getLogger(__name__)


class NSFWDetector:
    """
    NSFW Image Detector using NudeNet.
    
    NudeNet is lightweight, fast, and has no heavy dependencies.
    """

    def __init__(self, threshold: float = 0.7):
        """
        Initialize NSFW detector.

        Args:
            threshold: NSFW threshold (0.0-1.0), higher = more strict
        """
        logger.info(f"NSFWDetector.__init__ called with threshold={threshold}")
        self.threshold = threshold
        self._detector = None
        self._backend_name = None

        self._initialize_detector()

    def _initialize_detector(self):
        """Initialize the NudeNet detector."""
        try:
            from nudenet import NudeDetector

            self._detector = NudeDetector()
            self._backend_name = "NudeNet"
            logger.info(f"Initialized {self._backend_name} detector")
        except Exception as e:
            logger.error(f"Failed to initialize NudeNet: {e}")
            raise

    def is_nsfw(self, image_path: str) -> bool:
        """
        Check if an image is NSFW.

        Args:
            image_path: Path to the image file

        Returns:
            True if image is NSFW, False otherwise
        """
        if not Path(image_path).exists():
            logger.warning(f"Image not found: {image_path}")
            return False

        try:
            return self._check_nudenet(image_path)
        except Exception as e:
            logger.error(f"Error checking NSFW for {image_path}: {e}")
            return False

    def is_nsfw_from_bytes(self, image_bytes: bytes) -> bool:
        """
        Check if an image is NSFW from in-memory bytes.

        This avoids saving the image to disk before checking NSFW,
        saving bandwidth and disk I/O for images that will be filtered.

        Args:
            image_bytes: Image data as bytes

        Returns:
            True if image is NSFW, False otherwise
        """
        if not image_bytes:
            logger.warning("Empty image bytes provided")
            return False

        try:
            return self._check_nudenet_from_bytes(image_bytes)
        except Exception as e:
            logger.error(f"Error checking NSFW from bytes: {e}")
            return False

    def _check_nudenet(self, image_path: str) -> bool:
        """Check NSFW using NudeNet."""
        detections = self._detector.detect(image_path)

        # NudeDetector.detect() returns a list of detections
        # Each detection: {'class': str, 'score': float, 'box': [x, y, w, h]}
        if not detections:
            logger.debug(f"NudeNet detected safe: {image_path} (no detections)")
            return False

        # Check for NSFW classes
        nsfw_classes = [
            "FEMALE_GENITALIA_COVERED",  # Treat covered as potentially NSFW too
            "BUTTOCKS_EXPOSED",
            "FEMALE_BREAST_EXPOSED",
            "FEMALE_GENITALIA_EXPOSED",
            "MALE_BREAST_EXPOSED",
            "ANUS_EXPOSED",
            "BELLY_EXPOSED",
            "MALE_GENITALIA_EXPOSED",
            "ARMPITS_EXPOSED",
        ]

        max_score = 0.0
        detected_nsfw = False

        for detection in detections:
            class_name = detection.get('class', '')
            score = detection.get('score', 0.0)

            if class_name in nsfw_classes:
                detected_nsfw = True
                max_score = max(max_score, score)
                logger.debug(f"NudeNet detected NSFW class: {class_name} (score={score:.3f})")

        if detected_nsfw and max_score > self.threshold:
            logger.debug(f"NudeNet detected NSFW: {image_path} (max_score={max_score:.3f} > threshold={self.threshold})")
            return True

        logger.debug(f"NudeNet detected safe: {image_path} (max_score={max_score:.3f})")
        return False

    def _check_nudenet_from_bytes(self, image_bytes: bytes) -> bool:
        """Check NSFW using NudeNet from in-memory bytes."""
        # NudeNet requires a file path, so save bytes to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            tmp_file.write(image_bytes)
            tmp_path = tmp_file.name

        try:
            detections = self._detector.detect(tmp_path)

            # NudeDetector.detect() returns a list of detections
            # Each detection: {'class': str, 'score': float, 'box': [x, y, w, h]}
            if not detections:
                logger.debug(f"NudeNet detected safe from bytes (no detections)")
                return False

            # Check for NSFW classes
            nsfw_classes = [
                "FEMALE_GENITALIA_COVERED",  # Treat covered as potentially NSFW too
                "BUTTOCKS_EXPOSED",
                "FEMALE_BREAST_EXPOSED",
                "FEMALE_GENITALIA_EXPOSED",
                "MALE_BREAST_EXPOSED",
                "ANUS_EXPOSED",
                "BELLY_EXPOSED",
                "MALE_GENITALIA_EXPOSED",
                "ARMPITS_EXPOSED",
            ]

            max_score = 0.0
            detected_nsfw = False

            for detection in detections:
                class_name = detection.get('class', '')
                score = detection.get('score', 0.0)

                if class_name in nsfw_classes:
                    detected_nsfw = True
                    max_score = max(max_score, score)
                    logger.debug(f"NudeNet detected NSFW class from bytes: {class_name} (score={score:.3f})")

            if detected_nsfw and max_score > self.threshold:
                logger.debug(f"NudeNet detected NSFW from bytes (max_score={max_score:.3f} > threshold={self.threshold})")
                return True

            logger.debug(f"NudeNet detected safe from bytes (max_score={max_score:.3f})")
            return False
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass

    def get_backend_name(self) -> str:
        """Get the name of the current backend."""
        return self._backend_name

    def get_info(self) -> Dict[str, Any]:
        """Get information about the detector."""
        return {
            "backend": "nudenet",
            "backend_name": self._backend_name,
            "threshold": self.threshold,
        }


# Convenience function for quick checks
def is_image_nsfw(image_path: str, threshold: float = 0.7) -> bool:
    """
    Quick check if an image is NSFW.

    Args:
        image_path: Path to the image
        threshold: NSFW threshold (0.0-1.0)

    Returns:
        True if NSFW, False otherwise
    """
    detector = NSFWDetector(threshold=threshold)
    return detector.is_nsfw(image_path)


if __name__ == "__main__":
    # Test the detector
    import sys

    if len(sys.argv) < 2:
        print("Usage: python nsfw_filter.py <image_path> [threshold]")
        sys.exit(1)

    image_path = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.7

    print(f"Checking: {image_path}")
    print(f"Threshold: {threshold}")
    print("-" * 40)

    try:
        detector = NSFWDetector(threshold=threshold)
        print(f"Detector info: {detector.get_info()}")

        is_nsfw = detector.is_nsfw(image_path)

        print("-" * 40)
        print(f"Result: {'NSFW' if is_nsfw else 'SAFE'}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)