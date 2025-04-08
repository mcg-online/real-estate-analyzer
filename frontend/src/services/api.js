import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for authentication
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle common errors
    if (error.response) {
      if (error.response.status === 401) {
        // Unauthorized - redirect to login
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default {
  // Property endpoints
  getProperties: (filters = {}) => apiClient.get('/properties', { params: filters }),
  getProperty: (id) => apiClient.get(`/properties/${id}`),
  
  // Analysis endpoints
  getPropertyAnalysis: (id) => apiClient.get(`/analysis/property/${id}`),
  customizeAnalysis: (id, params) => apiClient.post(`/analysis/property/${id}`, params),
  
  // Market endpoints
  getTopMarkets: (params = {}) => apiClient.get('/markets/top', { params }),
  
  // Auth endpoints
  login: (credentials) => apiClient.post('/auth/login', credentials),
  register: (userData) => apiClient.post('/auth/register', userData),
  logout: () => apiClient.post('/auth/logout'),
};