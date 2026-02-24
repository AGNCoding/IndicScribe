/**
 * API Module - Handles communication with the backend
 */

export const api = {
    async runOcr(file, pageStart = null, pageEnd = null) {
        const formData = new FormData();
        formData.append('file', file);
        if (pageStart !== null) {
            formData.append('page_start', pageStart);
            formData.append('page_end', pageEnd);
        }

        const response = await fetch('/api/ocr', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'OCR Request failed' }));
            throw new Error(error.detail || 'OCR failed');
        }

        return await response.json();
    },

    async fetchProjects() {
        const response = await fetch('/api/projects', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Failed to fetch projects' }));
            throw new Error(error.detail || 'Failed to fetch projects');
        }

        return await response.json();
    },

    async saveProject(projectName, content) {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: projectName,
                content: content
            })
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Failed to save project' }));
            throw new Error(error.detail || 'Failed to save project');
        }

        return await response.json();
    },

    async loadProject(fileId) {
        const response = await fetch(`/api/projects/${fileId}`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Failed to load project' }));
            throw new Error(error.detail || 'Failed to load project');
        }

        return await response.json();
    }
};
