"""
Google Cloud API Client Wrapper
Handles initialization and management of Google Cloud Vision and Speech clients
"""
import os
import io
import logging
import time
from typing import Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pdfplumber
from pdf2image import convert_from_bytes
from google.cloud import vision, speech

logger = logging.getLogger(__name__)

class VisionService:
    """
    Advanced OCR Service for handling both images and PDFs efficiently.
    Implements hybrid approach: Direct text extraction for searchable PDFs,
    Image-based OCR for scanned PDFs.
    """

    def __init__(self, vision_client: vision.ImageAnnotatorClient):
        """Initialize VisionService with a Vision API client"""
        self.client = vision_client
        self.max_workers = 4  # Optimized parallel processing for PDF pages

    def _is_pdf(self, file_bytes: bytes) -> bool:
        """Check if file is PDF by magic bytes"""
        return file_bytes.startswith(b'%PDF')

    def detect_text(self, file_bytes: bytes, page_start: Optional[int] = None, page_end: Optional[int] = None) -> str:
        """
        Main entry point: Detect and extract text from image or PDF.
        """
        try:
            if not file_bytes:
                logger.warning("Empty file bytes provided")
                return ""
            
            if self._is_pdf(file_bytes):
                logger.info("PDF detected - Starting hybrid OCR pipeline")
                return self._extract_text_from_pdf_hybrid(file_bytes, page_start=page_start, page_end=page_end)
            else:
                logger.info("Image detected - Starting Vision API OCR")
                return self._extract_text_from_image(file_bytes)
            
        except Exception as e:
            logger.error(f"Error in detect_text: {e}")
            return f"Error detecting text: {str(e)}"

    def _extract_text_from_image(self, file_bytes: bytes) -> str:
        """Extract text from image using Google Vision API"""
        try:
            image = vision.Image(content=file_bytes)
            response = self.client.document_text_detection(image=image)
            
            if response.error.message:
                logger.error(f"Vision API error: {response.error.message}")
                return ""
            
            return response.full_text_annotation.text if response.full_text_annotation else ""
        except Exception as e:
            logger.error(f"Error extracting from image: {e}")
            return ""

    def _is_text_quality_good(self, text: str) -> bool:
        """
        Evaluate if extracted text is of acceptable quality.
        Detects CID-encoded garbage and other encoding issues.
        """
        if not text or len(text.strip()) < 20:
            return False
        
        cid_count = text.count('(cid:')
        if (cid_count / len(text)) * 100 > 5:
            return False
            
        return True

    def _extract_text_from_pdf_hybrid(self, pdf_bytes: bytes, page_start: Optional[int] = None, page_end: Optional[int] = None) -> str:
        """
        Hybrid PDF OCR Strategy: Direct extraction first, then Vision API fallback.
        """
        try:
            # Phase 1: Direct extraction
            logger.info("Phase 1: Attempting direct text extraction...")
            extracted_text = self._extract_text_directly_from_pdf(pdf_bytes, page_start=page_start, page_end=page_end)
            
            if self._is_text_quality_good(extracted_text):
                logger.info("✓ Phase 1 successful")
                return extracted_text
            
            # Phase 2: Vision API fallback
            logger.warning("Phase 1 quality poor. Phase 2: Image-based OCR...")
            return self._extract_text_via_images(pdf_bytes, page_start=page_start, page_end=page_end)
            
        except Exception as e:
            logger.error(f"Error in hybrid OCR: {e}")
            return ""

    def _extract_text_directly_from_pdf(self, pdf_bytes: bytes, page_start: Optional[int] = None, page_end: Optional[int] = None) -> str:
        """Fast direct text extraction from searchable PDFs."""
        text_parts = []
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                total_pages = len(pdf.pages)
                start = max(1, page_start) if page_start else 1
                end = min(total_pages, page_end) if page_end else total_pages
                
                for i in range(start - 1, end):
                    page_text = pdf.pages[i].extract_text()
                    if page_text:
                        text_parts.append(f"--- Page {i+1} ---\n{page_text}")
            
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"Direct extraction error: {e}")
            return ""

    def _extract_text_via_images(self, pdf_bytes: bytes, page_start: Optional[int] = None, page_end: Optional[int] = None) -> str:
        """
        Convert PDF to images and OCR via Vision API.
        Optimized to only convert requested pages.
        """
        try:
            logger.info(f"Converting PDF to images (pages {page_start or 1} to {page_end or 'end'})...")
            
            # Optimization: Only convert necessary pages from the start
            # This significantly reduces memory usage and processing time for large PDFs
            images = convert_from_bytes(
                pdf_bytes, 
                dpi=200, 
                first_page=page_start or 1, 
                last_page=page_end
            )
            
            total_converted = len(images)
            logger.info(f"Successfully converted {total_converted} pages")
            
            results: List[Tuple[int, str]] = []
            start_num = page_start or 1
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Page numbers in results should match the actual PDF page numbers
                futures = {executor.submit(self._ocr_page, img, start_num + idx): (start_num + idx) for idx, img in enumerate(images)}
                
                for future in as_completed(futures):
                    page_num = futures[future]
                    try:
                        results.append((page_num, future.result()))
                    except Exception as e:
                        logger.error(f"Page {page_num} OCR failed: {e}")
            
            results.sort(key=lambda x: x[0])
            return "\n\n".join([f"--- Page {num} ---\n{text}" for num, text in results if text])
            
        except Exception as e:
            logger.error(f"Critical error in image-based OCR: {e}", exc_info=True)
            return f"[Error processing document: {str(e)}]"

    def _ocr_page(self, pil_image, page_num: int) -> str:
        """Perform OCR on a single PIL image"""
        img_byte_arr = io.BytesIO()
        pil_image.save(img_byte_arr, format='JPEG', quality=85) # Lossy compression for faster upload
        image = vision.Image(content=img_byte_arr.getvalue())
        response = self.client.document_text_detection(image=image)
        return response.full_text_annotation.text if response.full_text_annotation else ""

class SpeechService:
    """Service for handling speech-to-text transcription using Google Cloud Speech API"""

    def __init__(self, speech_client: speech.SpeechClient):
        self.client = speech_client

    def _convert_audio_to_wav(self, audio_bytes: bytes) -> bytes:
        """Convert audio to optimal format for Speech API"""
        from pydub import AudioSegment
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        audio = audio.set_channels(1).set_frame_rate(16000)
        wav_buffer = io.BytesIO()
        audio.export(wav_buffer, format="wav")
        return wav_buffer.getvalue()

    def transcribe(self, audio_bytes: bytes, language_code: str = "hi-IN") -> str:
        """Transcribe audio to text"""
        try:
            wav_audio = self._convert_audio_to_wav(audio_bytes)
            audio = speech.RecognitionAudio(content=wav_audio)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=True,
            )
            response = self.client.recognize(config=config, audio=audio)
            return " ".join([res.alternatives[0].transcript for res in response.results if res.alternatives])
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

class GoogleCloudClient:
    """Wrapper for Google Cloud APIs"""

    def __init__(self):
        self.vision_client = vision.ImageAnnotatorClient()
        self.speech_client = speech.SpeechClient()
        self.vision_service = VisionService(self.vision_client)
        self.speech_service = SpeechService(self.speech_client)

    def get_vision_service(self) -> VisionService:
        return self.vision_service

    def get_speech_service(self) -> SpeechService:
        return self.speech_service

_google_client = None

def get_google_client() -> GoogleCloudClient:
    global _google_client
    if _google_client is None:
        _google_client = GoogleCloudClient()
    return _google_client
