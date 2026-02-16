/**
 * Editor Module - Wraps Quill.js functionality
 */

export const editor = {
    quill: null,
    fontMap: {
        'en-US': 'Inter',
        'hi-IN': 'Noto Sans Devanagari',
        'sa-IN': 'Noto Sans Devanagari',
        'kn-IN': 'Noto Sans Kannada',
        'te-IN': 'Noto Sans Telugu'
    },

    init(containerId) {
        this.quill = new Quill(containerId, {
            theme: 'snow',
            placeholder: 'Start typing... or upload an image/PDF for OCR, or record audio for transcription',
            modules: {
                toolbar: [
                    [{ 'header': [1, 2, 3, false] }],
                    ['bold', 'italic', 'underline', 'strike'],
                    ['blockquote', 'code-block'],
                    [{ 'list': 'ordered' }, { 'list': 'bullet' }],
                    [{ 'font': [] }],
                    [{ 'align': [] }],
                    ['clean']
                ]
            }
        });
        return this.quill;
    },

    insertText(text) {
        if (!this.quill) return;
        const length = this.quill.getLength();
        this.quill.insertText(length, `\n${text}\n`);
        this.quill.setSelection(length + text.length + 2);
    },

    setFont(langCode) {
        if (!this.quill) return;
        const font = this.fontMap[langCode] || 'Inter';
        this.quill.format('font', font);
    },

    getText() {
        return this.quill ? this.quill.getText() : '';
    },

    getHtml() {
        return this.quill ? this.quill.root.innerHTML : '';
    }
};
