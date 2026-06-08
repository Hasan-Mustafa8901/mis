import { api } from './apiClient';
import { authStorage } from '../lib/storage';
export async function login(payload){ const auth = await api.post('/auth/login', payload); authStorage.set(auth); return auth; }
export async function logout(){ authStorage.clear(); try { await api.post('/auth/logout', {}); } catch {} }
export async function registerUser(payload){ return api.post('/auth/register', payload); }
export async function getUsers(){ return api.get('/auth/users'); }
