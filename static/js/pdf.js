/**
 * PDF Module - Handles PDF.js loading and rendering
 */
import { ui } from './ui.js';

export const pdf = {
    /**
     * Ensures pdfjsLib is loaded from CDN
     */
    async ensureLoaded() {
        if (typeof pdfjsLib !== 'undefined') return;

        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
            script.onload = () => {
                pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
                resolve();
            };
            script.onerror = () => reject(new Error('Failed to load PDF.js'));
            document.head.appendChild(script);
        });
    },

    async getPageCount(file) {
        await this.ensureLoaded();
        const fileBytes = await file.arrayBuffer();
        const doc = await pdfjsLib.getDocument(fileBytes).promise;
        return doc.numPages;
    },

    async renderPreview(file, container) {
        await this.ensureLoaded();
        try {
            const fileBytes = await file.arrayBuffer();
            const doc = await pdfjsLib.getDocument(fileBytes).promise;
            container.innerHTML = '';

            const pagesWrapper = document.createElement('div');
            pagesWrapper.className = 'flex flex-col gap-4 p-4';
            const scale = 1.2;

            for (let pageNum = 1; pageNum <= doc.numPages; pageNum++) {
                const page = await doc.getPage(pageNum);
                const viewport = page.getViewport({ scale });

                const pageDiv = document.createElement('div');
                pageDiv.className = 'border border-gray-300 rounded-lg overflow-hidden bg-white shadow-sm';

                const canvas = document.createElement('canvas');
                canvas.width = viewport.width;
                canvas.height = viewport.height;
                canvas.className = 'w-full block';

                const context = canvas.getContext('2d');
                await page.render({ canvasContext: context, viewport: viewport }).promise;

                const pageLabel = document.createElement('div');
                pageLabel.className = 'text-center text-xs text-gray-500 bg-gray-50 py-1 border-t border-gray-300';
                pageLabel.textContent = `Page ${pageNum} of ${doc.numPages}`;

                pageDiv.appendChild(canvas);
                pageDiv.appendChild(pageLabel);
                pagesWrapper.appendChild(pageDiv);
            }
            container.appendChild(pagesWrapper);
            ui.syncEditorHeight();
        } catch (err) {
            console.error('Error rendering PDF:', err);
            container.innerHTML = '<p class="text-red-500 p-4">Error displaying PDF preview</p>';
        }
    }
};
