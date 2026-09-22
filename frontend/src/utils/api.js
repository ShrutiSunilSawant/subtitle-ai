/**
 * utils/api.js — API Client
 * ===========================
 * Centralized axios-based API calls to the FastAPI backend.
 */

import axios from "axios";

const BASE_URL = "/api/v1";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000, // 60s for long operations
});

/**
 * Upload a video file with progress tracking.
 * @param {File} file — The video file to upload
 * @param {function} onProgress — Callback(percent: number)
 * @returns {Promise<{job_id, filename, file_size_bytes, message}>}
 */
export async function uploadVideo(file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (e.total && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    },
  });

  return response.data;
}

/**
 * Start processing a job.
 * @param {object} options — { job_id, language, silence_threshold_db, burn_subtitles, ... }
 * @returns {Promise<StatusResponse>}
 */
export async function startProcessing(options) {
  const response = await api.post("/process", options);
  return response.data;
}

/**
 * Poll the status of a processing job.
 * @param {string} jobId
 * @returns {Promise<{status, progress_percent, current_step, error_message}>}
 */
export async function getStatus(jobId) {
  const response = await api.get(`/status/${jobId}`);
  return response.data;
}

/**
 * Get the full result of a completed job.
 * @param {string} jobId
 * @returns {Promise<ResultResponse>}
 */
export async function getResult(jobId) {
  const response = await api.get(`/result/${jobId}`);
  return response.data;
}

/**
 * Build download URLs for job outputs.
 */
export function getDownloadUrls(jobId) {
  return {
    video:      `${BASE_URL}/download/${jobId}/video`,
    srt:        `${BASE_URL}/download/${jobId}/srt`,
    transcript: `${BASE_URL}/download/${jobId}/transcript`,
  };
}
