import {
  Download,
  Edit,
  Plus,
  RefreshCw,
  Trash2,
  X,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import * as XLSX from 'xlsx';
import Alert from '../components/Alert';
import Button from '../components/Button';
import DataTable from '../components/DataTable';
import Field, { Select } from '../components/Field';
import FiltersBar from '../components/FiltersBar';
import Loader from '../components/Loader';
import PageHeader from '../components/PageHeader';
import { BOOKING_COLUMNS, DELIVERY_COLUMNS } from '../config/columns';
import { useMasters } from '../context/MasterDataContext';
import { deleteTransaction, getTransactionsPage } from '../services/transactionService';
import { api } from '../services/apiClient';

const cleanNumber = (value) => {
  if (value === null || value === undefined || value === '') return 0;
  const num = String(value).replace(/[₹,\s]/g, '');
  return Number(num || 0);
};

const firstAmount = (row, keys) => {
  for (const key of keys) {
    if (row?.[key] !== undefined && row?.[key] !== null && row?.[key] !== '') {
      return cleanNumber(row[key]);
    }
  }
  return 0;
};

const firstText = (row, keys) => {
  for (const key of keys) {
    if (row?.[key] !== undefined && row?.[key] !== null && row?.[key] !== '') {
      return row[key];
    }
  }
  return '';
};

const getVariantId = (row) => {
  return (
    row?.variant_id ||
    row?.variantId ||
    row?.vehicle_variant_id ||
    row?.car_variant_id ||
    null
  );
};

const getBookingDate = (row) => {
  return row?.booking_date || row?.bookingDate || row?.date || null;
};

const getModelYear = (row) => {
  return row?.model_year || row?.modelYear || row?.year || 2026;
};

const isPriceComponentName = (name) => {
  const lower = String(name || '').toLowerCase();

  return (
    lower.includes('ex showroom') ||
    lower.includes('ex-showroom') ||
    lower.includes('exshowroom') ||
    lower.includes('tcs') ||
    lower.includes('insurance') ||
    lower.includes('registration') ||
    lower.includes('fastag') ||
    lower.includes('fas tag') ||
    lower.includes('accessories') ||
    lower.includes('accessory') ||
    lower.includes('amc') ||
    lower.includes('warranty') ||
    lower.includes('shield')
  );
};

const isDiscountComponentName = (name) => {
  const lower = String(name || '').toLowerCase();

  const excludedFromDiscount =
    lower.includes('ex showroom') ||
    lower.includes('ex-showroom') ||
    lower.includes('exshowroom') ||
    lower.includes('tcs') ||
    lower.includes('insurance') ||
    lower.includes('registration') ||
    lower.includes('fastag') ||
    lower.includes('fas tag') ||
    lower.includes('accessories') ||
    lower.includes('accessory') ||
    lower.includes('amc') ||
    lower.includes('warranty') ||
    lower.includes('shield') ||
    lower.includes('price increase') ||
    lower.includes('maximum benefit') ||
    lower.includes('price difference');

  if (excludedFromDiscount) return false;

  return (
    lower.includes('cash discount') ||
    lower.includes('additional discount') ||
    lower.includes('dealer discount') ||
    lower.includes('exchange bonus') ||
    lower.includes('exchange discount') ||
    lower.includes('corporate discount') ||
    lower.includes('scrap discount') ||
    lower.includes('scrappage') ||
    lower.includes('loyalty') ||
    lower.includes('scheme discount') ||
    lower.includes('discount')
  );
};

const ALWAYS_ALLOWED_DISCOUNTS = [
  'cash discount',
  'additional discount',
  'dealer discount',
];

const CONDITIONAL_DISCOUNT_RULES = [
  {
    conditionKey: 'exchange',
    keywords: ['exchange bonus', 'exchange discount', 'exchange'],
  },
  {
    conditionKey: 'corporate',
    keywords: ['corporate discount', 'corporate'],
  },
  {
    conditionKey: 'scrap',
    keywords: ['scrap discount', 'scrappage', 'scrap'],
  },
  {
    conditionKey: 'upgrade',
    keywords: ['loyalty', 'upgrade'],
  },
  {
    conditionKey: 'govt_employee',
    keywords: ['govt', 'government'],
  },
  {
    conditionKey: 'tr_case',
    keywords: ['tr case', 'tr'],
  },
];

const getConditions = (row) => {
  if (row?.conditions && typeof row.conditions === 'object') {
    return row.conditions;
  }

  if (typeof row?.conditions === 'string') {
    try {
      return JSON.parse(row.conditions);
    } catch {
      return {};
    }
  }

  return {};
};

const isAllowedDiscountForRow = (name, row) => {
  const lower = String(name || '').toLowerCase();

  if (!isDiscountComponentName(name)) return false;

  const isAlwaysAllowed = ALWAYS_ALLOWED_DISCOUNTS.some((keyword) =>
    lower.includes(keyword)
  );

  if (isAlwaysAllowed) return true;

  const conditions = getConditions(row);

  return CONDITIONAL_DISCOUNT_RULES.some((rule) => {
    const conditionSelected = Boolean(conditions?.[rule.conditionKey]);

    if (!conditionSelected) return false;

    return rule.keywords.some((keyword) => lower.includes(keyword));
  });
};

const isActualAmountField = (key) => {
  const lower = String(key || '').toLowerCase();

  return (
    lower.endsWith('_actual') ||
    lower.endsWith(' actual') ||
    lower.includes('_actual_')
  );
};

const cleanComponentNameFromActualKey = (key) => {
  return String(key || '')
    .toLowerCase()
    .replace(/_actual$/g, '')
    .replace(/ actual$/g, '')
    .replace(/_actual_/g, '')
    .replace(/_/g, ' ');
};

const getLineItems = (row) => {
  const possibleArrays = [
    row?.items,
    row?.transaction_items,
    row?.transactionItems,
    row?.price_items,
    row?.discount_items,
    row?.components,
    row?.amount_items,
    row?.transaction_components,
    row?.transactionComponents,
    row?.line_items,
    row?.lineItems,
    row?.details,
  ];

  for (const arr of possibleArrays) {
    if (Array.isArray(arr) && arr.length) return arr;
  }

  return [];
};

const getItemName = (item) => {
  return (
    item?.name ||
    item?.component_name ||
    item?.particular ||
    item?.particulars ||
    item?.label ||
    item?.title ||
    ''
  );
};

const getItemType = (item) => {
  return String(
    item?.type ||
      item?.component_type ||
      item?.item_type ||
      ''
  ).toLowerCase();
};

const getItemActual = (item) => {
  return cleanNumber(
    item?.actual_amount ??
      item?.actual ??
      item?.charged_amount ??
      item?.charged ??
      item?.given_amount ??
      item?.given ??
      item?.amount ??
      0
  );
};

const getItemAllowed = (item) => {
  return cleanNumber(
    item?.allowed_amount ??
      item?.allowed ??
      item?.listed_amount ??
      item?.listed ??
      item?.price_list_amount ??
      item?.price_list ??
      0
  );
};

const fetchPriceListAllowedAmounts = async (row) => {
  const variantId = getVariantId(row);
  const bookingDate = getBookingDate(row);
  const modelYear = getModelYear(row);

  if (!variantId || !bookingDate || !modelYear) {
    return {};
  }

  try {
    const preview = await api.get('/price-list/preview', {
      variant_id: variantId,
      booking_date: bookingDate,
      model_year: Number(modelYear),
    });

    const allowed = {};

    Object.entries(preview || {}).forEach(([name, value]) => {
      allowed[name] = cleanNumber(value);
    });

    return allowed;
  } catch (err) {
    console.warn(`Price-list preview failed for transaction #${row?.id}`, err);
    return {};
  }
};

const getFlattenedActualPriceFields = (row) => {
  return Object.fromEntries(
    Object.entries(row || {}).filter(([key]) => {
      if (!isActualAmountField(key)) return false;

      const componentName = cleanComponentNameFromActualKey(key);
      return isPriceComponentName(componentName);
    })
  );
};

const sumActualPrices = (row) => {
  let total = 0;

  if (row?.actual_amounts && typeof row.actual_amounts === 'object') {
    total = Object.entries(row.actual_amounts).reduce((sum, [name, value]) => {
      return isPriceComponentName(name) ? sum + cleanNumber(value) : sum;
    }, 0);

    if (total > 0) return total;
  }

  const flattenedActualPriceFields = getFlattenedActualPriceFields(row);

  total = Object.values(flattenedActualPriceFields).reduce(
    (sum, value) => sum + cleanNumber(value),
    0
  );

  if (total > 0) return total;

  const lineItems = getLineItems(row);

  if (lineItems.length) {
    total = lineItems.reduce((sum, item) => {
      const name = getItemName(item);
      const type = getItemType(item);
      const actual = getItemActual(item);

      const isPrice =
        type === 'price' ||
        type === 'price_component' ||
        isPriceComponentName(name);

      return isPrice && actual > 0 ? sum + actual : sum;
    }, 0);
  }

  return total;
};

const sumActualDiscounts = (row) => {
  const lineItems = getLineItems(row);

  if (lineItems.length) {
    const total = lineItems.reduce((sum, item) => {
      const name = getItemName(item);
      const type = getItemType(item);

      const isDiscount =
        type === 'discount' ||
        type === 'discount_component' ||
        isDiscountComponentName(name);

      return isDiscount ? sum + getItemActual(item) : sum;
    }, 0);

    if (total > 0) return total;
  }

  if (row?.actual_amounts && typeof row.actual_amounts === 'object') {
    const total = Object.entries(row.actual_amounts).reduce((sum, [name, value]) => {
      return isDiscountComponentName(name) ? sum + cleanNumber(value) : sum;
    }, 0);

    if (total > 0) return total;
  }

  return Object.entries(row || {}).reduce((sum, [key, value]) => {
    if (!isActualAmountField(key)) return sum;

    const componentName = cleanComponentNameFromActualKey(key);

    return isDiscountComponentName(componentName)
      ? sum + cleanNumber(value)
      : sum;
  }, 0);
};

const sumAllowedDiscounts = (row) => {
  if (
    row?.price_list_allowed_amounts &&
    typeof row.price_list_allowed_amounts === 'object'
  ) {
    return Object.entries(row.price_list_allowed_amounts).reduce(
      (sum, [name, value]) => {
        return isAllowedDiscountForRow(name, row)
          ? sum + cleanNumber(value)
          : sum;
      },
      0
    );
  }

  const lineItems = getLineItems(row);

  if (lineItems.length) {
    return lineItems.reduce((sum, item) => {
      const name = getItemName(item);
      const type = getItemType(item);

      const isDiscount =
        type === 'discount' ||
        type === 'discount_component' ||
        isAllowedDiscountForRow(name, row);

      return isDiscount ? sum + getItemAllowed(item) : sum;
    }, 0);
  }

  if (row?.allowed_amounts && typeof row.allowed_amounts === 'object') {
    return Object.entries(row.allowed_amounts).reduce((sum, [name, value]) => {
      return isAllowedDiscountForRow(name, row)
        ? sum + cleanNumber(value)
        : sum;
    }, 0);
  }

  return Object.entries(row || {}).reduce((sum, [key, value]) => {
    const lower = String(key || '').toLowerCase();

    const isAllowedField =
      lower.endsWith('_allowed') ||
      lower.endsWith('_listed') ||
      lower.includes('_allowed_') ||
      lower.includes('_listed_');

    if (!isAllowedField) return sum;

    const componentName = lower
      .replace(/_allowed$/g, '')
      .replace(/_listed$/g, '')
      .replace(/_allowed_/g, '')
      .replace(/_listed_/g, '')
      .replace(/_/g, ' ');

    return isAllowedDiscountForRow(componentName, row)
      ? sum + cleanNumber(value)
      : sum;
  }, 0);
};

const calculateExcessDiscount = (row, totalDiscount) => {
  const allowedDiscount = sumAllowedDiscounts(row);

  return Math.max(
    0,
    cleanNumber(totalDiscount) - cleanNumber(allowedDiscount)
  );
};

const extractTransactionRows = (response) => {
  if (Array.isArray(response)) return response;

  const possibleArrays = [
    response?.items,
    response?.rows,
    response?.data,
    response?.results,
    response?.transactions,
    response?.records,
    response?.list,
  ];

  for (const value of possibleArrays) {
    if (Array.isArray(value)) return value;
  }

  return [];
};

const normalizeTransactionRow = (row, stage) => {
  const bookingAmount = firstAmount(row, [
    'booking_amount',
    'booking_amt',
    'bookingAmount',
    'booking_amt_booking',
  ]);

  const grossActualPrice = sumActualPrices(row);

  const directPriceOffered = firstAmount(row, [
    'price_offered',
    'priceOffered',
    'price_charged',
    'priceCharged',
    'total_price_charged',
    'totalPriceCharged',
    'total_charged_price',
    'totalChargedPrice',
    'on_road_price',
    'onRoadPrice',
    'onroad_price',
    'onroadPrice',
    'total_on_road_price',
    'totalOnRoadPrice',
    'total_onroad_price',
    'totalOnroadPrice',
  ]);

  const actualDiscountTotal = sumActualDiscounts(row);

  const fallbackDiscount = firstAmount(row, [
    'discount_booking',
    'other_discount_booking',
    'other_discount_delivery',
  ]);

  const totalDiscount = actualDiscountTotal || fallbackDiscount;

  const priceOffered =
    grossActualPrice > 0
      ? Math.max(0, grossActualPrice - totalDiscount)
      : directPriceOffered;

  const excess = calculateExcessDiscount(row, totalDiscount);

  const bookingDate = firstText(row, [
    'booking_date',
    'bookingDate',
  ]);

  const deliveryDate = firstText(row, [
    'delivery_date',
    'deliveryDate',
  ]);

  const executive = firstText(row, [
    'sales_executive_name',
    'executive_name',
    'employee_name',
    'sales_executive',
    'executive',
  ]);

  const variant = firstText(row, [
    'variant_name',
    'variant',
    'car_variant',
  ]);

  const customer = firstText(row, [
    'customer_name',
    'customer',
    'name',
  ]);

  const status = excess > 0 ? 'Excess Discount' : 'No Excess Discount';

  return {
    ...row,

    booking_amount: bookingAmount,
    bookingAmount,
    booking_amt: bookingAmount,

    gross_actual_price: grossActualPrice,
    grossActualPrice,

    price_offered: priceOffered,
    priceOffered,
    price_offered_booking: priceOffered,
    priceOfferedBooking: priceOffered,
    price_charged: priceOffered,
    priceCharged: priceOffered,
    total_price_charged: priceOffered,
    totalPriceCharged: priceOffered,
    total_charged_price: priceOffered,
    totalChargedPrice: priceOffered,
    price_difference: priceOffered,
    priceDifference: priceOffered,
    on_road_price: priceOffered,
    onRoadPrice: priceOffered,
    onroad_price: priceOffered,
    onroadPrice: priceOffered,
    total_on_road_price: priceOffered,
    totalOnRoadPrice: priceOffered,
    total_onroad_price: priceOffered,
    totalOnroadPrice: priceOffered,

    total_discount: totalDiscount,
    totalDiscount,
    total_discount_booking: totalDiscount,
    totalDiscountBooking: totalDiscount,

    excess,
    excess_booking: excess,
    excessBooking: excess,
    total_excess_discount: excess,
    totalExcessDiscount: excess,

    booking_date: bookingDate,
    bookingDate,
    delivery_date: deliveryDate,
    deliveryDate,

    sales_executive_name: executive,
    executive_name: executive,
    executive,

    variant_name: variant,
    variant,

    customer_name: customer,
    customer,

    status,

    ...(stage === 'booking'
      ? {
          date: bookingDate,
          amount: bookingAmount,
        }
      : {
          date: deliveryDate || bookingDate,
          amount: bookingAmount,
        }),
  };
};

const normalizeSearchText = (value) => {
  if (value === null || value === undefined) return '';

  if (typeof value === 'object') {
    try {
      return JSON.stringify(value).toLowerCase();
    } catch {
      return '';
    }
  }

  return String(value).toLowerCase();
};

const getColumnKey = (column) => {
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

const getColumnSearchValue = (row, column) => {
  const key = getColumnKey(column);
  if (!key) return '';
  return normalizeSearchText(row?.[key]);
};

const rowMatchesColumnFilters = (row, columns, columnFilters) => {
  return (columns || []).every((column) => {
    const key = getColumnKey(column);
    const query = normalizeSearchText(columnFilters?.[key]).trim();

    if (!query) return true;

    return getColumnSearchValue(row, column).includes(query);
  });
};

const getExportValue = (row, column) => {
  const key = getColumnKey(column);

  if (!key) return '';

  const value = row?.[key];

  if (value === null || value === undefined) return '';

  if (typeof value === 'object') {
    return JSON.stringify(value);
  }

  return value;
};

const exportRowsToExcel = ({ rows, columns, fileName, sheetName }) => {
  const visibleColumns = (columns || []).filter((column) => {
    const key = getColumnKey(column);
    const label = String(getColumnLabel(column) || '').trim().toLowerCase();

    return (
      key !== '__sno' &&
      label &&
      label !== 'actions' &&
      label !== 'action'
    );
  });

  const exportData = (rows || []).map((row, index) => {
    const output = {
      'S No.': index + 1,
    };

    visibleColumns.forEach((column) => {
      output[getColumnLabel(column)] = getExportValue(row, column);
    });

    return output;
  });

  const worksheet = XLSX.utils.json_to_sheet(
    exportData.length ? exportData : [{ 'S No.': '' }]
  );

  worksheet['!cols'] = Object.keys(exportData[0] || { 'S No.': '' }).map(
    (key) => ({
      wch: Math.max(14, String(key).length + 4),
    })
  );

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);

  XLSX.writeFile(workbook, fileName);
};

export default function MisPage({ stage }) {
  const masters = useMasters();
  const [rows, setRows] = useState([]);
  const [filters, setFilters] = useState({ stage, limit: 25, offset: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [columnFilters, setColumnFilters] = useState({});

  const baseColumns = stage === 'booking' ? BOOKING_COLUMNS : DELIVERY_COLUMNS;
  const title = stage === 'booking' ? 'Booking MIS' : 'Delivery MIS';

  const columns = useMemo(() => {
    return [
      {
        key: '__sno',
        label: 'S No.',
      },
      ...baseColumns,
    ];
  }, [baseColumns]);

  const searchableColumns = useMemo(() => {
    return (columns || []).filter((column) => {
      const key = getColumnKey(column);
      const label = String(getColumnLabel(column) || '').trim().toLowerCase();

      return (
        key !== '__sno' &&
        label &&
        label !== 'actions' &&
        label !== 'action'
      );
    });
  }, [columns]);

  const activeColumnFilters = useMemo(() => {
    return Object.entries(columnFilters).filter(([, value]) =>
      String(value || '').trim()
    );
  }, [columnFilters]);

  const filteredRows = useMemo(() => {
    return rows.filter((row) =>
      rowMatchesColumnFilters(row, searchableColumns, columnFilters)
    );
  }, [rows, searchableColumns, columnFilters]);

  const tableRows = useMemo(() => {
    return filteredRows.map((row, index) => ({
      ...row,
      __sno: (Number(filters.offset) || 0) + index + 1,
    }));
  }, [filteredRows, filters.offset]);

  const openNewEntry = () => {
    window.location.href = `/form?stage=${stage}${
      stage === 'delivery' ? '&mode=direct' : ''
    }`;
  };

  const openEditEntry = (row) => {
    window.location.href = `/form?stage=${stage}&transaction_id=${row.id}${
      stage === 'delivery' ? '&mode=direct' : ''
    }`;
  };

  const handleExportExcel = () => {
    if (!filteredRows.length) {
      setError('No rows available to export.');
      return;
    }

    const now = new Date();
    const stamp = now.toISOString().slice(0, 19).replace(/[:T]/g, '-');

    exportRowsToExcel({
      rows: filteredRows,
      columns,
      fileName: `${stage === 'booking' ? 'booking-mis' : 'delivery-mis'}-${stamp}.xlsx`,
      sheetName: stage === 'booking' ? 'Booking MIS' : 'Delivery MIS',
    });
  };

  async function load(next = filters) {
    setLoading(true);
    setError('');

    try {
      const data = await getTransactionsPage(next);
      const rowsFromApi = extractTransactionRows(data);

      const detailedRows = await Promise.all(
        rowsFromApi.map(async (row) => {
          try {
            const detail = await api.get(`/transactions/${row.id}`);
            const mergedWithoutPriceList = { ...row, ...detail };

            const priceListAllowedAmounts =
              await fetchPriceListAllowedAmounts(mergedWithoutPriceList);

            return {
              ...mergedWithoutPriceList,
              price_list_allowed_amounts: priceListAllowedAmounts,
              backend_allowed_amounts: mergedWithoutPriceList.allowed_amounts,
            };
          } catch (err) {
            console.warn(`Unable to fetch transaction detail for #${row.id}`, err);
            return row;
          }
        })
      );

      const normalizedRows = detailedRows.map((row) =>
        normalizeTransactionRow(row, stage)
      );

      setRows(normalizedRows);
    } catch (e) {
      console.error('MIS load failed:', e);
      setError(
        e?.message?.includes('map is not a function')
          ? 'Unable to load MIS data because the API response format is not matching the table format.'
          : e.message || 'Unable to load transactions.'
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const f = { ...filters, stage };
    setFilters(f);
    load(f);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage]);

  const page = useMemo(
    () =>
      Math.floor((Number(filters.offset) || 0) / (Number(filters.limit) || 25)) +
      1,
    [filters]
  );

  async function remove(row) {
    if (!confirm(`Delete transaction #${row.id}?`)) return;

    try {
      await deleteTransaction(row.id);
      await load();
    } catch (e) {
      setError(e.message || 'Unable to delete transaction.');
    }
  }

  function next(delta) {
    const limit = Number(filters.limit) || 25;
    const offset = Math.max(0, (Number(filters.offset) || 0) + delta * limit);
    const nextFilters = { ...filters, offset };

    setFilters(nextFilters);
    load(nextFilters);
  }

  return (
    <>
      <PageHeader
        title={title}
        description="Fast paginated table consuming /transactions-pages. Full details open on demand."
        actions={
          <Button onClick={openNewEntry}>
            <Plus size={16} /> New Entry
          </Button>
        }
      />

      <FiltersBar
        filters={filters}
        setFilters={setFilters}
        dealerships={masters.dealerships}
        outlets={masters.outlets}
        onApply={() => {
          const nextFilters = { ...filters, offset: 0 };
          setFilters(nextFilters);
          load(nextFilters);
        }}
        rightActions={
          <button
            type="button"
            onClick={handleExportExcel}
            disabled={!filteredRows.length}
            className="inline-flex h-12 min-w-[220px] items-center justify-center gap-2 rounded-xl border border-emerald-300 bg-emerald-400 px-8 text-sm font-black uppercase tracking-wide text-slate-950 shadow-sm transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Download size={16} />
            Export Excel
          </button>
        }
      >
        <Field label="Rows">
          <Select
            value={filters.limit}
            onChange={(e) =>
              setFilters((f) => ({
                ...f,
                limit: Number(e.target.value),
                offset: 0,
              }))
            }
          >
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </Select>
        </Field>
      </FiltersBar>

      {activeColumnFilters.length ? (
        <div className="mb-4 flex flex-wrap items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => setColumnFilters({})}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-slate-300 px-5 text-sm font-black uppercase tracking-wide text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
          >
            <X size={16} />
            Clear Search
          </button>
        </div>
      ) : null}

      {activeColumnFilters.length ? (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="text-xs font-black uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Active Filters:
          </span>

          {activeColumnFilters.map(([key, value]) => {
            const column = searchableColumns.find(
              (item) => getColumnKey(item) === key
            );

            return (
              <span
                key={key}
                className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-bold text-amber-800 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-200"
              >
                {getColumnLabel(column)}: {value}

                <button
                  type="button"
                  onClick={() =>
                    setColumnFilters((prev) => ({
                      ...prev,
                      [key]: '',
                    }))
                  }
                  className="text-amber-700 hover:text-amber-950 dark:text-amber-200"
                >
                  <X size={12} />
                </button>
              </span>
            );
          })}

          <button
            type="button"
            onClick={() => setColumnFilters({})}
            className="rounded-full border border-slate-300 px-3 py-1 text-xs font-black uppercase tracking-wide text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
          >
            Clear All
          </button>
        </div>
      ) : null}

      <Alert type="error">{error || masters.error}</Alert>

      {loading ? (
        <Loader />
      ) : (
        <DataTable
          columns={columns}
          rows={tableRows}
          showColumnFilters
          columnFilters={columnFilters}
          onColumnFilterChange={(key, value) =>
            setColumnFilters((prev) => ({
              ...prev,
              [key]: value,
            }))
          }
          actions={(row) => (
            <div className="flex justify-end gap-2">
              <button
                className="rounded-lg border p-2 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-900"
                onClick={() => openEditEntry(row)}
                title="Edit transaction"
              >
                <Edit size={15} />
              </button>

              <button
                className="rounded-lg border p-2 text-red-600 hover:bg-red-50 dark:border-slate-700 dark:hover:bg-red-950/20"
                onClick={() => remove(row)}
                title="Delete transaction"
              >
                <Trash2 size={15} />
              </button>
            </div>
          )}
        />
      )}

      <div className="mt-4 flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-500">
          Page {page}
        </p>

        <div className="flex gap-2">
          <Button
            variant="secondary"
            onClick={() => next(-1)}
            disabled={(filters.offset || 0) <= 0}
          >
            Previous
          </Button>

          <Button
            variant="secondary"
            onClick={() => next(1)}
            disabled={rows.length < Number(filters.limit || 25)}
          >
            Next
          </Button>

          <Button variant="secondary" onClick={() => load()}>
            <RefreshCw size={16} /> Refresh
          </Button>
        </div>
      </div>
    </>
  );
}