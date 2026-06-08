import { useCallback, useEffect, useState } from 'react';
export function useAsync(fn, deps=[]){
  const [data, setData] = useState(null); const [loading, setLoading] = useState(false); const [error, setError] = useState('');
  const run = useCallback(async (...args) => { setLoading(true); setError(''); try { const result = await fn(...args); setData(result); return result; } catch(e){ setError(e.message || 'Something went wrong'); throw e; } finally { setLoading(false); } }, deps);
  useEffect(() => { run().catch(() => {}); }, [run]);
  return { data, loading, error, run, setData };
}
