export const currency = (value) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(value || 0));
export const number = (value) => new Intl.NumberFormat('en-IN').format(Number(value || 0));
export const compactDate = (value) => value ? String(value).slice(0, 10) : '—';
export const titleCase = (value='') => String(value).replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase());
export const pick = (obj, keys) => keys.reduce((acc, key) => ({ ...acc, [key]: obj?.[key] }), {});
