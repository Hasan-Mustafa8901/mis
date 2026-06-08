import { api } from './apiClient';
export const getDailyReport = (params) => api.get('/report/', params);
export const downloadDailyReport = (params) => api.download('/reports/daily', params);
export const uploadEbd = (formData) => api.form('/mis/upload-ebd', formData);
export const getMisDetails = (params) => api.get('/mis/details', params);
export const toggleMis = (path, payload) => api.post(`/mis/${path}`, payload);
