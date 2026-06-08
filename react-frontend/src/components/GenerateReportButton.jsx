import { useState } from 'react';
import { FileText, X } from 'lucide-react';
import { generateVisualMisReportPdf } from '../reports/visualMisReportPdf';

const REPORT_OPTIONS = [
  {
    key: 'weekly',
    label: 'Weekly Report',
    description: 'Last 7 days / selected week style report',
  },
  {
    key: 'monthly',
    label: 'Monthly Report',
    description: 'Current selected month style report',
  },
  {
    key: 'quarterly',
    label: 'Quarterly Report',
    description: 'Quarter-wise management report',
  },
  {
    key: 'annual',
    label: 'Annual Report',
    description: 'Full-year executive report',
  },
];

export default function GenerateReportButton({
  reportData,
  reportTitle = 'Automobile Sales Audit MIS Report',
}) {
  const [open, setOpen] = useState(false);
  const [generating, setGenerating] = useState(false);

  async function handleGenerate(periodType) {
    try {
      setGenerating(true);

      await generateVisualMisReportPdf({
        reportData: reportData || {},
        periodType,
        reportTitle,
      });

      setOpen(false);
    } catch (error) {
      console.error('PDF report generation failed:', error);
      alert(error?.message || 'Unable to generate report.');
    } finally {
      setGenerating(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-amber-400 px-5 text-sm font-black uppercase tracking-wide text-slate-950 shadow-sm transition hover:bg-amber-300"
      >
        <FileText size={16} />
        Generate Report
      </button>

      {open ? (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-3xl border border-slate-800 bg-slate-950 p-6 shadow-2xl">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.35em] text-amber-300">
                  Report Generator
                </p>
                <h2 className="mt-2 text-2xl font-black text-white">
                  Generate Visual MIS Report
                </h2>
                <p className="mt-2 text-sm font-semibold leading-6 text-slate-400">
                  Select a period. The PDF will be created through a vector PDF engine,
                  so it does not depend on browser screenshots or print rendering.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setOpen(false)}
                disabled={generating}
                className="rounded-xl border border-slate-800 p-2 text-slate-400 transition hover:bg-slate-900 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                <X size={18} />
              </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {REPORT_OPTIONS.map((option) => (
                <button
                  key={option.key}
                  type="button"
                  disabled={generating}
                  onClick={() => handleGenerate(option.key)}
                  className="rounded-2xl border border-slate-800 bg-slate-900/70 px-5 py-5 text-left transition hover:border-amber-400 hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <p className="text-base font-black text-white">
                    {option.label}
                  </p>
                  <p className="mt-2 text-xs font-bold leading-5 text-slate-500">
                    {option.description}
                  </p>
                </button>
              ))}
            </div>

            {generating ? (
              <div className="mt-5 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm font-bold text-amber-200">
                Generating visual PDF report. Please wait...
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  );
}
