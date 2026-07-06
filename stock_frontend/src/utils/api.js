import axios from 'axios';

export const API_BASE_URL = 'http://127.0.0.1:8000';

export function getAuthHeader(token) {
  return { headers: { Authorization: `Bearer ${token}` } };
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

export default apiClient;
