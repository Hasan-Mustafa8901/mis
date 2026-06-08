import { api } from './apiClient';
export async function getMasters(){
  const [cars, variants, outlets, executives, accessories, dealerships, components] = await Promise.all([
    api.get('/cars'), api.get('/variants'), api.get('/outlets'), api.get('/sales-executives'), api.get('/accessories'), api.get('/dealerships'), api.get('/components')
  ]);
  return { cars, variants, outlets, executives, accessories, dealerships, components };
}
export const createDealership = (payload) => api.post('/dealership', payload);
export const createOutlet = (payload) => api.post('/outlets', payload);
export const createExecutive = (payload) => api.post('/sales-executive', payload);
