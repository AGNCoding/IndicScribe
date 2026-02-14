"""
Google Cloud API Client Wrapper
Handles initialization and management of Google Cloud Vision and Speech clients
"""
from google.cloud import vision, speech
import os
import io
import logging
import time
import pdfplumber
from pdf2image import convert_from_bytes
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class VisionService:
    """
    Advanced OCR Service for handling both images and PDFs efficiently.
    Implements hybrid approach: Direct text extraction for searchable PDFs,
    Image-based OCR for scanned PDFs.
    """

    def __init__(self, vision_client):
        """Initialize VisionService with a Vision API client"""
        self.client = vision_client
        self.max_workers = 3  # Parallel processing for PDF pages

    def _is_pdf(self, file_bytes):
        """Check if file is PDF by magic bytes"""
        return file_bytes[:4] == b'%PDF'

    def detect_text(self, file_bytes, page_start=None, page_end=None):
        """
        Main entry point: Detect and extract text from image or PDF.
        Intelligent routing based on file type and content.
        
        Args:
            file_bytes: Raw bytes from image or PDF
            page_start: Optional start page (1-indexed, for PDFs only)
            page_end: Optional end page (1-indexed inclusive, for PDFs only)
            
        Returns:
            str: Extracted text
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
                # Page parameters are ignored for images
                return self._extract_text_from_image(file_bytes)
            
        except Exception as e:
            logger.error(f"Error in detect_text: {type(e).__name__}: {str(e)}")
            return ""

    def _extract_text_from_image(self, file_bytes):
        """Extract text from image using Google Vision API"""
        try:
            image = vision.Image(content=file_bytes)
            response = self.client.document_text_detection(image=image)
            
            if response.error.message:
                logger.error(f"Vision API error: {response.error.message}")
                return ""
            
            if response.text_annotations:
                full_text = response.text_annotations[0].description
                logger.info(f"Extracted {len(full_text)} chars from image")
                return full_text if full_text else ""
            
            return ""
        except Exception as e:
            logger.error(f"Error extracting from image: {str(e)}")
            return ""

    def _is_text_quality_good(self, text):
        """
        Evaluate if extracted text is of acceptable quality.
        Detects CID-encoded garbage and other encoding issues.
        
        Returns True if text is usable, False if it should trigger Phase 2 fallback.
        """
        if not text or len(text.strip()) < 50:
            logger.warning(f"Text too short ({len(text)} chars) - likely poor extraction")
            return False
        
        # Count CID-encoded characters: (cid:xxxx) patterns indicate encoding issues
        cid_count = text.count('(cid:')
        cid_percentage = (cid_count / len(text)) * 100 if text else 0
        
        if cid_percentage > 5:  # If >5% of text is CID-encoded garbage
            logger.warning(f"Text is {cid_percentage:.1f}% CID-encoded garbage - failing extraction")
            return False
        
        # Count control characters and other non-printable characters
        control_char_count = sum(1 for c in text if ord(c) < 32 and c not in '\n\t\r')
        control_percentage = (control_char_count / len(text)) * 100 if text else 0
        
        if control_percentage > 10:  # If >10% control characters
            logger.warning(f"Text is {control_percentage:.1f}% control characters - failing extraction")
            return False
        
        logger.info(f"✓ Text quality acceptable: {cid_percentage:.1f}% CID, {control_percentage:.1f}% control chars")
        return True

    def _extract_text_from_pdf_hybrid(self, pdf_bytes, page_start=None, page_end=None):
        """
        Hybrid PDF OCR Strategy:
        1. Try direct text extraction (searchable PDFs) - INSTANT, NO API CALLS
        2. If poor quality detected, convert to images and use Vision API (scanned PDFs)
        
        Args:
            pdf_bytes: Raw PDF bytes
            page_start: Optional start page (1-indexed)
            page_end: Optional end page (1-indexed inclusive)
        """
        try:
            start_time = time.time()
            # Phase 1: Direct text extraction from PDF
            logger.info("Phase 1: Attempting direct text extraction...")
            extracted_text = self._extract_text_directly_from_pdf(pdf_bytes, page_start=page_start, page_end=page_end)
            
            # Evaluate extraction quality with intelligent detection
            if extracted_text and self._is_text_quality_good(extracted_text):
                phase1_time = time.time() - start_time
                logger.info(f"✓ Direct extraction successful: {len(extracted_text)} chars in {phase1_time:.2f}s")
                logger.info(f"TIMING: Phase 1 (Direct text extraction) completed in {phase1_time:.2f} seconds")
                return extracted_text
            
            # Phase 2: If direct extraction failed or quality poor, use image-based OCR
            logger.warning("Phase 1 failed quality check. Phase 2: Converting PDF to images for Vision API...")
            phase1_time = time.time() - start_time
            logger.info(f"TIMING: Phase 1 took {phase1_time:.2f} seconds, starting Phase 2...")
            
            phase2_start = time.time()
            result = self._extract_text_via_images(pdf_bytes, page_start=page_start, page_end=page_end)
            phase2_time = time.time() - phase2_start
            total_time = time.time() - start_time
            
            logger.info(f"TIMING: Phase 2 (Vision API OCR) completed in {phase2_time:.2f} seconds")
            logger.info(f"TIMING: Total hybrid OCR time: {total_time:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Error in hybrid PDF OCR: {str(e)}")
            return ""

    def _extract_text_directly_from_pdf(self, pdf_bytes, page_start=None, page_end=None):
        """
        Fast direct text extraction from searchable PDFs.
        Zero API calls, instant results.
        
        Args:
            pdf_bytes: Raw PDF bytes
            page_start: Optional start page (1-indexed)
            page_end: Optional end page (1-indexed inclusive)
        """
        try:
            start_time = time.time()
            logger.info("Extracting text directly from PDF...")
            pdf_file = io.BytesIO(pdf_bytes)
            text_parts = []
            
            with pdfplumber.open(pdf_file) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"PDF has {total_pages} pages")
                
                # Determine page range
                start = max(1, page_start) if page_start else 1
                end = min(total_pages, page_end) if page_end else total_pages
                
                if page_start or page_end:
                    logger.info(f"Processing pages {start} to {end}")
                
                for page_num in range(start, end + 1):
                    try:
                        page_start_time = time.time()
                        page = pdf.pages[page_num - 1]  # Convert 1-indexed to 0-indexed
                        page_text = page.extract_text()
                        page_time = time.time() - page_start_time
                        if page_text:
                            text_parts.append(f"--- Page {page_num} ---\n{page_text}\n")
                            logger.debug(f"Page {page_num}: {len(page_text)} chars extracted in {page_time:.3f}s")
                        else:
                            logger.debug(f"Page {page_num}: No text extracted in {page_time:.3f}s")
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num}: {str(e)}")
                        continue
            
            full_text = "\n".join(text_parts)
            elapsed_time = time.time() - start_time
            pages_processed = (end - start + 1) if page_start or page_end else total_pages
            logger.info(f"Direct extraction complete: {len(full_text)} total chars from {pages_processed} pages in {elapsed_time:.2f}s")
            return full_text
            
        except Exception as e:
            logger.error(f"Error in direct extraction: {str(e)}")
            return ""

    def _extract_text_via_images(self, pdf_bytes, page_start=None, page_end=None):
        """
        Convert PDF pages to images and use Vision API for OCR.
        Uses parallel processing for speed.
        
        Args:
            pdf_bytes: Raw PDF bytes
            page_start: Optional start page (1-indexed)
            page_end: Optional end page (1-indexed inclusive)
        """
        try:
            start_time = time.time()
            logger.info("Converting PDF to images...")
            
            conversion_start = time.time()
            # Convert all pages first, then slice if needed
            all_images = convert_from_bytes(pdf_bytes, dpi=300)  # High DPI for quality
            conversion_time = time.time() - conversion_start
            logger.info(f"Converted {len(all_images)} pages to images at 300 DPI in {conversion_time:.2f}s")
            
            # Determine page range
            total_pages = len(all_images)
            start = max(1, page_start) if page_start else 1
            end = min(total_pages, page_end) if page_end else total_pages
            
            if page_start or page_end:
                logger.info(f"Processing pages {start} to {end}")
            
            # Slice images if page range specified
            images_to_process = all_images[start-1:end]  # Convert 1-indexed to 0-indexed slice
            
            logger.info(f"TIMING: PDF to image conversion took {conversion_time:.2f} seconds")
            
            if not images_to_process:
                logger.warning("No images to process")
                return ""
            
            # Process images in parallel
            text_parts = []
            ocr_start = time.time()
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self._extract_text_from_pil_image, img, start + idx): (start + idx)
                    for idx, img in enumerate(images_to_process)
                }
                
                for future in as_completed(futures):
                    page_num = futures[future]
                    try:
                        text = future.result()
                        if text:
                            text_parts.append((page_num, text))
                            logger.info(f"Page {page_num}: {len(text)} chars extracted via Vision API")
                    except Exception as e:
                        logger.error(f"Error processing page {page_num}: {str(e)}")
            
            ocr_time = time.time() - ocr_start
            logger.info(f"TIMING: Vision API OCR on {len(images_to_process)} pages took {ocr_time:.2f} seconds")
            
            # Sort by page number and join
            text_parts.sort(key=lambda x: x[0])
            full_text = "\n".join([f"--- Page {num} ---\n{text}\n" for num, text in text_parts])
            
            elapsed_time = time.time() - start_time
            logger.info(f"Image-based OCR complete: {len(full_text)} total chars in {elapsed_time:.2f}s")
            logger.info(f"TIMING: Image extraction total time {elapsed_time:.2f}s (conversion: {conversion_time:.2f}s, OCR: {ocr_time:.2f}s)")
            return full_text
            
        except Exception as e:
            logger.error(f"Error in image-based OCR: {str(e)}")
            return ""

    def _extract_text_from_pil_image(self, pil_image, page_num):
        """Convert PIL image to Vision API format and extract text"""
        try:
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            # Use Vision API
            image = vision.Image(content=img_bytes)
            response = self.client.document_text_detection(image=image)
            
            if response.error.message:
                logger.warning(f"Vision API error on page {page_num}: {response.error.message}")
                return ""
            
            if response.text_annotations:
                return response.text_annotations[0].description
            
            return ""
        except Exception as e:
            logger.error(f"Error extracting from page {page_num} image: {str(e)}")
            return ""


class SpeechService:
    """Service for handling speech-to-text transcription using Google Cloud Speech API"""

    def __init__(self, speech_client):
        """
        Initialize SpeechService with a Speech API client
        
        Args:
            speech_client: google.cloud.speech.SpeechClient instance
        """
        self.client = speech_client

    def _convert_audio_to_wav(self, audio_bytes):
        """
        Convert incoming audio bytes to Mono, 16000Hz, WAV format.
        Supports multiple audio formats (WebM, MP3, OGG, etc.)
        
        Args:
            audio_bytes: Raw audio bytes in any supported format
            
        Returns:
            bytes: Converted WAV audio in Mono, 16000Hz format
        """
        try:
            # Lazy import pydub to avoid import issues
            import io
            from pydub import AudioSegment
            
            # Load audio from bytes
            # pydub automatically detects the format
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            
            # Convert to mono
            if audio.channels != 1:
                audio = audio.set_channels(1)
            
            # Set sample rate to 16000 Hz
            if audio.frame_rate != 16000:
                audio = audio.set_frame_rate(16000)
            
            # Export to WAV format
            wav_buffer = io.BytesIO()
            audio.export(
                wav_buffer,
                format="wav",
                parameters=["-q:a", "9", "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le"]
            )
            
            return wav_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error converting audio: {str(e)}")
            raise

    def transcribe(self, audio_bytes, language_code="hi-IN"):
        """
        Transcribe audio to text using Google Cloud Speech-to-Text API.
        
        Args:
            audio_bytes: Raw audio bytes (supports WebM, MP3, OGG, WAV, etc.)
            language_code: Language code (default: hi-IN for Hindi)
            
        Returns:
            str: Transcribed text from the audio
        """
        try:
            if not audio_bytes:
                return ""
            
            # Convert audio to WAV format (Mono, 16000Hz)
            wav_audio = self._convert_audio_to_wav(audio_bytes)
            
            # Create RecognitionAudio from converted bytes
            audio = speech.RecognitionAudio(content=wav_audio)
            
            # Configure the recognition request
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=True,
            )
            
            # Perform the transcription
            response = self.client.recognize(config=config, audio=audio)
            
            # Extract transcript from results
            transcript = []
            for result in response.results:
                if result.alternatives:
                    transcript.append(result.alternatives[0].transcript)
            
            return " ".join(transcript)
            
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            return ""


class GoogleCloudClient:
    """Wrapper for Google Cloud APIs (Vision and Speech)"""

    def __init__(self):
        """Initialize Google Cloud clients"""
        self.vision_client = vision.ImageAnnotatorClient()
        self.speech_client = speech.SpeechClient()
        self.vision_service = VisionService(self.vision_client)
        self.speech_service = SpeechService(self.speech_client)

    def get_vision_client(self):
        """Get the Vision API client"""
        return self.vision_client

    def get_vision_service(self):
        """Get the Vision Service for document text detection"""
        return self.vision_service

    def get_speech_client(self):
        """Get the Speech API client"""
        return self.speech_client

    def get_speech_service(self):
        """Get the Speech Service for audio transcription"""
        return self.speech_service

    def perform_ocr(self, image_content):
        """
        Perform Optical Character Recognition on image content
        
        Args:
            image_content: Image bytes or file path
            
        Returns:
            Vision API response with extracted text
        """
        image = vision.Image(content=image_content)
        response = self.vision_client.text_detection(image=image)
        return response

    def transcribe_audio(self, audio_content, language_code="en-US"):
        """
        Transcribe audio content to text using Speech-to-Text API
        
        Args:
            audio_content: Audio bytes
            language_code: Language code (default: en-US)
            
        Returns:
            Speech-to-Text API response with transcription
        """
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=language_code,
        )
        response = self.speech_client.recognize(config=config, audio=audio)
        return response


# Singleton instance
_google_client = None


def get_google_client():
    """Get or create the Google Cloud client singleton"""
    global _google_client
    if _google_client is None:
        _google_client = GoogleCloudClient()
    return _google_client
