import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const client = axios.create({ baseURL: API_BASE });

export const api = {
  getProfile: (email) => client.get(`/profile/${encodeURIComponent(email)}`),
  upsertProfile: (data) => client.post('/profile', data),
  listStores: () => client.get('/stores'),
  listRecipes: () => client.get('/recipes'),
  sendChat: (data) => client.post('/chat', data),
  getCookedHistory: (userId) => client.get(`/cooked/${userId}`),
  logCooked: (data) => client.post('/cooked', data),
};