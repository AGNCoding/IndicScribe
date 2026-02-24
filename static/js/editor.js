export const editor = {
    quill: null,
    currentProjectName: null,
    currentProjectId: null,

    init(containerId) {
        this.quill = new Quill(containerId, {
            theme: 'snow',
            placeholder: 'Start typing... or upload an image/PDF for OCR, or record audio for transcription',
            modules: {
                history: {
                    delay: 2000,
                    maxStack: 500,
                    userOnly: true
                },
                toolbar: {
                    container: [
                        ['undo', 'redo'],
                        [{ 'header': [1, 2, 3, false] }],
                        ['bold', 'italic', 'underline', 'strike'],
                        ['blockquote', 'code-block'],
                        [{ 'list': 'ordered' }, { 'list': 'bullet' }],
                        [{ 'font': [] }],
                        [{ 'align': [] }],
                        ['clean'],
                        ['save-drive']
                    ],
                    handlers: {
                        'undo': () => {
                            this.quill.history.undo();
                        },
                        'redo': () => {
                            this.quill.history.redo();
                        },
                        'save-drive': () => {
                            const event = new CustomEvent('editor:save-to-drive');
                            document.dispatchEvent(event);
                        }
                    }
                },
                keyboard: {
                    bindings: {
                        // Explicitly bind Ctrl+Y for Redo
                        redo_y: {
                            key: 'Y',
                            shortKey: true,
                            handler: () => {
                                this.quill.history.redo();
                            }
                        }
                    }
                }
            }
        });

        // Ensure custom buttons have icons and titles
        const toolbar = this.quill.getModule('toolbar');
        const toolbarContainer = toolbar.container;

        const undoBtn = toolbarContainer.querySelector('.ql-undo');
        const redoBtn = toolbarContainer.querySelector('.ql-redo');
        const saveBtn = toolbarContainer.querySelector('.ql-save-drive');

        if (undoBtn) undoBtn.setAttribute('title', 'Undo (Ctrl+Z)');
        if (redoBtn) redoBtn.setAttribute('title', 'Redo (Ctrl+Y)');
        if (saveBtn) {
            saveBtn.setAttribute('title', 'Save to Drive');
            saveBtn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>';
            saveBtn.classList.add('flex', 'items-center', 'justify-center');
        }

        return this.quill;
    },

    insertText(text) {
        if (!this.quill) return;
        const length = this.quill.getLength();
        this.quill.insertText(length, `\n${text}\n`);
        this.quill.setSelection(length + text.length + 2);
    },

    setText(text) {
        if (!this.quill) return;
        this.quill.setText(text);
    },

    setContents(delta) {
        if (!this.quill) return;
        this.quill.setContents(delta);
    },

    getText() {
        return this.quill ? this.quill.getText() : '';
    },

    getHtml() {
        return this.quill ? this.quill.root.innerHTML : '';
    },

    getContents() {
        return this.quill ? this.quill.getContents() : null;
    },

    clear() {
        if (this.quill) {
            this.quill.setText('');
        }
        this.currentProjectName = null;
        this.currentProjectId = null;
    }
};
