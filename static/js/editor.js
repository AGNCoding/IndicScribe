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
                        },
                        // Bind Ctrl+S for Save
                        save: {
                            key: 'S',
                            shortKey: true,
                            handler: () => {
                                const event = new CustomEvent('editor:save-to-drive');
                                document.dispatchEvent(event);
                                return false;
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
            saveBtn.setAttribute('title', 'Save Project (Ctrl+S)');
            saveBtn.innerHTML = '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M17 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z"/></svg>';
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

    enableAutoSave(callback, interval = 30000) {
        // interval in milliseconds (default 30 seconds)
        this.autoSaveCallback = callback;
        
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }

        // Trigger auto-save at regular intervals
        this.autoSaveInterval = setInterval(() => {
            if (this.currentProjectName && this.currentProjectId && callback) {
                callback(this.currentProjectName, this.getContents());
            }
        }, interval);

        console.log(`Auto-save enabled (interval: ${interval}ms)`);
    },

    disableAutoSave() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = null;
        }
        this.autoSaveCallback = null;
        console.log('Auto-save disabled');
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
