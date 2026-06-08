import { Search, X } from 'lucide-react';

const getColumnKey = (column) => {
  if (typeof column === 'string') return column;

  return (
    column?.key ||
    column?.accessor ||
    column?.field ||
    column?.name ||
    column?.id ||
    ''
  );
};

const getColumnLabel = (column) => {
  if (typeof column === 'string') {
    return column
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  return (
    column?.label ||
    column?.header ||
    column?.title ||
    column?.name ||
    column?.key ||
    column?.accessor ||
    column?.field ||
    column?.id ||
    ''
  );
};

const getCellValue = (row, column, index) => {
  const key = getColumnKey(column);

  if (column && typeof column === 'object' && typeof column.render === 'function') {
    return column.render(row?.[key], row, index);
  }

  const value = row?.[key];

  if (value === null || value === undefined) return '';

  if (typeof value === 'boolean') return value ? 'Yes' : 'No';

  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return '';
    }
  }

  return value;
};

export default function DataTable({
  columns = [],
  rows = [],
  actions,
  columnFilters = {},
  onColumnFilterChange,
  showColumnFilters = false,
}) {
  const safeColumns = Array.isArray(columns) ? columns : [];
  const safeRows = Array.isArray(rows) ? rows : [];

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-left text-sm">
          <thead className="bg-slate-50 dark:bg-slate-900">
            <tr className="border-b border-slate-200 dark:border-slate-800">
              {safeColumns.map((column, index) => {
                const key = getColumnKey(column) || `column-${index}`;
                const label = getColumnLabel(column);

                return (
                  <th
                    key={key}
                    className="whitespace-nowrap px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400"
                  >
                    {label}
                  </th>
                );
              })}

              {actions ? (
                <th className="whitespace-nowrap px-4 py-4 text-right text-xs font-black uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                  Action
                </th>
              ) : null}
            </tr>

            {showColumnFilters ? (
              <tr className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
                {safeColumns.map((column, index) => {
                  const key = getColumnKey(column) || `column-${index}`;
                  const label = getColumnLabel(column);
                  const value = columnFilters?.[key] || '';

                  if (key === '__sno') {
                    return (
                      <th key={key} className="px-4 py-3">
                        <div className="h-10 w-16 rounded-lg border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900" />
                      </th>
                    );
                  }

                  return (
                    <th key={key} className="px-4 py-3">
                      <div className="relative min-w-[140px]">
                        <input
                          value={value}
                          onChange={(e) =>
                            onColumnFilterChange?.(key, e.target.value)
                          }
                          placeholder=""
                          className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 pr-9 text-sm font-semibold text-slate-900 outline-none transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100 dark:border-slate-700 dark:bg-slate-900 dark:text-white dark:focus:border-amber-400 dark:focus:ring-amber-400/10"
                          title={`Search ${label}`}
                        />

                        {value ? (
                          <button
                            type="button"
                            onClick={() => onColumnFilterChange?.(key, '')}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 transition hover:text-slate-700 dark:hover:text-white"
                            title={`Clear ${label}`}
                          >
                            <X size={14} />
                          </button>
                        ) : (
                          <Search
                            size={14}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400"
                          />
                        )}
                      </div>
                    </th>
                  );
                })}

                {actions ? <th className="px-4 py-3" /> : null}
              </tr>
            ) : null}
          </thead>

          <tbody>
            {safeRows.length ? (
              safeRows.map((row, rowIndex) => (
                <tr
                  key={row?.id || rowIndex}
                  className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900/70"
                >
                  {safeColumns.map((column, columnIndex) => {
                    const key = getColumnKey(column) || `column-${columnIndex}`;

                    return (
                      <td
                        key={key}
                        className="whitespace-nowrap px-4 py-4 font-semibold text-slate-700 dark:text-slate-200"
                      >
                        {getCellValue(row, column, rowIndex)}
                      </td>
                    );
                  })}

                  {actions ? (
                    <td className="whitespace-nowrap px-4 py-4 text-right">
                      {actions(row)}
                    </td>
                  ) : null}
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={safeColumns.length + (actions ? 1 : 0)}
                  className="px-4 py-10 text-center text-sm font-semibold text-slate-500 dark:text-slate-400"
                >
                  No records found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}