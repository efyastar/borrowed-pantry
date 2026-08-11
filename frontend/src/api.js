import axios from 'axios';

const API_BASE = 'https://bm325ycol4ovpkay4pjvv4izoy0wvuza.lambda-url.us-east-2.on.aws';

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
  resolveDish: (dish) => client.post('/dish', { dish }),
  listCommunityTips: () => client.get('/community'),
  searchIngredients: (q) => client.get(`/ingredients/search?q=${encodeURIComponent(q)}`),
  submitTip: (data) => client.post('/reviews', data),
  storesNearby: (lat, lng) => client.post('/stores/nearby', { lat, lng }),
  ensureInventory: (storeId) => client.post('/stores/ensure-inventory', { store_id: storeId }),
};