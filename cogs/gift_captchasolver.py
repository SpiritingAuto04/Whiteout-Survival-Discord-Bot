#!/usr/bin/env python3
# Gift Captcha Solver for WOS Discord Bot
# Version 2 - now with ddddocr

import os
import warnings
import base64
import io
import time
import traceback
import logging
import logging.handlers

try:
    import ddddocr
    DDDDOCR_AVAILABLE = True
except ImportError:
    ddddocr = None
    DDDDOCR_AVAILABLE = False

class GiftCaptchaSolver:
    def __init__(self, save_images=0):
        """
        Initialize the ddddocr captcha solver.

        Args:
            save_images (int): Image saving mode (0=None, 1=Failed, 2=Success, 3=All).
                               Note: Saving logic is primarily handled in gift_operations.py now.
        """
        self.save_images_mode = save_images
        self.ddddocr_reader = None
        self.is_initialized = False

        # Logger setup
        self.logger = logging.getLogger("gift_solver")
        if not self.logger.hasHandlers():
            self.logger.setLevel(logging.INFO)
            self.logger.propagate = False
            log_dir = 'log'
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'gift_solver.txt')
            handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=3 * 1024 * 1024, backupCount=3, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
            self.logger.addHandler(handler)

        self.captcha_dir = 'captcha_images'
        os.makedirs(self.captcha_dir, exist_ok=True)

        self._initialize_ocr()

        self.stats = {
            "total_attempts": 0,
            "successful_decodes": 0,
            "failures": 0
        }
        self.reset_run_stats()

    def reset_run_stats(self):
        """Reset statistics for the current run."""
        self.run_stats = {
            "total_attempts": 0,
            "successful_decodes": 0,
            "failures": 0,
            "start_time": time.time()
        }

    def get_run_stats_report(self):
        """Get a formatted report of run statistics."""
        duration = time.time() - self.run_stats["start_time"]
        success_rate = 0
        if self.run_stats["total_attempts"] > 0:
            success_rate = (self.run_stats["successful_decodes"] / self.run_stats["total_attempts"]) * 100

        report = [
            "\n=== Captcha Solver Statistics ===",
            f"Total captcha attempts: {self.run_stats['total_attempts']}",
            f"Successful decodes: {self.run_stats['successful_decodes']}",
            f"Failures: {self.run_stats['failures']}",
            f"Success rate: {success_rate:.2f}%",
            f"Processing time: {duration:.2f} seconds",
            "=========================================="
        ]
        return "\n".join(report)

    def _initialize_ocr(self):
        """Initialize the DdddOcr reader and verify basic functionality."""
        if not DDDDOCR_AVAILABLE:
            self.logger.error("DdddOcr library not found. Captcha solving disabled.")
            self.is_initialized = False
            return

        try:
            self.logger.info("Initializing DdddOcr...")
            self.ddddocr_reader = ddddocr.DdddOcr(ocr=True, det=False, show_ad=False)
            self.logger.info("DdddOcr object created. Performing test classification...")
            try:
                from PIL import Image
                import numpy as np
                dummy_img = Image.new('RGB', (60, 30), color = 'black')
                import io
                img_byte_arr = io.BytesIO()
                dummy_img.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                test_result = self.ddddocr_reader.classification(img_bytes)
                self.logger.info(f"DdddOcr test classification successful (Result: '{test_result}'). Initialization complete.")
                self.is_initialized = True
            except ImportError:
                 self.logger.error("Pillow library not found, cannot perform DdddOcr init test. Assuming success if object created.")
                 self.is_initialized = True
            except Exception as test_e:
                 self.logger.error(f"DdddOcr test classification failed: {test_e}. Marking initialization as failed.")
                 self.is_initialized = False
                 self.ddddocr_reader = None
        except Exception as e:
            self.logger.exception(f"Failed during DdddOcr object creation: {e}")
            self.ddddocr_reader = None
            self.is_initialized = False
    
    async def solve_captcha(self, image_bytes, fid=None, attempt=0):
        """
        Attempts to solve captcha using ddddocr.

        Args:
            image_bytes (bytes): The raw byte data of the captcha image.
            fid (optional): Player ID for logging.
            attempt (int): Attempt number for logging.

        Returns:
            tuple: (solved_code, success, method, confidence, image_path)
                   - solved_code (str or None): The solved captcha text or None on failure.
                   - success (bool): True if solved successfully, False otherwise.
                   - method (str): Always "DdddOcr".
                   - confidence (float): Always 1.0 for ddddocr success, 0.0 otherwise.
                   - image_path (None): No longer provides a path from solver.
        """
        if not self.is_initialized or not self.ddddocr_reader:
            self.logger.error(f"DdddOcr not initialized. Cannot solve captcha for FID {fid}.")
            return None, False, "DdddOcr", 0.0, None

        self.stats["total_attempts"] += 1
        self.run_stats["total_attempts"] += 1
        start_time = time.time()

        try:
            EXPECTED_CAPTCHA_LENGTH = 4
            VALID_CHARACTERS = set('123456789ABCDEFGHIJKLMNPQRSTUVWXYZabcdefghijklmnpqrstuvwxyz')

            predicted_text = self.ddddocr_reader.classification(image_bytes)

            solve_duration = time.time() - start_time
            self.logger.info(f"[Solver] FID {fid}, Attempt {attempt+1}: DdddOcr raw result='{predicted_text}' ({solve_duration:.3f}s)")

            if (predicted_text and
                isinstance(predicted_text, str) and
                len(predicted_text) == EXPECTED_CAPTCHA_LENGTH and
                all(c in VALID_CHARACTERS for c in predicted_text)):

                self.stats["successful_decodes"] += 1
                self.run_stats["successful_decodes"] += 1
                self.logger.info(f"[Solver] FID {fid}, Attempt {attempt+1}: Success. Solved: {predicted_text}")
                return predicted_text, True, "DdddOcr", 1.0, None
            else:
                self.stats["failures"] += 1
                self.run_stats["failures"] += 1
                self.logger.warning(f"[Solver] FID {fid}, Attempt {attempt+1}: Failed validation (Length: {len(predicted_text) if predicted_text else 'N/A'}, Chars OK: {all(c in VALID_CHARACTERS for c in predicted_text) if predicted_text else 'N/A'})")
                return None, False, "DdddOcr", 0.0, None

        except Exception as e:
            self.stats["failures"] += 1
            self.run_stats["failures"] += 1
            self.logger.exception(f"[Solver] FID {fid}, Attempt {attempt+1}: Exception during ddddocr classification: {e}")
            return None, False, "DdddOcr", 0.0, None

    def get_stats(self):
        """Get current OCR statistics."""
        return self.stats