import axios from 'axios';

const API_BASE = 'http://192.168.1.13:8000';

const client = axios.create({ baseURL: API_BASE });

export const api = {
  getProfile: (email) => client.get(`/profile/${encodeURIComponent(email)}`),
  upsertProfile: (data) => client.post('/profile', data),
  listStores: () => client.get('/stores'),
  listRecipes: () => client.get('/recipes'),
  sendChat: (data) => client.post('/chat', data),
  getCookedHistory: (userId) => client.get(`/cooked/${userId}`),
  logCooked: (data) => client.post('/cooked', data),
  getRecipeIngredients: (recipeId) => client.get(`/recipes/${recipeId}/ingredients`),
  getPlan: (data) => client.post('/plan', data),
};