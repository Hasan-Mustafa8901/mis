import { api } from './apiClient';
export const getComplaints = (params) => api.get('/complaints/', params);
export const getComplaintStatuses = () => api.get('/complaints/statuses');
export const getComplaintFlags = () => api.get('/complaints/flags');
export const saveComplaint = (payload) => api.post('/complaints/save-complaint', payload);
export const updateComplaintStatus = (payload) => api.post('/complaints/update-status', payload);
export const updateComplaintFlag = (payload) => api.post('/complaints/update-flag', payload);
export const submitRemark = (payload) => api.post('/complaints/remarks', payload);
