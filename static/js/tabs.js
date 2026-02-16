/**
 * Tabs Module - Manages multi-document state and tab rendering
 */
import { ui } from './ui.js';

export const tabs = {
    allFiles: [],
    activeFileIndex: -1,

    addFile(file, pages) {
        this.allFiles.push({ file, pages });
        return this.allFiles.length - 1;
    },

    removeFile(index) {
        this.allFiles.splice(index, 1);
        if (this.activeFileIndex === index) {
            this.activeFileIndex = this.allFiles.length > 0 ? Math.max(0, index - 1) : -1;
        } else if (this.activeFileIndex > index) {
            this.activeFileIndex--;
        }
    },

    getActiveFile() {
        return this.activeFileIndex !== -1 ? this.allFiles[this.activeFileIndex] : null;
    },

    clearAll() {
        this.allFiles = [];
        this.activeFileIndex = -1;
    },

    render(onSwitch, onRemove) {
        const container = document.getElementById('tabsContainer');
        if (!container) return;

        container.innerHTML = '';

        if (this.allFiles.length === 0) {
            ui.sourceViewer.innerHTML = '<div class="text-center text-gray-500 p-4"><p>Upload a PDF or image to see it here</p></div>';
            document.getElementById('runOcrBtn').disabled = true;
            return;
        }

        document.getElementById('runOcrBtn').disabled = false;

        this.allFiles.forEach((fileObj, index) => {
            const tab = document.createElement('div');
            tab.className = `doc-tab ${index === this.activeFileIndex ? 'active' : ''}`;
            tab.title = fileObj.file.name;

            const nameSpan = document.createElement('span');
            nameSpan.className = 'tab-name';
            nameSpan.textContent = fileObj.file.name;
            tab.appendChild(nameSpan);

            const closeBtn = document.createElement('span');
            closeBtn.className = 'close-tab';
            closeBtn.innerHTML = '&times;';
            closeBtn.onclick = (e) => {
                e.stopPropagation();
                onRemove(index);
            };
            tab.appendChild(closeBtn);

            tab.onclick = () => onSwitch(index);
            container.appendChild(tab);
        });
    }
};
