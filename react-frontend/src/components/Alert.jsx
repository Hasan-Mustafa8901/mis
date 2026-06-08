export default function Alert({ type='info', children }){
  const styles = type === 'error' ? 'border-red-200 bg-red-50 text-red-700' : type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-700';
  if(!children) return null;
  return <div className={`rounded-xl border px-4 py-3 text-sm ${styles}`}>{children}</div>;
}
