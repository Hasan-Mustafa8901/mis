import { X } from 'lucide-react';
export default function Modal({ open, title, children, onClose, width='max-w-4xl' }){
  if(!open) return null;
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4"><div className={`w-full ${width} max-h-[90vh] overflow-hidden rounded-3xl bg-white shadow-2xl`}><div className="flex items-center justify-between border-b border-slate-200 px-5 py-4"><h2 className="text-lg font-bold text-slate-950">{title}</h2><button onClick={onClose} className="rounded-full p-2 hover:bg-slate-100"><X size={20}/></button></div><div className="max-h-[calc(90vh-72px)] overflow-auto p-5">{children}</div></div></div>;
}
