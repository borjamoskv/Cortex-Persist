# [C5-REAL] Exergy-Maximized
"""
UIFeedbackLoop - Perception-Action Feedback Loop.

Coordinates real-time screen capture, Apple Vision native OCR, state diffing,
decision making, and MaestroUI execution to close the loop on desktop automation.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import time
from collections.abc import Callable
from typing import Any

from cortex.extensions.ui_control.maestro import MaestroUI
from cortex.extensions.ui_control.models import AppTarget, InteractionResult

try:
    import Vision
    from Cocoa import NSURL  # type: ignore
except ImportError:
    Vision = None
    NSURL = None

logger = logging.getLogger("cortex_extensions.ui_control.feedback_loop")


class UIFeedbackLoop:
    """
    Orchestrates the active perception-action loop:
    Capture -> OCR/State Parse -> Verify/Decide -> Act -> Recurse.
    """

    def __init__(self, maestro: MaestroUI | None = None) -> None:
        self.maestro = maestro or MaestroUI()
        self.last_screenshot_path: str | None = None
        self.last_ocr_results: list[dict[str, Any]] = []

    def perform_native_ocr(self, image_path: str) -> list[dict[str, Any]]:
        """
        Runs native macOS Apple Vision OCR (VNRecognizeTextRequest).
        Zero-dependency, high-speed, local C5-REAL text extraction.
        """
        if not Vision or not NSURL:
            logger.warning("Vision framework or Cocoa NSURL not available. Bypassing local OCR.")
            return []

        if not os.path.exists(image_path):
            logger.error("Screenshot path does not exist for OCR: %s", image_path)
            return []

        try:
            url = NSURL.fileURLWithPath_(image_path)
            handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, None)
            request = Vision.VNRecognizeTextRequest.alloc().init()

            # Configure OCR settings
            request.setRecognitionLevel_(0)  # 0 = Accurate, 1 = Fast
            request.setUsesLanguageCorrection_(True)

            success, error = handler.performRequests_error_([request], None)
            if not success:
                logger.error("Native OCR failed: %s", error)
                return []

            results = request.results()
            parsed = []
            for obs in results:
                candidates = obs.topCandidates_(1)
                if not candidates:
                    continue
                candidate = candidates[0]
                text = candidate.string()
                confidence = candidate.confidence()

                # Get bounding box (normalized coordinates 0.0 - 1.0)
                bbox = obs.boundingBox()
                # bbox properties: origin.x, origin.y, size.width, size.height
                parsed.append(
                    {
                        "text": text,
                        "confidence": float(confidence),
                        "x": float(bbox.origin.x),
                        "y": float(bbox.origin.y),
                        "width": float(bbox.size.width),
                        "height": float(bbox.size.height),
                    }
                )
            return parsed
        except Exception as e:
            logger.error("Error performing native Apple Vision OCR: %s", e)
            return []

    async def observe_state(self) -> dict[str, Any]:
        """Captures screen and extracts native OCR text state."""
        # 1. Capture screen
        cap_res = self.maestro.screenshot()
        if not cap_res.success or not cap_res.output:
            raise RuntimeError(f"Screen capture failed: {cap_res.error}")

        self.last_screenshot_path = cap_res.output

        # 2. Extract OCR
        ocr_res = self.perform_native_ocr(self.last_screenshot_path)  # type: ignore
        self.last_ocr_results = ocr_res

        # 3. Compile textual state
        full_text = " ".join([item["text"] for item in ocr_res])

        return {
            "screenshot_path": self.last_screenshot_path,
            "ocr_elements": ocr_res,
            "full_text": full_text,
            "timestamp": time.time(),
        }

    async def execute_perception_action_loop(
        self,
        goal: str,
        verify_fn: Callable[[dict[str, Any]], bool],
        decide_fn: Callable[[dict[str, Any], str], list[dict[str, Any]]],
        max_iterations: int = 5,
        step_delay: float = 1.0,
    ) -> InteractionResult:
        """
        Runs the closed-loop automation cycle:
        1. Capture screenshot and perform local OCR.
        2. Verify if the target condition is met (verify_fn).
        3. If not, decide on the next actions (decide_fn).
        4. Execute those actions via MaestroUI.
        5. Repeat.
        """
        logger.info("[FeedbackLoop] Initiating perception-action loop for goal: '%s'", goal)

        for iteration in range(1, max_iterations + 1):
            logger.info("[FeedbackLoop] Iteration %d/%d starting...", iteration, max_iterations)

            # Step 1 & 2: Observe and parse
            try:
                state = await self.observe_state()
            except Exception as e:
                logger.error("[FeedbackLoop] Perception step failed: %s", e)
                return InteractionResult(success=False, error=f"Perception failed: {e}")

            # Step 3: Verify target state
            if verify_fn(state):
                logger.info("[FeedbackLoop] Goal successfully achieved and verified!")
                return InteractionResult(
                    success=True,
                    output=f"Goal verified on iteration {iteration}. Final state: {state['full_text'][:200]}...",
                )

            if iteration == max_iterations:
                break

            # Step 4: Decide next actions
            actions = decide_fn(state, goal)
            if not actions:
                logger.warning("[FeedbackLoop] No actions generated. Terminating loop.")
                return InteractionResult(
                    success=False, error="Decision function returned no actions."
                )

            # Step 5: Execute actions
            for action in actions:
                action_name = action.get("action")
                if not action_name:
                    continue

                logger.info("[FeedbackLoop] Executing decided action: %s", action_name)
                args = action.get("args", {})

                # Map 'app' or 'app_name' to target AppTarget if expected
                app_name = args.get("app") or args.get("app_name") or args.get("target")
                if app_name and isinstance(app_name, str):
                    args["target"] = AppTarget(name=app_name)
                    args.pop("app", None)
                    args.pop("app_name", None)

                if hasattr(self.maestro, action_name):
                    method = getattr(self.maestro, action_name)
                    try:
                        if inspect.iscoroutinefunction(method):
                            res = await method(**args)
                        elif callable(method):
                            res = method(**args)
                            if asyncio.iscoroutine(res) or asyncio.isfuture(res):
                                res = await res
                        else:
                            res = method

                        # Check result type
                        if isinstance(res, InteractionResult) and not res.success:
                            logger.warning(
                                "[FeedbackLoop] Action execution warning: %s failed: %s",
                                action_name,
                                res.error,
                            )
                    except Exception as exc:
                        logger.error(
                            "[FeedbackLoop] Exception executing action %s: %s", action_name, exc
                        )
                else:
                    logger.error("[FeedbackLoop] MaestroUI has no method %s", action_name)

            # Step 6: Step delay to allow GUI to render / update
            await asyncio.sleep(step_delay)

        logger.warning(
            "[FeedbackLoop] Failed to verify goal completion after %d iterations.", max_iterations
        )
        return InteractionResult(
            success=False,
            error=f"Goal not met/verified within max iterations ({max_iterations}).",
        )
