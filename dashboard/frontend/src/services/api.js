import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getStats = () => api.get('/stats');
export const getListings = (params) => api.get('/listings', { params });
export const getListing = (id) => api.get(`/listings/${id}`);
export const getDeals = (params) => api.get('/deals', { params });
export const getMarketStats = () => api.get('/market-stats');
export const getSellers = (params) => api.get('/sellers', { params });
export const getSeller = (id) => api.get(`/sellers/${id}`);
export const getAlerts = (params) => api.get('/alerts', { params });
export const getModels = () => api.get('/models');
export const getTrends = (days) => api.get('/trends', { params: { days } });

export default api;
