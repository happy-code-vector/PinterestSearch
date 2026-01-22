"""
NSFW Image Detector Module
Supports multiple backends: NudeNet and PyTorch
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

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
    - pytorch: More accurate, requires PyTorch installation
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
            from nudenet import NudeClassifier

            self._detector = NudeClassifier()
            self._backend_name = "NudeNet"
            logger.info(f"Initialized {self._backend_name} detector")
        except ImportError:
            raise ImportError(
                "NudeNet not installed. Install with: pip install nudenet"
            )

    def _init_pytorch(self):
        """Initialize PyTorch-based detector."""
        try:
            import torch
            from torchvision import models, transforms
            from PIL import Image

            # Use a pre-trained ResNet50 model
            # For production NSFW detection, you would load a trained NSFW model
            # This is a placeholder - in practice you'd use a model trained on NSFW data
            self._detector = models.resnet50(pretrained=True)
            self._detector.eval()

            # Image preprocessing
            self._preprocess = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                ),
            ])

            self._torch = torch
            self._pil_image = Image
            self._backend_name = "PyTorch (ResNet50)"
            logger.info(f"Initialized {self._backend_name} detector")
            logger.warning(
                "PyTorch backend uses generic ResNet50. "
                "For production NSFW detection, use a properly trained model or NudeNet."
            )
        except ImportError:
            raise ImportError(
                "PyTorch not installed. Install with: pip install torch torchvision Pillow"
            )

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

    def _check_nudenet(self, image_path: str) -> bool:
        """Check NSFW using NudeNet."""
        result = self._detector.classify(image_path)

        # NudeNet returns: {'unsafe': bool, 'score': float}
        unsafe = result.get('unsafe', False)
        score = result.get('score', 0.0)

        # Use both unsafe flag and score threshold
        if unsafe:
            logger.debug(f"NudeNet detected NSFW: {image_path} (unsafe=True, score={score:.3f})")
            return True

        if score > self.threshold:
            logger.debug(f"NudeNet detected NSFW: {image_path} (score={score:.3f} > threshold={self.threshold})")
            return True

        logger.debug(f"NudeNet detected safe: {image_path} (score={score:.3f})")
        return False

    def _check_pytorch(self, image_path: str) -> bool:
        """
        Check NSFW using PyTorch.

        Note: This is a placeholder implementation using generic ResNet50.
        For production use, replace with a trained NSFW model.
        """
        try:
            # Load and preprocess image
            img = self._pil_image.open(image_path).convert('RGB')
            img_tensor = self._preprocess(img).unsqueeze(0)

            # Run inference
            with self._torch.no_grad():
                outputs = self._detector(img_tensor)

            # Get the predicted class and confidence
            # Note: ImageNet classes don't include NSFW, so this is a simplified check
            # In production, use a model actually trained on NSFW data
            probabilities = self._torch.nn.functional.softmax(outputs[0], dim=0)
            max_prob, predicted_class = self._torch.max(probabilities, 0)

            # Placeholder: This would need a proper NSFW-trained model
            # For now, we'll return False (safe) as this is not a real NSFW detector
            logger.debug(
                f"PyTorch check: {image_path} (class={predicted_class.item()}, "
                f"prob={max_prob.item():.3f}) - Note: Using generic ResNet50"
            )

            # In production, check if predicted class is NSFW and probability > threshold
            # For now, always return False since we're using a generic model
            return False

        except Exception as e:
            logger.error(f"PyTorch detection error: {e}")
            return False

    def get_backend_name(self) -> str:
        """Get the name of the current backend."""
        return self._backend_name

    def get_info(self) -> Dict[str, Any]:
        """Get information about the detector."""
        return {
            "backend": self.backend,
            "backend_name": self._backend_name,
            "threshold": self.threshold,
        }


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
