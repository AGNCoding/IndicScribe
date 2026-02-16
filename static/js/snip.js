/**
 * Snip Module - Handles the document selection/snipping tool
 */
import { ui } from './ui.js';
import { api } from './api.js';

export const snip = {
    isSnipping: false,
    snipStart: null,
    snipRect: null,
    snipSelection: null,
    sourceViewer: document.getElementById('sourceViewer'),

    init(onComplete) {
        this.sourceViewer.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        this.sourceViewer.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.sourceViewer.addEventListener('mouseup', (e) => this.handleMouseUp(e));

        document.getElementById('cancelSnipOcrBtn').onclick = () => this.cancel();
        document.getElementById('confirmSnipOcrBtn').onclick = () => this.confirm(onComplete);

        const modal = document.getElementById('snipOcrModal');
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.cancel();
        });
    },

    createSnipRect(x, y) {
        const rect = document.createElement('div');
        rect.id = 'snipRect';
        Object.assign(rect.style, {
            position: 'absolute',
            border: '2px dashed #2563eb',
            background: 'rgba(59,130,246,0.1)',
            pointerEvents: 'none',
            zIndex: '100',
            left: `${x}px`,
            top: `${y}px`,
            width: '0px',
            height: '0px'
        });
        return rect;
    },

    handleMouseDown(e) {
        if (e.button !== 0) return;
        if (!(e.target.tagName === 'CANVAS' || e.target.tagName === 'IMG')) return;

        if (this.snipRect) this.snipRect.remove();

        this.isSnipping = true;
        this.snipStart = { x: e.offsetX, y: e.offsetY, target: e.target };
        this.snipRect = this.createSnipRect(e.offsetX, e.offsetY);
        this.sourceViewer.style.position = 'relative';
        this.sourceViewer.appendChild(this.snipRect);
    },

    handleMouseMove(e) {
        if (!this.isSnipping || !this.snipRect) return;
        const x = Math.min(e.offsetX, this.snipStart.x);
        const y = Math.min(e.offsetY, this.snipStart.y);
        const w = Math.abs(e.offsetX - this.snipStart.x);
        const h = Math.abs(e.offsetY - this.snipStart.y);

        Object.assign(this.snipRect.style, {
            left: `${x}px`,
            top: `${y}px`,
            width: `${w}px`,
            height: `${h}px`
        });
    },

    handleMouseUp(e) {
        if (!this.isSnipping || !this.snipRect) return;
        this.isSnipping = false;

        const x = Math.min(e.offsetX, this.snipStart.x);
        const y = Math.min(e.offsetY, this.snipStart.y);
        const w = Math.abs(e.offsetX - this.snipStart.x);
        const h = Math.abs(e.offsetY - this.snipStart.y);

        if (w < 10 || h < 10) {
            this.snipRect.remove();
            this.snipRect = null;
            return;
        }

        this.snipSelection = { x, y, w, h, target: this.snipStart.target };
        document.getElementById('snipOcrModal').classList.remove('hidden');
    },

    cancel() {
        document.getElementById('snipOcrModal').classList.add('hidden');
        if (this.snipRect) {
            this.snipRect.remove();
            this.snipRect = null;
        }
        this.snipSelection = null;
        this.isSnipping = false;
        this.snipStart = null;
    },

    async confirm(onComplete) {
        const selection = this.snipSelection;
        this.cancel();
        if (!selection) return;

        ui.showSpinner('Performing OCR on selection...');

        try {
            const target = selection.target;
            const displayRect = target.getBoundingClientRect();
            const scaleX = (target.naturalWidth || target.width) / displayRect.width;
            const scaleY = (target.naturalHeight || target.height) / displayRect.height;

            const canvas = document.createElement('canvas');
            canvas.width = Math.round(selection.w * scaleX);
            canvas.height = Math.round(selection.h * scaleY);

            const ctx = canvas.getContext('2d');
            ctx.drawImage(
                target,
                Math.round(selection.x * scaleX), Math.round(selection.y * scaleY),
                canvas.width, canvas.height,
                0, 0, canvas.width, canvas.height
            );

            const blob = await new Promise(res => canvas.toBlob(res, 'image/png'));
            if (!blob) throw new Error('Failed to capture selection');

            const result = await api.runOcr(blob);
            onComplete(result.text);
            ui.notify('Selection OCR complete', 'success');
        } catch (err) {
            ui.notify(err.message, 'error');
            onComplete(`[Error: ${err.message}]`);
        } finally {
            ui.hideSpinner();
        }
    }
};
