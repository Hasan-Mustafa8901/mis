export default function Field({ label, children, className='' }){ return <label className={`block space-y-1.5 ${className}`}><span className="label">{label}</span>{children}</label>; }
export function Input(props){ return <input className="input" {...props} />; }
export function Select({ children, ...props }){ return <select className="input" {...props}>{children}</select>; }
export function Textarea(props){ return <textarea className="input min-h-24" {...props} />; }
