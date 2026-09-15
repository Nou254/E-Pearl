import client from '../client';

export const authApi = {
  login: (data) => client.post('/auth/token/', data),
  register: (data) => client.post('/auth/register-customer/', data),
  refresh: (data) => client.post('/auth/token/refresh/', data),
  logout: () => client.post('/auth/logout/'),
  getProfile: () => client.get('/auth/me/'),
};