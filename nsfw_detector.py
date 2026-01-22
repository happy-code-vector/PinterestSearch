"""
NSFW Image Detector Module
Supports multiple backends: NudeNet and PyTorch (production-ready)
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum
import os

logger = logging.getLogger(__name__)


class NSFWBackend(Enum):
    """Available NSFW detection backends."""
    NUDENET = "nudenet"
    PYTORCH = "pytorch"


class NSFWDetector:
    """
    NSFW Image Detector with support for multiple backends.

    Backends:
    - nudenet: Lightweight, fast, no heavy dependencies
    - pytorch: Production-ready PyTorch model using nsfw_detector package
    """

    def __init__(self, backend: str = "nudenet", threshold: float = 0.7):
        """
        Initialize NSFW detector.

        Args:
            backend: Detection backend ('nudenet' or 'pytorch')
            threshold: NSFW threshold (0.0-1.0), higher = more strict
        """
        self.backend = backend.lower()
        self.threshold = threshold
        self._detector = None
        self._backend_name = None

        self._initialize_detector()

    def _initialize_detector(self):
        """Initialize the selected detector backend."""
        if self.backend == NSFWBackend.NUDENET.value:
            self._init_nudenet()
        elif self.backend == NSFWBackend.PYTORCH.value:
            self._init_pytorch()
        else:
            raise ValueError(f"Unknown backend: {self.backend}. Choose 'nudenet' or 'pytorch'")

    def _init_nudenet(self):
        """Initialize NudeNet detector."""
        try:
            from nudenet import NudeDetector

            self._detector = NudeDetector()
            self._backend_name = "NudeNet"
            logger.info(f"Initialized {self._backend_name} detector")
        except Exception as e:
            logger.error(f"Failed to initialize Nudenet: {e}")
            raise

    def _init_pytorch(self):
        """
        Initialize production PyTorch-based NSFW detector.

        Uses the nsfw_detector package with EfficientNet V2 model.
        Model is downloaded automatically on first use.
        """
        try:
            from nsfw_detector import predict

            # The nsfw_detector package uses a functional approach
            # Store the predict function as our detector
            self._detector = predict
            self._model_name = 'efficientnet_v2'
            self._backend_name = f"PyTorch ({self._model_name.upper()})"

            logger.info(f"Initialized {self._backend_name} detector")
            logger.info(f"NSFW threshold: {self.threshold}")
        except Exception as e:
            logger.error(f"Failed to initialize PyTorch NSFW detector: {e}")
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
            if self.backend == NSFWBackend.NUDENET.value:
                return self._check_nudenet(image_path)
            elif self.backend == NSFWBackend.PYTORCH.value:
                return self._check_pytorch(image_path)
        except Exception as e:
            logger.error(f"Error checking NSFW for {image_path}: {e}")
            return False

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
            if self.backend == NSFWBackend.NUDENET.value:
                return self._check_nudenet_from_bytes(image_bytes)
            elif self.backend == NSFWBackend.PYTORCH.value:
                return self._check_pytorch_from_bytes(image_bytes)
        except Exception as e:
            logger.error(f"Error checking NSFW from bytes: {e}")
            return False

        return False

    def _check_nudenet(self, image_path: str) -> bool:
        """Check NSFW using NudeNet."""
        detections = self._detector.detect(image_path)

        # NudeDetector.detect() returns a list of detections
        # Each detection: {'class': str, 'score': float, 'box': [x, y, w, h]}
        # NSFW classes are those with _EXPOSED suffix
        if not detections:
            logger.debug(f"NudeNet detected safe: {image_path} (no detections)")
            return False

        # Check for NSFW classes (those ending with _EXPOSED)
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
        import tempfile

        # NudeNet requires a file path, so save bytes to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            tmp_file.write(image_bytes)
            tmp_path = tmp_file.name

        try:
            detections = self._detector.detect(tmp_path)

            # NudeDetector.detect() returns a list of detections
            # Each detection: {'class': str, 'score': float, 'box': [x, y, w, h]}
            # NSFW classes are those with _EXPOSED suffix
            if not detections:
                logger.debug(f"NudeNet detected safe from bytes (no detections)")
                return False

            # Check for NSFW classes (those ending with _EXPOSED)
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

    def _check_pytorch(self, image_path: str) -> bool:
        """Check NSFW using PyTorch."""
        try:
            # nsfw_detector.predict() returns: {'porn': prob, 'sexy': prob, 'hentai': prob, 'neutral': prob, 'drawings': prob}
            predictions = self._detector(image_path)

            # Get NSFW probability (sum of porn, sexy, hentai)
            nsfw_score = (
                predictions.get('porn', 0.0) +
                predictions.get('sexy', 0.0) +
                predictions.get('hentai', 0.0)
            )

            is_nsfw = nsfw_score > self.threshold

            if is_nsfw:
                logger.debug(
                    f"PyTorch: NSFW detected for {image_path} "
                    f"(score={nsfw_score:.3f} > threshold={self.threshold})"
                )
            else:
                logger.debug(
                    f"PyTorch: Safe (score={nsfw_score:.3f}, "
                    f"neutral={predictions.get('neutral', 0.0):.3f})"
                )

            return is_nsfw

        except Exception as e:
            logger.error(f"PyTorch detection error: {e}")
            return False

    def _check_pytorch_from_bytes(self, image_bytes: bytes) -> bool:
        """Check NSFW using PyTorch from in-memory bytes."""
        import tempfile

        # nsfw_detector requires a file path, so save bytes to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            tmp_file.write(image_bytes)
            tmp_path = tmp_file.name

        try:
            # nsfw_detector.predict() returns: {'porn': prob, 'sexy': prob, 'hentai': prob, 'neutral': prob, 'drawings': prob}
            predictions = self._detector(tmp_path)

            # Get NSFW probability (sum of porn, sexy, hentai)
            nsfw_score = (
                predictions.get('porn', 0.0) +
                predictions.get('sexy', 0.0) +
                predictions.get('hentai', 0.0)
            )

            is_nsfw = nsfw_score > self.threshold

            if is_nsfw:
                logger.debug(
                    f"PyTorch: NSFW detected from bytes "
                    f"(score={nsfw_score:.3f} > threshold={self.threshold})"
                )
            else:
                logger.debug(
                    f"PyTorch: Safe from bytes (score={nsfw_score:.3f}, "
                    f"neutral={predictions.get('neutral', 0.0):.3f})"
                )

            return is_nsfw

        except Exception as e:
            logger.error(f"PyTorch detection from bytes error: {e}")
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
        info = {
            "backend": self.backend,
            "backend_name": self._backend_name,
            "threshold": self.threshold,
        }

        if self.backend == NSFWBackend.PYTORCH.value:
            info["model"] = self._model_name if hasattr(self, '_model_name') else "unknown"

        return info


# Convenience function for quick checks
def is_image_nsfw(
    image_path: str,
    backend: str = "nudenet",
    threshold: float = 0.7
) -> bool:
    """
    Quick check if an image is NSFW.

    Args:
        image_path: Path to the image
        backend: Detection backend ('nudenet' or 'pytorch')
        threshold: NSFW threshold (0.0-1.0)

    Returns:
        True if NSFW, False otherwise
    """
    detector = NSFWDetector(backend=backend, threshold=threshold)
    return detector.is_nsfw(image_path)


if __name__ == "__main__":
    # Test the detector
    import sys

    if len(sys.argv) < 2:
        print("Usage: python nsfw_detector.py <image_path> [backend] [threshold]")
        print("Backends: nudenet (default), pytorch")
        sys.exit(1)

    image_path = sys.argv[1]
    backend = sys.argv[2] if len(sys.argv) > 2 else "nudenet"
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.7

    print(f"Checking: {image_path}")
    print(f"Backend: {backend}")
    print(f"Threshold: {threshold}")
    print("-" * 40)

    try:
        detector = NSFWDetector(backend=backend, threshold=threshold)
        print(f"Detector info: {detector.get_info()}")

        is_nsfw = detector.is_nsfw(image_path)

        print("-" * 40)
        print(f"Result: {'NSFW' if is_nsfw else 'SAFE'}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
