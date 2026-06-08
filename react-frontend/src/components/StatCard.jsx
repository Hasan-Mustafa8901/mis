export default function StatCard({ label, value, caption, icon: Icon }) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-500">{label}</p>
          <p className="mt-2 text-3xl font-bold text-slate-950">{value}</p>
          {caption && <p className="mt-1 text-xs text-slate-500">{caption}</p>}
        </div>
        {Icon && (
          <div className="rounded-2xl bg-slate-950 p-3 text-white">
            <Icon size={20} />
          </div>
        )}
      </div>
    </div>
  );
}
