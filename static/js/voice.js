/**
 * Voice Module - Handles audio recording and transcription
 */
import { ui } from './ui.js';
import { api } from './api.js';

export const voice = {
    mediaRecorder: null,
    audioChunks: [],
    isRecording: false,

    async start(langCode, onComplete) {
        if (this.isRecording) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (e) => this.audioChunks.push(e.data);

            this.mediaRecorder.onstop = async () => {
                ui.showSpinner('Transcribing...');
                try {
                    const blob = new Blob(this.audioChunks, { type: 'audio/webm' });
                    const result = await api.transcribeVoice(blob, langCode);
                    if (result.text) {
                        onComplete(result.text);
                        ui.notify('Transcription complete', 'success');
                    } else {
                        ui.notify('No voice detected', 'info');
                    }
                } catch (err) {
                    ui.notify(err.message, 'error');
                } finally {
                    ui.hideSpinner();
                    stream.getTracks().forEach(t => t.stop());
                }
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            this.updateButton(true);
        } catch (err) {
            ui.notify('Microphone access denied', 'error');
        }
    },

    stop() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            this.updateButton(false);
        }
    },

    updateButton(active) {
        const btn = document.getElementById('micBtn');
        const text = document.getElementById('micText');
        if (active) {
            btn.classList.add('recording', 'recording-pulse');
            text.textContent = 'Stop';
        } else {
            btn.classList.remove('recording', 'recording-pulse');
            text.textContent = 'Record';
        }
    }
};
