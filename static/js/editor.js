export const editor = {
    quill: null,
    currentProjectName: null,
    currentProjectId: null,
    autoSaveInterval: null,
    autoSaveCallback: null,

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
                        ['clean']
                    ],
                    handlers: {
                        'undo': () => {
                            this.quill.history.undo();
                        },
                        'redo': () => {
                            this.quill.history.redo();
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
                        },
                    }
                }
            }
        });

        // Ensure custom buttons have icons and titles
        const toolbar = this.quill.getModule('toolbar');
        const toolbarContainer = toolbar.container;

        const undoBtn = toolbarContainer.querySelector('.ql-undo');
        const redoBtn = toolbarContainer.querySelector('.ql-redo');

        if (undoBtn) undoBtn.setAttribute('title', 'Undo (Ctrl+Z)');
        if (redoBtn) redoBtn.setAttribute('title', 'Redo (Ctrl+Y)');

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

    enableAutoSave(callback, debounceTime = 2000) {
        // Trigger auto-save on change with debouncing
        this.autoSaveCallback = callback;

        if (this.autoSaveListener) {
            this.quill.off('text-change', this.autoSaveListener);
        }

        let timeout;
        this.autoSaveListener = (delta, oldDelta, source) => {
            if (source === 'user') {
                if (timeout) clearTimeout(timeout);
                timeout = setTimeout(() => {
                    if (this.currentProjectName && this.autoSaveCallback) {
                        this.autoSaveCallback(this.currentProjectName, this.getContents());
                    }
                }, debounceTime);
            }
        };

        this.quill.on('text-change', this.autoSaveListener);
        console.log(`Real-time auto-save enabled (debounce: ${debounceTime}ms)`);
    },

    disableAutoSave() {
        if (this.autoSaveListener) {
            this.quill.off('text-change', this.autoSaveListener);
            this.autoSaveListener = null;
        }
        this.autoSaveCallback = null;
        console.log('Real-time auto-save disabled');
    },

    clear() {
        if (this.quill) {
            this.quill.setText('');
        }
        this.currentProjectName = null;
        this.currentProjectId = null;
        this.disableAutoSave();
    }
};
