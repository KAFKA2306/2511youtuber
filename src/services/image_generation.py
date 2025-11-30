"""Service layer for image generation using diffusion models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Protocol

import torch


@dataclass
class ImageGenerationRequest:
    """Request for image generation."""
    prompt: str
    negative_prompt: str = ""
    width: int = 1280
    height: int = 720
    num_inference_steps: int = 9
    guidance_scale: float = 0.0
    seed: int | None = None


@dataclass
class ImageGenerationResult:
    """Result of image generation."""
    image: Any  # PIL.Image.Image
    seed: int
    prompt: str


class ImageGenerationService(Protocol):
    """Protocol for image generation services."""

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """Generate a single image."""
        ...

    def generate_batch(
        self,
        requests: List[ImageGenerationRequest]
    ) -> List[ImageGenerationResult]:
        """Generate multiple images in batch."""
        ...

    def is_available(self) -> bool:
        """Check if the service is available."""
        ...


class ZImageTurboService:
    """Z-Image-Turbo implementation of ImageGenerationService."""

    def __init__(
        self,
        model_path: str | Path,
        device: str = "cuda",
        batch_size: int = 1,
        compile_model: bool = False,
    ):
        """Initialize Z-Image-Turbo service.

        Args:
            model_path: Path to Z-Image-Turbo model
            device: Device to run on (cuda/cpu)
            batch_size: Maximum batch size for inference
            compile_model: Whether to compile model with torch.compile
        """
        self.model_path = Path(model_path)
        self.device = device
        self.batch_size = batch_size
        self.compile_model = compile_model
        self._pipeline = None
        self._compiled = False

    def is_available(self) -> bool:
        """Check if Z-Image-Turbo is available."""
        return self.model_path.exists()

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """Generate a single image."""
        results = self.generate_batch([request])
        return results[0]

    def generate_batch(
        self,
        requests: List[ImageGenerationRequest]
    ) -> List[ImageGenerationResult]:
        """Generate multiple images in batch.

        Automatically handles batching based on configured batch_size.
        """
        if not requests:
            return []

        pipe = self._ensure_pipeline()

        results = []
        for i in range(0, len(requests), self.batch_size):
            batch = requests[i:i + self.batch_size]
            batch_results = self._generate_batch_internal(pipe, batch)
            results.extend(batch_results)

        return results

    def _generate_batch_internal(
        self,
        pipe: Any,
        requests: List[ImageGenerationRequest],
    ) -> List[ImageGenerationResult]:
        """Generate a single batch of images."""
        # Prepare batch inputs
        prompts = [req.prompt for req in requests]
        negative_prompts = [req.negative_prompt for req in requests]

        # Use first request's settings (assume all same in batch)
        first = requests[0]

        # Handle seeds
        seeds = [req.seed if req.seed is not None else 42 for req in requests]

        # Generate batch
        if len(requests) == 1:
            # Single image - use scalar inputs
            generator = torch.Generator(self.device).manual_seed(seeds[0])
            output = pipe(
                prompt=prompts[0],
                negative_prompt=negative_prompts[0],
                height=first.height,
                width=first.width,
                num_inference_steps=first.num_inference_steps,
                guidance_scale=first.guidance_scale,
                generator=generator,
            )
            images = [output.images[0]]
        else:
            # Batch generation - use list inputs
            # Note: ZImagePipeline may not support batch generation directly
            # We'll generate sequentially for now
            images = []
            for idx, req in enumerate(requests):
                generator = torch.Generator(self.device).manual_seed(seeds[idx])
                output = pipe(
                    prompt=req.prompt,
                    negative_prompt=req.negative_prompt,
                    height=req.height,
                    width=req.width,
                    num_inference_steps=req.num_inference_steps,
                    guidance_scale=req.guidance_scale,
                    generator=generator,
                )
                images.append(output.images[0])

        # Build results
        return [
            ImageGenerationResult(
                image=image,
                seed=seeds[idx],
                prompt=requests[idx].prompt,
            )
            for idx, image in enumerate(images)
        ]

    def _ensure_pipeline(self) -> Any:
        """Lazy load and optionally compile the pipeline."""
        if self._pipeline is None:
            from diffusers import ZImagePipeline

            self._pipeline = ZImagePipeline.from_pretrained(
                str(self.model_path),
                torch_dtype=torch.bfloat16,
                low_cpu_mem_usage=False
            ).to(self.device)

            # Optionally compile the model
            if self.compile_model and not self._compiled:
                self._pipeline.unet = torch.compile(
                    self._pipeline.unet,
                    mode="reduce-overhead",
                    fullgraph=True,
                )
                self._compiled = True

        return self._pipeline
