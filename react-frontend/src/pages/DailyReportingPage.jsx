import { Download, RefreshCw, Search, X, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import Alert from '../components/Alert';
import Button from '../components/Button';
import Field, { Input, Select } from '../components/Field';
import Loader from '../components/Loader';
import PageHeader from '../components/PageHeader';
import { useMasters } from '../context/MasterDataContext';
import { api } from '../services/apiClient';
import { downloadDailyReport, getDailyReport } from '../services/reportService';

const today = new Date().toISOString().slice(0, 10);

const addDays = (dateString, days) => {
  const d = new Date(dateString);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
};

const formatDate = (value) => {
  if (!value) return '—';

  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;

  return d.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
};

const cleanNumber = (value) => {
  const n = Number(value || 0);
  return Number.isFinite(n) ? n : 0;
};

const getCellValue = (row, key) => {
  const value = row?.[key];
  return value === null || value === undefined ? 0 : value;
};

const titleMap = {
  total_count: 'Total Count',
  files_received: 'Files Received',
  files_pending: 'Files Pending',
  files_out_of_scope: 'Files Out Of Scope',
  files_to_be_verified: 'Files To Be Verified',
  files_incomplete: 'Files Incomplete',
  files_verified: 'Files Verified',
  files_approved: 'Files Approved',
  files_rejected: 'Files Rejected',
  files_in_mis: 'Files in MIS',
  files_scanned: 'Files Scanned',
  files_not_verified: 'Files Not Verified',
  rejected_files_delivered: 'Rejected Files Delivered',
};

const rangeOptions = [
  { value: 'today', label: `Today (${formatDate(today)})` },
  { value: 'yesterday', label: `Yesterday (${formatDate(addDays(today, -1))})` },
  { value: 'last7', label: 'Last 7 Days' },
  { value: 'last15', label: 'Last 15 Days' },
  { value: 'last30', label: '1 Month' },
  { value: 'last60', label: '2 Months' },
  { value: 'last90', label: '3 Months' },
  { value: 'custom', label: 'Custom Date Range' },
];

const tableColumns = {
  booking: [
    { key: 'date', label: 'Booking Date', type: 'date' },
    { key: 'total_count', label: 'Total Count' },
    { key: 'files_received', label: 'Files Received' },
    { key: 'files_pending', label: 'Files Pending', highlightWhenPositive: true },
    { key: 'files_out_of_scope', label: 'Files Out of Scope' },
    { key: 'files_to_be_verified', label: 'Files To Be Verified' },
    { key: 'files_incomplete', label: 'Files Incomplete', highlightWhenPositive: true },
    { key: 'files_scanned', label: 'Files Scanned', highlightWhenPositive: true },
    { key: 'files_in_mis', label: 'Files in MIS', highlightWhenPositive: true },
    { key: 'files_approved', label: 'Approved' },
    { key: 'files_rejected', label: 'Rejected' },
    { key: 'files_not_verified', label: 'Files Not Verified' },
  ],
  delivery: [
    { key: 'date', label: 'Delivery Date', type: 'date' },
    { key: 'total_count', label: 'Total Count' },
    { key: 'files_received', label: 'Files Received' },
    { key: 'files_pending', label: 'Files Pending', highlightWhenPositive: true },
    { key: 'files_out_of_scope', label: 'Files Out of Scope' },
    { key: 'files_to_be_verified', label: 'Files To Be Verified' },
    { key: 'files_incomplete', label: 'Files Incomplete', highlightWhenPositive: true },
    { key: 'files_scanned', label: 'Files Scanned', highlightWhenPositive: true },
    { key: 'files_in_mis', label: 'Files in MIS', highlightWhenPositive: true },
    { key: 'files_verified', label: 'Files Verified' },
    { key: 'rejected_files_delivered', label: 'Rejected Files Delivered' },
  ],
};

const detailBaseColumns = [
  { key: 'select', label: 'Select' },
  { key: 'sr_no', label: 'S.No' },
  { key: 'date', label: 'Date' },
  { key: 'customer_name', label: 'Customer Name' },
  { key: 'customer_mobile', label: 'Mobile' },
  { key: 'car_model', label: 'Car Model' },
  { key: 'team_leader', label: 'TL' },
  { key: 'receiving_date', label: 'Receiving Date' },
  { key: 'out_of_scope_reason', label: 'Out of Scope Reason' },
  { key: 'approved', label: 'Approved' },
  { key: 'rejection_reason', label: 'Rejection Reason' },
  { key: 'scanning_date', label: 'Scanned Date' },
  { key: 'entry_date', label: 'MIS Entry' },
  { key: 'incomplete', label: 'Incomplete' },
  { key: 'incomplete_remarks', label: 'Incomplete Remarks' },
];

const deriveRows = (rows = []) => {
  return rows.map((row) => {
    const filesToBeVerified = Math.max(
      cleanNumber(row.files_received) - cleanNumber(row.files_out_of_scope),
      0
    );

    const filesVerified = Math.max(
      filesToBeVerified - cleanNumber(row.files_incomplete),
      0
    );

    return {
      ...row,
      files_to_be_verified: filesToBeVerified,
      files_verified: filesVerified,
    };
  });
};

const ensureTodayRow = (rows = []) => {
  const exists = rows.some((row) => row.date === today);

  if (exists) return rows;

  return [
    ...rows,
    {
      date: today,
      is_placeholder: false,
      total_count: 0,
      files_received: 0,
      files_pending: 0,
      files_out_of_scope: 0,
      files_to_be_verified: 0,
      files_incomplete: 0,
      files_scanned: 0,
      files_in_mis: 0,
      files_verified: 0,
      files_approved: 0,
      files_rejected: 0,
      files_not_verified: 0,
      rejected_files_delivered: 0,
    },
  ].sort((a, b) => String(a.date).localeCompare(String(b.date)));
};

const getRangeDates = (range, customFrom, customTo) => {
  switch (range) {
    case 'today':
      return { from: today, to: today };

    case 'yesterday': {
      const y = addDays(today, -1);
      return { from: y, to: y };
    }

    case 'last7':
      return { from: addDays(today, -6), to: today };

    case 'last15':
      return { from: addDays(today, -14), to: today };

    case 'last30':
      return { from: addDays(today, -29), to: today };

    case 'last60':
      return { from: addDays(today, -59), to: today };

    case 'last90':
      return { from: addDays(today, -89), to: today };

    case 'custom':
    default:
      return {
        from: customFrom || today,
        to: customTo || today,
      };
  }
};

const DetailDialog = ({
  open,
  onClose,
  title,
  stage,
  column,
  rows,
  selectedIds,
  setSelectedIds,
  search,
  setSearch,
  onRefresh,
  onDeleteSelected,
  onAction,
}) => {
  const filteredRows = useMemo(() => {
    const text = String(search || '').trim().toLowerCase();

    if (!text) return rows;

    return rows.filter((row) =>
      Object.values(row || {})
        .map((value) => String(value || '').toLowerCase())
        .join(' ')
        .includes(text)
    );
  }, [rows, search]);

  if (!open) return null;

  const showReceivedAction = column === 'total_count';
  const showOosAction = column === 'files_received';
  const showApprovalAction = stage === 'booking' && column === 'files_to_be_verified';
  const showScannedAction = column === 'files_scanned';

  const detailColumns = [
    ...detailBaseColumns,
    ...(showReceivedAction ? [{ key: 'received_action', label: 'Received' }] : []),
    ...(showOosAction ? [{ key: 'oos_action', label: 'Out of Scope' }] : []),
    ...(showApprovalAction
      ? [
          { key: 'approve_action', label: 'Approve' },
          { key: 'reject_action', label: 'Reject' },
        ]
      : []),
    ...(showScannedAction ? [{ key: 'scanned_action', label: 'Scanned' }] : []),
  ];

  const toggleSelected = (id, checked) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);

      if (checked) next.add(id);
      else next.delete(id);

      return next;
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm">
      <div className="max-h-[92vh] w-[98vw] max-w-[1800px] overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-950">
        <div className="flex items-center gap-3 border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">{title}</h2>
            <p className="text-xs font-semibold text-slate-400">
              {filteredRows.length} record{filteredRows.length === 1 ? '' : 's'}
            </p>
          </div>

          <div className="ml-auto w-1/2">
            <Input
              placeholder="Search..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-slate-200 p-2 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <X size={18} />
          </button>
        </div>

        <div className="max-h-[58vh] overflow-auto">
          <table className="w-full min-w-[1800px] border-separate border-spacing-0 text-sm">
            <thead className="sticky top-0 z-10">
              <tr>
                {detailColumns.map((col) => (
                  <th
                    key={col.key}
                    className="border-b border-r border-slate-200 bg-slate-100 px-3 py-2 text-center text-[11px] font-bold uppercase tracking-wide text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300"
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {!filteredRows.length ? (
                <tr>
                  <td
                    colSpan={detailColumns.length}
                    className="px-4 py-12 text-center text-slate-400"
                  >
                    📭 No records found
                  </td>
                </tr>
              ) : (
                filteredRows.map((row, index) => (
                  <tr
                    key={row.id || index}
                    className={
                      index % 2
                        ? 'bg-slate-50/80 dark:bg-slate-900/50'
                        : 'bg-white dark:bg-slate-950'
                    }
                  >
                    <td className="border-b border-r border-slate-200 px-3 py-2 text-center dark:border-slate-800">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(row.id)}
                        onChange={(e) => toggleSelected(row.id, e.target.checked)}
                      />
                    </td>

                    <td className="border-b border-r border-slate-200 bg-indigo-50 px-3 py-2 text-center font-mono font-bold text-indigo-600 dark:border-slate-800 dark:bg-indigo-400/10 dark:text-indigo-300">
                      {index + 1}
                    </td>

                    <td className="border-b border-r border-slate-200 px-3 py-2 text-center text-slate-700 dark:border-slate-800 dark:text-slate-200">
                      {formatDate(row.date)}
                    </td>

                    <td className="border-b border-r border-slate-200 px-3 py-2 text-left font-semibold text-slate-800 dark:border-slate-800 dark:text-slate-100">
                      {row.customer_name || '—'}
                    </td>

                    <td className="border-b border-r border-slate-200 px-3 py-2 text-center text-slate-700 dark:border-slate-800 dark:text-slate-200">
                      {row.customer_mobile || '—'}
                    </td>

                    <td className="border-b border-r border-slate-200 px-3 py-2 text-center text-slate-700 dark:border-slate-800 dark:text-slate-200">
                      {row.car_model || '—'}
                    </td>

                    <td className="border-b border-r border-slate-200 px-3 py-2 text-center text-slate-700 dark:border-slate-800 dark:text-slate-200">
                      {row.team_leader || '—'}
                    </td>

                    <td className="border-b border-r border-slate-200 px-3 py-2 text-center text-slate-700 dark:border-slate-800 dark:text-slate-200">
                      {formatDate(row.receiving_date)}
                    </td>

                    <td className="border-b border-r border-slate-200 px-3 py-2 text-left text-slate-700 dark:border-slate-800 dark:text-slate-200">
                      {row.out_of_scope_reason || '—'}
                    </td>

                    <td className="border-b border-r border-slate-200 px-3 py-2 text-center dark:border-slate-800">
                      <input type="checkbox" checked={Boolean(row.approved)} disabled readOnly />
                    </td>

                    <td className="border-b border-r border-slate-200 px-3 py-2 text-left text-slate-700 dark:border-slate-800 dark:text-slate-200">
                      {row.rejection_reason || '—'}
                    </td>

                    <td className="border-b border-r border-slate-200 px-3 py-2 text-center text-slate-700 dark:border-slate-800 dark:text-slate-200">
                      {formatDate(row.scanning_date)}
                    </td>

                    <td className="border-b border-r border-slate-200 px-3 py-2 text-center text-slate-700 dark:border-slate-800 dark:text-slate-200">
                      {formatDate(row.entry_date)}
                    </td>

                    <td className="border-b border-r border-slate-200 px-3 py-2 text-center dark:border-slate-800">
                      <input type="checkbox" checked={Boolean(row.incomplete)} disabled readOnly />
                    </td>

                    <td className="border-b border-r border-slate-200 px-3 py-2 text-left text-slate-700 dark:border-slate-800 dark:text-slate-200">
                      {row.incomplete_remarks || '—'}
                    </td>

                    {showReceivedAction && (
                      <td className="border-b border-r border-slate-200 px-3 py-2 dark:border-slate-800">
                        <div className="flex items-center gap-2">
                          <Input
                            type="date"
                            defaultValue={row.receiving_date || ''}
                            onChange={(e) => {
                              row.__receiving_date = e.target.value;
                            }}
                          />
                          <input
                            type="checkbox"
                            checked={Boolean(row.received)}
                            onChange={(e) =>
                              onAction('received', row, {
                                value: e.target.checked,
                                receiving_date: row.__receiving_date || row.receiving_date || '',
                              })
                            }
                          />
                        </div>
                      </td>
                    )}

                    {showOosAction && (
                      <td className="border-b border-r border-slate-200 px-3 py-2 dark:border-slate-800">
                        <div className="flex items-center gap-2">
                          <Input
                            placeholder="Reason"
                            defaultValue={row.out_of_scope_reason || ''}
                            onChange={(e) => {
                              row.__out_of_scope_reason = e.target.value;
                            }}
                          />
                          <input
                            type="checkbox"
                            checked={Boolean(row.out_of_scope)}
                            onChange={(e) =>
                              onAction('oos', row, {
                                value: e.target.checked,
                                reason: row.__out_of_scope_reason || row.out_of_scope_reason || '',
                              })
                            }
                          />
                        </div>
                      </td>
                    )}

                    {showApprovalAction && (
                      <>
                        <td className="border-b border-r border-slate-200 px-3 py-2 text-center dark:border-slate-800">
                          <input
                            type="checkbox"
                            checked={Boolean(row.approved)}
                            disabled={Boolean(row.rejected)}
                            onChange={(e) =>
                              onAction('approve', row, {
                                value: e.target.checked,
                              })
                            }
                          />
                        </td>

                        <td className="border-b border-r border-slate-200 px-3 py-2 dark:border-slate-800">
                          <div className="flex items-center gap-2">
                            <Input
                              placeholder="Reason"
                              defaultValue={row.rejection_reason || ''}
                              onChange={(e) => {
                                row.__rejection_reason = e.target.value;
                              }}
                            />
                            <input
                              type="checkbox"
                              checked={Boolean(row.rejected)}
                              disabled={Boolean(row.approved)}
                              onChange={(e) =>
                                onAction('reject', row, {
                                  value: e.target.checked,
                                  reason: row.__rejection_reason || row.rejection_reason || '',
                                })
                              }
                            />
                          </div>
                        </td>
                      </>
                    )}

                    {showScannedAction && (
                      <td className="border-b border-r border-slate-200 px-3 py-2 dark:border-slate-800">
                        <div className="flex items-center gap-2">
                          <Input
                            type="date"
                            defaultValue={row.scanning_date || ''}
                            onChange={(e) => {
                              row.__scanning_date = e.target.value;
                            }}
                          />
                          <input
                            type="checkbox"
                            checked={Boolean(row.scanned)}
                            onChange={(e) =>
                              onAction('scanned', row, {
                                value: e.target.checked,
                                scanning_date: row.__scanning_date || row.scanning_date || '',
                              })
                            }
                          />
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 px-5 py-4 dark:border-slate-800">
          <p className="text-xs font-bold text-slate-400">
            {filteredRows.length} record{filteredRows.length === 1 ? '' : 's'}
          </p>

          <div className="flex gap-2">
            <Button variant="secondary" onClick={onDeleteSelected}>
              <Trash2 size={16} />
              Delete Selected
            </Button>

            <Button variant="secondary" onClick={onRefresh}>
              <RefreshCw size={16} />
              Refresh
            </Button>

            <Button onClick={onClose}>Close</Button>
          </div>
        </div>
      </div>
    </div>
  );
};

const ReportTable = ({ stage, rows, onCellClick }) => {
  const columns = tableColumns[stage];

  const footerColumns = columns.filter((col) => col.key !== 'date');

  const getTotal = (key) => {
    return rows.reduce((sum, row) => sum + cleanNumber(row[key]), 0);
  };

  const footerRow = {
    date: null,
    is_footer: true,
  };

  footerColumns.forEach((col) => {
    footerRow[col.key] = getTotal(col.key);
  });

  const hasRows = Array.isArray(rows) && rows.length > 0;

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="max-h-[460px] overflow-auto">
        <table className="w-full min-w-[1250px] border-separate border-spacing-0 text-sm">
          <thead className="sticky top-0 z-20">
            <tr>
              {columns.map((col, index) => (
                <th
                  key={col.key}
                  className={`border-b border-slate-200 bg-slate-100 px-4 py-3 text-center text-[11px] font-black uppercase tracking-widest text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 ${
                    index === 0
                      ? 'sticky left-0 z-30 border-r border-slate-200 dark:border-slate-800'
                      : ''
                  }`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {!hasRows ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-12 text-center text-sm font-bold text-slate-400"
                >
                  No data available
                </td>
              </tr>
            ) : (
              rows.map((row, index) => {
                const isToday = row.date === today;

                return (
                  <tr
                    key={`${stage}-${row.date || 'no-date'}-${index}`}
                    className={`transition ${
                      isToday
                        ? 'bg-blue-50/80 dark:bg-blue-950/20'
                        : index % 2
                          ? 'bg-slate-50/80 dark:bg-slate-900/40'
                          : 'bg-white dark:bg-slate-950'
                    }`}
                  >
                    {columns.map((col, colIndex) => {
                      const rawValue = row[col.key];

                      const value =
                        col.type === 'date'
                          ? formatDate(rawValue)
                          : getCellValue(row, col.key);

                      const numericValue = cleanNumber(row[col.key]);

                      const highlight =
                        col.highlightWhenPositive && numericValue > 0;

                      const isDateColumn = col.key === 'date';

                      return (
                        <td
                          key={col.key}
                          onClick={() => {
                            if (!isDateColumn) {
                              onCellClick(stage, row, col.key);
                            }
                          }}
                          className={`border-b border-slate-200 px-4 py-3 text-center font-bold dark:border-slate-800 ${
                            colIndex === 0
                              ? 'sticky left-0 z-10 border-r border-slate-200 bg-inherit text-slate-700 dark:border-slate-800 dark:text-slate-200'
                              : ''
                          } ${
                            isDateColumn
                              ? 'whitespace-nowrap text-slate-700 dark:text-slate-200'
                              : 'cursor-pointer text-slate-800 hover:bg-amber-50 dark:text-slate-100 dark:hover:bg-amber-400/10'
                          } ${
                            highlight
                              ? 'bg-orange-50 text-orange-700 dark:bg-orange-400/10 dark:text-orange-300'
                              : ''
                          }`}
                        >
                          {value}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            )}
          </tbody>

          <tfoot className="sticky bottom-0 z-20">
            <tr>
              <td className="sticky left-0 z-30 border-t border-r border-slate-300 bg-slate-200 px-4 py-3 text-center text-[11px] font-black uppercase tracking-widest text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
                Total
              </td>

              {footerColumns.map((col) => (
                <td
                  key={col.key}
                  onClick={() => onCellClick(stage, footerRow, col.key)}
                  className="cursor-pointer border-t border-slate-300 bg-slate-200 px-4 py-3 text-center font-black text-slate-900 hover:bg-amber-100 dark:border-slate-700 dark:bg-slate-900 dark:text-white dark:hover:bg-amber-400/10"
                >
                  {getTotal(col.key)}
                </td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
};

export default function DailyReportingPage() {
  const masters = useMasters();

  const [filters, setFilters] = useState({
    range: 'today',
    report_from: today,
    report_to: today,
    dealership_id: '',
    outlet_id: '',
  });

  const [bookingRows, setBookingRows] = useState([]);
  const [deliveryRows, setDeliveryRows] = useState([]);

  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState('');

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailRows, setDetailRows] = useState([]);
  const [detailContext, setDetailContext] = useState(null);
  const [detailSearch, setDetailSearch] = useState('');
  const [selectedIds, setSelectedIds] = useState(new Set());

  const dealerships = Array.isArray(masters.dealerships) ? masters.dealerships : [];
  const outlets = Array.isArray(masters.outlets) ? masters.outlets : [];

  const filteredOutlets = filters.dealership_id
    ? outlets.filter(
        (outlet) =>
          String(outlet.dealership_id || outlet.dealershipId || '') ===
          String(filters.dealership_id)
      )
    : outlets;

  const applyRange = (range, customFrom = filters.report_from, customTo = filters.report_to) => {
    const dates = getRangeDates(range, customFrom, customTo);

    setFilters((prev) => ({
      ...prev,
      range,
      report_from: dates.from,
      report_to: dates.to,
    }));

    return dates;
  };

  async function load(customFilters = filters) {
    setLoading(true);
    setError('');

    try {
      const reportData = await getDailyReport({
        report_from: customFilters.report_from,
        report_to: customFilters.report_to,
        dealership_id: customFilters.dealership_id || undefined,
        outlet_id: customFilters.outlet_id || undefined,
      });

      const bookings = ensureTodayRow(deriveRows(reportData?.bookings || []));
      const deliveries = ensureTodayRow(deriveRows(reportData?.deliveries || []));

      setBookingRows(bookings);
      setDeliveryRows(deliveries);
    } catch (e) {
      setError(e.message || 'Unable to load daily report.');
    } finally {
      setLoading(false);
    }
  }

  async function openDetail(stage, row, column) {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailRows([]);
    setSelectedIds(new Set());
    setDetailSearch('');

    const label = titleMap[column] || column;
    const dateText = row.is_footer ? 'All Dates' : formatDate(row.date);

    const context = {
      stage,
      row,
      column,
      is_footer: Boolean(row.is_footer),
      title: `${label} — ${dateText}`,
    };

    setDetailContext(context);

    try {
      const params = {
        record_date: row.date,
        stage,
        column,
        outlet_id: filters.outlet_id || undefined,
        dealership_id: filters.dealership_id || undefined,
        is_footer: Boolean(row.is_footer),
        start_date: filters.report_from,
        end_date: filters.report_to,
      };

      const rows = await api.get('/mis/details', params);

      setDetailRows(Array.isArray(rows) ? rows : []);
    } catch (e) {
      setError(e.message || 'Unable to load report details.');
      setDetailRows([]);
    } finally {
      setDetailLoading(false);
    }
  }

  async function refreshDetail() {
    if (!detailContext) return;

    await openDetail(detailContext.stage, detailContext.row, detailContext.column);
  }

  async function handleDetailAction(type, row, extra = {}) {
    try {
      if (type === 'received') {
        await api.post('/mis/toggle-received', {
          mis_record_id: row.id,
          receiving_date: extra.receiving_date,
          value: extra.value,
        });
      }

      if (type === 'oos') {
        await api.post('/mis/toggle-oos', {
          mis_record_id: row.id,
          value: extra.value,
          reason: extra.reason || '',
        });
      }

      if (type === 'approve') {
        await api.post('/mis/toggle-approve', {
          mis_record_id: row.id,
          value: extra.value,
        });
      }

      if (type === 'reject') {
        await api.post('/mis/toggle-reject', {
          mis_record_id: row.id,
          value: extra.value,
          reason: extra.reason || '',
        });
      }

      if (type === 'scanned') {
        await api.post('/mis/toggle-scanned', {
          mis_record_id: row.id,
          value: extra.value,
          scanning_date: extra.scanning_date,
        });
      }

      await refreshDetail();
      await load();
    } catch (e) {
      setError(e.message || 'Unable to update status.');
    }
  }

  async function deleteSelected() {
    if (!selectedIds.size) {
      setError('No records selected.');
      return;
    }

    try {
      await api.delete('/mis/bulk-delete', {
        ids: Array.from(selectedIds),
      });

      setSelectedIds(new Set());
      await refreshDetail();
      await load();
    } catch (e) {
      setError(e.message || 'Unable to delete selected records.');
    }
  }

  async function download() {
    setDownloading(true);
    setError('');

    try {
      const blob = await downloadDailyReport({
        start_date: filters.report_from,
        end_date: filters.report_to,
        dealership_id: filters.dealership_id || undefined,
        outlet_id: filters.outlet_id || undefined,
      });

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');

      a.href = url;
      a.download = `daily-report-${filters.report_from}-to-${filters.report_to}.xlsx`;

      document.body.appendChild(a);
      a.click();
      a.remove();

      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message || 'Unable to download daily report.');
    } finally {
      setDownloading(false);
    }
  }

  useEffect(() => {
    const initial = getRangeDates('today', today, today);

    load({
      ...filters,
      report_from: initial.from,
      report_to: initial.to,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <PageHeader
        title="Daily Reporting"
        description="Track booking & delivery file status by date."
        actions={
          <Button onClick={download} disabled={downloading}>
            <Download size={16} />
            {downloading ? 'Downloading...' : 'Download Report'}
          </Button>
        }
      />

      <div className="dashboard-hero card mb-6 grid gap-4 p-5 lg:grid-cols-5">
        <Field label="Date Range">
          <Select
            value={filters.range}
            onChange={(e) => {
              const dates = applyRange(e.target.value);

              load({
                ...filters,
                range: e.target.value,
                report_from: dates.from,
                report_to: dates.to,
              });
            }}
          >
            {rangeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="From">
          <Input
            type="date"
            value={filters.report_from}
            disabled={filters.range !== 'custom'}
            onChange={(e) => {
              const dates = applyRange('custom', e.target.value, filters.report_to);

              load({
                ...filters,
                range: 'custom',
                report_from: dates.from,
                report_to: dates.to,
              });
            }}
          />
        </Field>

        <Field label="To">
          <Input
            type="date"
            value={filters.report_to}
            disabled={filters.range !== 'custom'}
            onChange={(e) => {
              const dates = applyRange('custom', filters.report_from, e.target.value);

              load({
                ...filters,
                range: 'custom',
                report_from: dates.from,
                report_to: dates.to,
              });
            }}
          />
        </Field>

        <Field label="Dealership">
          <Select
            value={filters.dealership_id || ''}
            onChange={(e) => {
              const next = {
                ...filters,
                dealership_id: e.target.value,
                outlet_id: '',
              };

              setFilters(next);
              load(next);
            }}
          >
            <option value="">All Dealerships</option>
            {dealerships.map((x) => (
              <option key={x.id} value={x.id}>
                {x.name}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Outlet">
          <Select
            value={filters.outlet_id || ''}
            onChange={(e) => {
              const next = {
                ...filters,
                outlet_id: e.target.value,
              };

              setFilters(next);
              load(next);
            }}
          >
            <option value="">All Showrooms</option>
            {filteredOutlets.map((x) => (
              <option key={x.id} value={x.id}>
                {x.name}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <Alert type="error">{error || masters.error}</Alert>

      {loading ? (
        <Loader />
      ) : (
        <div className="space-y-6">
          <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-indigo-500" />
                <h2 className="text-sm font-bold text-slate-800 dark:text-white">
                  Booking Report
                </h2>
              </div>

              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                Click on any cell to see details
              </p>
            </div>

            <ReportTable stage="booking" rows={bookingRows} onCellClick={openDetail} />
          </section>

          <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                <h2 className="text-sm font-bold text-slate-800 dark:text-white">
                  Delivery Report
                </h2>
              </div>

              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                Click on any cell to see details
              </p>
            </div>

            <ReportTable stage="delivery" rows={deliveryRows} onCellClick={openDetail} />
          </section>
        </div>
      )}

      <DetailDialog
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={detailContext?.title || 'Details'}
        stage={detailContext?.stage || 'booking'}
        column={detailContext?.column}
        rows={detailLoading ? [] : detailRows}
        selectedIds={selectedIds}
        setSelectedIds={setSelectedIds}
        search={detailSearch}
        setSearch={setDetailSearch}
        onRefresh={refreshDetail}
        onDeleteSelected={deleteSelected}
        onAction={handleDetailAction}
      />

      {detailOpen && detailLoading && (
        <div className="fixed inset-x-0 top-4 z-[60] mx-auto w-fit rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white shadow-xl">
          Loading details...
        </div>
      )}
    </>
  );
}