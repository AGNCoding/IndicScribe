/**
 * Transliteration Module - Handles script-wide conversion with Auto Detection
 */

export class Transliteration {
    constructor(editor) {
        this.editor = editor;
        this.currentScheme = 'devanagari';
        this.originalText = '';
    }

    /**
     * Set the original OCR text (should be called after OCR)
     */
    setOriginalText(text) {
        this.originalText = text;
    }

    /**
     * Detects the script scheme of a given text based on Unicode ranges
     */
    detectScheme(text) {
        if (!text || !text.trim()) return 'devanagari';

        // Sample first 500 characters for detection
        const sample = text.substring(0, 500);

        // Unicode Range Checks (only the 6 allowed languages)
        const ranges = {
            devanagari: /[\u0900-\u097F]/, // Sanskrit (Devanagari)
            kannada: /[\u0C80-\u0CFF]/,
            hindi: /[\u0900-\u097F]/, // Hindi (Devanagari)
            telugu: /[\u0C00-\u0C7F]/,
            tamil: /[\u0B80-\u0BFF]/,
            english: /[a-zA-Z]/
        };

        if (ranges.devanagari.test(sample)) return 'devanagari';
        if (ranges.kannada.test(sample)) return 'kannada';
        if (ranges.hindi.test(sample)) return 'hindi';
        if (ranges.telugu.test(sample)) return 'telugu';
        if (ranges.tamil.test(sample)) return 'tamil';
        if (ranges.english.test(sample)) return 'english';

        return 'devanagari'; // Default fallback
    }

    /**
     * Transliterates the entire editor content to a target scheme
     * @param {string} targetScheme - The scheme to convert to (e.g., 'kannada', 'iast')
     */
    async transliterateEditor(targetScheme) {
        // Always use the original OCR text for transliteration
        const text = this.originalText || this.editor.getText();
        if (!text.trim()) return;


        // If English, transliterate the original OCR text to ITRANS (English) using Sanscript
        if (targetScheme === 'english') {
            const sans = typeof Sanscript !== 'undefined' ? Sanscript : (typeof sanscript !== 'undefined' ? sanscript : null);
            if (!sans) {
                throw new Error('Sanscript library not loaded');
            }
            // Always use the original OCR text if available, fallback to editor text
            const sourceText = this.originalText && this.originalText.trim() ? this.originalText : this.editor.getText();
            if (!sourceText.trim()) return;
            const detectedFrom = this.detectScheme(sourceText);
            const converted = sans.t(sourceText, detectedFrom, 'itrans');
            this.editor.quill.setText(converted);
            this.currentScheme = 'english';
            return;
        }

        // For all other languages, always run transliteration (even if detectedFrom === mappedTarget)
        let mappedTarget = targetScheme;
        if (targetScheme === 'hindi') mappedTarget = 'devanagari';

        const sans = typeof Sanscript !== 'undefined' ? Sanscript : (typeof sanscript !== 'undefined' ? sanscript : null);
        if (!sans) {
            throw new Error('Sanscript library not loaded');
        }

        // Detect source script from original text
        const detectedFrom = this.detectScheme(text);

        try {
            const converted = sans.t(text, detectedFrom, mappedTarget);
            this.editor.quill.setText(converted);
            this.currentScheme = targetScheme;
            console.log(`Auto-Transliterated: ${detectedFrom} -> ${mappedTarget}`);
        } catch (err) {
            console.error('Transliteration failed:', err);
            throw err;
        }
    }

    /**
     * Helper to update UI when state changes
     */
    setCurrentScheme(scheme) {
        const selector = document.getElementById('scriptSelector');
        if (selector) selector.value = scheme;
    }
}
