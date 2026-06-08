import { jsPDF } from 'jspdf';

const PAGE = {
  w: 1120,
  h: 1580,
  m: 46,
};

const C = {
  bg: '#020617',
  bg2: '#0f172a',
  panel: '#070b1a',
  panel2: '#0b1220',
  border: '#25324a',
  text: '#f8fafc',
  muted: '#94a3b8',
  muted2: '#cbd5e1',
  amber: '#f59e0b',
  amber2: '#fbbf24',
  blue: '#818cf8',
  green: '#34d399',
  cyan: '#22d3ee',
  red: '#f87171',
  purple: '#a855f7',
};

const MODEL_COLORS = [
  '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#06b6d4', '#f97316', '#84cc16', '#818cf8', '#14b8a6',
];

const safeArray = (value) => (Array.isArray(value) ? value : []);
const safeNumber = (value) => Number(value || 0) || 0;
const textValue = (value, fallback = '-') => {
  if (value === null || value === undefined || value === '') return fallback;
  return String(value);
};

const formatNumber = (value) =>
  new Intl.NumberFormat('en-IN').format(safeNumber(value));

const formatCurrency = (value) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(safeNumber(value));

const periodLabel = (periodType) => {
  const map = {
    weekly: 'Weekly Report',
    monthly: 'Monthly Report',
    quarterly: 'Quarterly Report',
    annual: 'Annual Report',
  };
  return map[periodType] || 'MIS Report';
};

const truncate = (doc, value, maxWidth) => {
  const str = textValue(value, '');
  if (doc.getTextWidth(str) <= maxWidth) return str;

  let output = str;
  while (output.length > 3 && doc.getTextWidth(`${output}...`) > maxWidth) {
    output = output.slice(0, -1);
  }
  return `${output}...`;
};

const setFill = (doc, color) => doc.setFillColor(color);
const setDraw = (doc, color) => doc.setDrawColor(color);
const setText = (doc, color) => doc.setTextColor(color);

const addPageBackground = (doc) => {
  setFill(doc, C.bg);
  doc.rect(0, 0, PAGE.w, PAGE.h, 'F');

  setFill(doc, '#07111f');
  doc.roundedRect(24, 24, PAGE.w - 48, PAGE.h - 48, 34, 34, 'F');

  setDraw(doc, C.border);
  doc.setLineWidth(1.4);
  doc.roundedRect(24, 24, PAGE.w - 48, PAGE.h - 48, 34, 34, 'S');
};

const addFooter = (doc, pageTitle) => {
  setText(doc, C.muted);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.text('ASiJA & ASSOCIATES  •  AUTOMOBILE SALES AUDIT MIS', PAGE.m, PAGE.h - 32);
  doc.text(pageTitle || '', PAGE.w - PAGE.m, PAGE.h - 32, { align: 'right' });
};

const addHeader = (doc, eyebrow, title, subtitle) => {
  setText(doc, C.muted);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.text(String(eyebrow || '').toUpperCase(), PAGE.m, 70, {
    charSpace: 4,
  });

  setText(doc, C.text);
  doc.setFontSize(29);
  doc.text(title || 'MIS Report', PAGE.m, 108);

  if (subtitle) {
    setText(doc, C.muted);
    doc.setFontSize(14);
    doc.text(subtitle, PAGE.m, 137);
  }
};

const addPanel = (doc, x, y, w, h, fill = C.panel) => {
  setFill(doc, fill);
  setDraw(doc, C.border);
  doc.setLineWidth(1.2);
  doc.roundedRect(x, y, w, h, 22, 22, 'FD');
};

const addKpiCard = (doc, x, y, w, h, title, value, sub, color = C.blue) => {
  addPanel(doc, x, y, w, h, C.panel);

  setText(doc, C.muted);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.text(String(title || '').toUpperCase(), x + 20, y + 31, { charSpace: 2 });

  setText(doc, color);
  doc.setFontSize(30);
  doc.text(textValue(value, '0'), x + 20, y + 75);

  if (sub) {
    setText(doc, C.muted);
    doc.setFontSize(10.5);
    const lines = doc.splitTextToSize(String(sub), w - 40);
    doc.text(lines.slice(0, 2), x + 20, y + 104);
  }
};

const addBar = (doc, x, y, w, label, value, max, color, displayValue) => {
  const val = safeNumber(value);
  const maxVal = Math.max(1, safeNumber(max));
  const barW = Math.max(3, Math.min(w, (val / maxVal) * w));

  setText(doc, C.muted2);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.text(truncate(doc, label, w * 0.66), x, y);

  setText(doc, C.text);
  doc.text(displayValue ?? formatNumber(val), x + w, y, { align: 'right' });

  setFill(doc, '#111827');
  doc.roundedRect(x, y + 13, w, 11, 5, 5, 'F');
  setFill(doc, color || C.blue);
  doc.roundedRect(x, y + 13, barW, 11, 5, 5, 'F');

  return y + 42;
};

const addMiniDonut = (doc, cx, cy, radius, rows, key, totalOverride) => {
  const data = safeArray(rows).filter((item) => safeNumber(item?.[key]) > 0).slice(0, 10);
  const total = safeNumber(totalOverride) || data.reduce((sum, item) => sum + safeNumber(item?.[key]), 0);

  setDraw(doc, '#111827');
  doc.setLineWidth(32);
  doc.circle(cx, cy, radius, 'S');

  if (!data.length || !total) return;

  let start = -90;
  data.forEach((item, index) => {
    const angle = (safeNumber(item?.[key]) / total) * 360;
    const end = start + angle;
    setDraw(doc, MODEL_COLORS[index % MODEL_COLORS.length]);
    doc.setLineWidth(32);
    drawArc(doc, cx, cy, radius, start, end);
    start = end;
  });

  setText(doc, C.muted);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.text('TOTAL', cx, cy - 6, { align: 'center' });
  setText(doc, C.text);
  doc.setFontSize(20);
  doc.text(formatNumber(total), cx, cy + 22, { align: 'center' });
};

const drawArc = (doc, cx, cy, r, startDeg, endDeg) => {
  const points = [];
  const step = Math.max(3, Math.abs(endDeg - startDeg) / 14);
  for (let a = startDeg; a <= endDeg; a += step) {
    const rad = (a * Math.PI) / 180;
    points.push([cx + Math.cos(rad) * r, cy + Math.sin(rad) * r]);
  }
  const endRad = (endDeg * Math.PI) / 180;
  points.push([cx + Math.cos(endRad) * r, cy + Math.sin(endRad) * r]);

  for (let i = 1; i < points.length; i += 1) {
    doc.line(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1]);
  }
};

const addLegend = (doc, x, y, rows, key, total, labelKey = 'name') => {
  safeArray(rows).slice(0, 9).forEach((item, index) => {
    const color = MODEL_COLORS[index % MODEL_COLORS.length];
    const val = safeNumber(item?.[key]);
    const pct = total ? ((val / total) * 100).toFixed(1) : '0.0';

    setFill(doc, color);
    doc.circle(x, y + index * 25, 5, 'F');

    setText(doc, C.muted2);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.text(truncate(doc, item?.[labelKey] || item?.label || item?.model || 'Unknown', 190), x + 16, y + 4 + index * 25);

    setText(doc, C.text);
    doc.text(`${formatNumber(val)} (${pct}%)`, x + 260, y + 4 + index * 25, { align: 'right' });
  });
};

const normalizeModelRows = (data) => safeArray(data?.models || data?.cars).map((item) => ({
  ...item,
  name: item?.name || item?.carName || item?.model || item?.label || 'Unknown Model',
  bookings: safeNumber(item?.bookings || item?.booking || item?.totalBookings),
  deliveries: safeNumber(item?.deliveries || item?.delivery || item?.totalDeliveries),
  excessDiscount: safeNumber(item?.excessDiscount || item?.excess || item?.totalExcess),
}));

const normalizeShowroomRows = (data) => safeArray(data?.showrooms).map((item) => ({
  ...item,
  name: item?.name || item?.showroomName || item?.showroom || item?.label || 'Unknown Showroom',
  bookings: safeNumber(item?.bookings || item?.booking || item?.totalBookings),
  deliveries: safeNumber(item?.deliveries || item?.delivery || item?.totalDeliveries),
  excessDiscount: safeNumber(item?.excessDiscount || item?.excess || item?.totalExcess),
}));

const normalizeCars = (data) => {
  const explicitCars = safeArray(data?.cars);
  if (explicitCars.length) {
    return explicitCars.map((item) => ({
      ...item,
      name: item?.name || item?.carName || item?.model || item?.label || 'Unknown Model',
      bookings: safeNumber(item?.bookings),
      deliveries: safeNumber(item?.deliveries),
      allowedDiscount: safeNumber(item?.allowedDiscount || item?.totalAllowedDiscount),
      actualDiscount: safeNumber(item?.actualDiscount || item?.totalActualDiscount),
      excessDiscount: safeNumber(item?.excessDiscount || item?.totalExcess),
      variants: safeArray(item?.variants),
      outlets: safeArray(item?.outlets),
    }));
  }

  return normalizeModelRows(data).map((item) => ({
    ...item,
    allowedDiscount: safeNumber(item?.allowedDiscount),
    actualDiscount: safeNumber(item?.actualDiscount),
    variants: [],
    outlets: [],
  }));
};

const addCoverPage = (doc, reportTitle, periodType, data) => {
  addPageBackground(doc);

  setText(doc, C.amber2);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14);
  doc.text('AUTOMOBILE MIS', PAGE.m + 20, 160, { charSpace: 6 });

  setText(doc, C.text);
  doc.setFontSize(54);
  const titleLines = doc.splitTextToSize(reportTitle || 'Automobile Sales Audit MIS Report', 780);
  doc.text(titleLines, PAGE.m + 20, 240);

  setText(doc, C.muted2);
  doc.setFontSize(26);
  doc.text(periodLabel(periodType), PAGE.m + 20, 360);

  addPanel(doc, PAGE.m + 20, 460, 460, 150, C.panel);
  addPanel(doc, PAGE.m + 510, 460, 460, 150, C.panel);

  setText(doc, C.muted);
  doc.setFontSize(11);
  doc.text('SCOPE', PAGE.m + 50, 505, { charSpace: 3 });
  setText(doc, C.text);
  doc.setFontSize(21);
  doc.text(truncate(doc, data?.scope || 'All Accessible Data', 380), PAGE.m + 50, 548);

  setText(doc, C.muted);
  doc.setFontSize(11);
  doc.text('GENERATED ON', PAGE.m + 540, 505, { charSpace: 3 });
  setText(doc, C.text);
  doc.setFontSize(18);
  doc.text(new Date().toLocaleString('en-IN'), PAGE.m + 540, 548);

  addPanel(doc, PAGE.m + 20, 760, 950, 350, C.panel2);
  setText(doc, C.muted);
  doc.setFontSize(12);
  doc.text('REPORT CONTAINS', PAGE.m + 60, 820, { charSpace: 4 });
  setText(doc, C.text);
  doc.setFontSize(24);
  const points = [
    'Executive Dashboard Snapshot',
    'Model-wise Performance Analysis',
    'Two Cars Per Page Visual Summary',
    'Showroom-wise Performance Analysis',
    'RTO, Trends and Exception Reporting',
  ];
  points.forEach((point, index) => {
    setFill(doc, C.amber);
    doc.circle(PAGE.m + 75, 880 + index * 48, 5, 'F');
    setText(doc, C.text);
    doc.text(point, PAGE.m + 100, 888 + index * 48);
  });

  addFooter(doc, 'Cover');
};

const addExecutivePage = (doc, data) => {
  doc.addPage();
  addPageBackground(doc);
  addHeader(doc, 'Executive Summary', 'Dashboard Snapshot', 'Key MIS indicators for the selected report scope.');

  const summary = data?.summary || {};
  const x = PAGE.m;
  const y = 190;
  const w = 320;
  const h = 140;
  const gap = 28;

  addKpiCard(doc, x, y, w, h, 'Total Bookings', formatNumber(summary.totalBookings), `${formatNumber(summary.okBookings)} OK · ${formatNumber(summary.excessBookings)} Excess`, C.blue);
  addKpiCard(doc, x + w + gap, y, w, h, 'Total Deliveries', formatNumber(summary.totalDeliveries), 'Delivered units', C.green);
  addKpiCard(doc, x + (w + gap) * 2, y, w, h, 'Actual Discount', formatCurrency(summary.actualDiscount), 'Total discount passed', C.cyan);

  addKpiCard(doc, x, y + h + gap, w, h, 'Allowed Discount', formatCurrency(summary.allowedDiscount), 'As per price policy', C.amber2);
  addKpiCard(doc, x + w + gap, y + h + gap, w, h, 'Excess Discount', formatCurrency(summary.excessDiscount), 'Requires review', C.red);
  addKpiCard(doc, x + (w + gap) * 2, y + h + gap, w, h, 'Compliance', `${safeNumber(summary.compliancePercent).toFixed(1)}%`, 'OK transaction ratio', C.green);

  const models = normalizeModelRows(data);
  const showrooms = normalizeShowroomRows(data);

  addPanel(doc, PAGE.m, 570, 500, 700, C.panel);
  setText(doc, C.text);
  doc.setFontSize(18);
  doc.text('Booking Model Share', PAGE.m + 24, 620);
  const totalBookings = models.reduce((sum, item) => sum + item.bookings, 0);
  addMiniDonut(doc, PAGE.m + 250, 800, 92, models, 'bookings', totalBookings);
  addLegend(doc, PAGE.m + 70, 980, models, 'bookings', totalBookings, 'name');

  addPanel(doc, PAGE.m + 530, 570, 500, 700, C.panel);
  setText(doc, C.text);
  doc.text('Showroom Excess Exposure', PAGE.m + 554, 620);
  const maxExcess = Math.max(1, ...showrooms.map((item) => item.excessDiscount));
  let barY = 675;
  showrooms.slice(0, 10).forEach((item) => {
    barY = addBar(doc, PAGE.m + 560, barY, 430, item.name, item.excessDiscount, maxExcess, C.red, formatCurrency(item.excessDiscount));
  });

  addFooter(doc, 'Executive Summary');
};

const addCarsPages = (doc, data) => {
  const cars = normalizeCars(data);
  const chunks = [];
  for (let i = 0; i < cars.length; i += 2) chunks.push(cars.slice(i, i + 2));

  if (!chunks.length) {
    doc.addPage();
    addPageBackground(doc);
    addHeader(doc, 'Car Analysis', 'Model-wise Performance', 'No model-wise records were supplied.');
    addFooter(doc, 'Car Analysis');
    return;
  }

  chunks.forEach((group, pageIndex) => {
    doc.addPage();
    addPageBackground(doc);
    addHeader(doc, 'Car Analysis', `Model-wise Performance ${pageIndex + 1}`, 'Two cars per page with booking, delivery and discount analysis.');

    group.forEach((car, index) => {
      const x = PAGE.m + index * 530;
      const y = 185;
      addCarCard(doc, x, y, 500, 1190, car);
    });

    addFooter(doc, `Car Analysis ${pageIndex + 1}`);
  });
};

const addCarCard = (doc, x, y, w, h, car) => {
  addPanel(doc, x, y, w, h, C.panel);

  addPanel(doc, x + 22, y + 22, 110, 80, '#020617');
  setText(doc, C.text);
  doc.setFontSize(34);
  doc.text('🚘', x + 77, y + 74, { align: 'center' });

  setText(doc, C.muted);
  doc.setFontSize(9);
  doc.text('SELECTED CAR', x + 150, y + 48, { charSpace: 3 });
  setText(doc, C.text);
  doc.setFontSize(24);
  doc.text(truncate(doc, car.name, w - 180), x + 150, y + 82);

  const miniY = y + 135;
  const miniW = (w - 64) / 3;
  addKpiCard(doc, x + 22, miniY, miniW, 100, 'Bookings', formatNumber(car.bookings), '', C.blue);
  addKpiCard(doc, x + 32 + miniW, miniY, miniW, 100, 'Deliveries', formatNumber(car.deliveries), '', C.green);
  addKpiCard(doc, x + 42 + miniW * 2, miniY, miniW, 100, 'Excess', formatCurrency(car.excessDiscount), '', C.red);

  addPanel(doc, x + 22, y + 260, w - 44, 345, C.panel2);
  setText(doc, C.text);
  doc.setFontSize(15);
  doc.text('Car Performance Graph', x + 44, y + 300);
  const maxMain = Math.max(1, car.bookings, car.deliveries, car.allowedDiscount, car.actualDiscount, car.excessDiscount);
  let yy = y + 335;
  yy = addBar(doc, x + 44, yy, w - 88, 'Bookings', car.bookings, maxMain, C.blue);
  yy = addBar(doc, x + 44, yy, w - 88, 'Deliveries', car.deliveries, maxMain, C.green);
  yy = addBar(doc, x + 44, yy, w - 88, 'Allowed Discount', car.allowedDiscount, maxMain, C.amber, formatCurrency(car.allowedDiscount));
  yy = addBar(doc, x + 44, yy, w - 88, 'Actual Discount', car.actualDiscount, maxMain, C.cyan, formatCurrency(car.actualDiscount));
  addBar(doc, x + 44, yy, w - 88, 'Excess Discount', car.excessDiscount, maxMain, C.red, formatCurrency(car.excessDiscount));

  addPanel(doc, x + 22, y + 635, w - 44, 250, C.panel2);
  setText(doc, C.text);
  doc.setFontSize(15);
  doc.text('Variant Mix', x + 44, y + 675);
  const variants = safeArray(car.variants).map((item) => ({ name: item?.name || item?.label || 'Variant', count: safeNumber(item?.count || item?.bookings || item?.value) }));
  const maxVariant = Math.max(1, ...variants.map((item) => item.count));
  yy = y + 710;
  variants.slice(0, 5).forEach((item) => {
    yy = addBar(doc, x + 44, yy, w - 88, item.name, item.count, maxVariant, C.purple);
  });
  if (!variants.length) {
    setText(doc, C.muted);
    doc.text('No variant data available', x + w / 2, y + 760, { align: 'center' });
  }

  addPanel(doc, x + 22, y + 915, w - 44, 235, C.panel2);
  setText(doc, C.text);
  doc.setFontSize(15);
  doc.text('Outlet Mix', x + 44, y + 955);
  const outlets = safeArray(car.outlets).map((item) => ({ name: item?.name || item?.label || 'Outlet', count: safeNumber(item?.count || item?.bookings || item?.value) }));
  const maxOutlet = Math.max(1, ...outlets.map((item) => item.count));
  yy = y + 990;
  outlets.slice(0, 4).forEach((item) => {
    yy = addBar(doc, x + 44, yy, w - 88, item.name, item.count, maxOutlet, C.green);
  });
  if (!outlets.length) {
    setText(doc, C.muted);
    doc.text('No outlet data available', x + w / 2, y + 1035, { align: 'center' });
  }
};

const addShowroomPage = (doc, data) => {
  doc.addPage();
  addPageBackground(doc);
  addHeader(doc, 'Showroom Comparison', 'Showroom-wise Performance Dashboard', 'Bookings, deliveries and excess discount by showroom.');

  const rows = normalizeShowroomRows(data);
  const panelW = 322;
  const y = 190;
  const maxBooking = Math.max(1, ...rows.map((item) => item.bookings));
  const maxDelivery = Math.max(1, ...rows.map((item) => item.deliveries));
  const maxExcess = Math.max(1, ...rows.map((item) => item.excessDiscount));

  const panels = [
    { title: 'Booking Share', key: 'bookings', max: maxBooking, color: C.blue, amount: false },
    { title: 'Delivery Share', key: 'deliveries', max: maxDelivery, color: C.green, amount: false },
    { title: 'Excess Discount', key: 'excessDiscount', max: maxExcess, color: C.red, amount: true },
  ];

  panels.forEach((panel, idx) => {
    const x = PAGE.m + idx * (panelW + 28);
    addPanel(doc, x, y, panelW, 980, C.panel);
    setText(doc, C.text);
    doc.setFontSize(17);
    doc.text(panel.title, x + 22, y + 44);
    let yy = y + 88;
    rows.slice(0, 16).forEach((item) => {
      yy = addBar(doc, x + 22, yy, panelW - 44, item.name, item[panel.key], panel.max, panel.color, panel.amount ? formatCurrency(item[panel.key]) : formatNumber(item[panel.key]));
    });
  });

  addFooter(doc, 'Showroom Analysis');
};

const addRtoPage = (doc, data) => {
  doc.addPage();
  addPageBackground(doc);
  addHeader(doc, 'RTO Analysis', 'RTO-wise Analysis', 'Lucknow, outside-city and missing RTO visibility.');

  const rows = safeArray(data?.rto).map((item) => ({
    name: item?.name || item?.label || item?.particulars || 'RTO',
    rto: item?.rto || item?.rtoDisplay || item?.rtoCode || '',
    bookings: safeNumber(item?.bookings || item?.count || item?.value),
    share: item?.share,
  }));
  const max = Math.max(1, ...rows.map((item) => item.bookings));

  addPanel(doc, PAGE.m, 190, PAGE.w - PAGE.m * 2, 760, C.panel);
  let y = 255;
  rows.slice(0, 18).forEach((item, index) => {
    y = addBar(doc, PAGE.m + 40, y, PAGE.w - PAGE.m * 2 - 80, `${item.name} ${item.rto ? `· ${item.rto}` : ''}`, item.bookings, max, MODEL_COLORS[index % MODEL_COLORS.length]);
  });
  if (!rows.length) {
    setText(doc, C.muted);
    doc.setFontSize(16);
    doc.text('No RTO data available', PAGE.w / 2, 520, { align: 'center' });
  }

  addFooter(doc, 'RTO Analysis');
};

const addTrendPage = (doc, data) => {
  doc.addPage();
  addPageBackground(doc);
  addHeader(doc, 'Trend Analysis', 'Trend Dashboard', 'Old period to new period movement and month-wise exposure.');

  const trendSummary = data?.trendSummary || {};
  addKpiCard(doc, PAGE.m, 190, 240, 135, 'Old Bookings', formatNumber(trendSummary.oldBookings), 'Previous period', C.blue);
  addKpiCard(doc, PAGE.m + 265, 190, 240, 135, 'New Bookings', formatNumber(trendSummary.newBookings), 'Current period', C.green);
  addKpiCard(doc, PAGE.m + 530, 190, 240, 135, 'Old Excess', formatCurrency(trendSummary.oldExcess), 'Previous period', C.red);
  addKpiCard(doc, PAGE.m + 795, 190, 240, 135, 'New Excess', formatCurrency(trendSummary.newExcess), 'Current period', C.amber2);

  const trends = safeArray(data?.trends).map((item) => ({
    month: item?.month || item?.label || item?.period || 'Period',
    excessDiscount: safeNumber(item?.excessDiscount || item?.excess || item?.value),
  }));
  const max = Math.max(1, ...trends.map((item) => item.excessDiscount));

  addPanel(doc, PAGE.m, 390, PAGE.w - PAGE.m * 2, 820, C.panel);
  setText(doc, C.text);
  doc.setFontSize(18);
  doc.text('Month-wise Excess Discount Histogram', PAGE.m + 30, 440);
  let y = 500;
  trends.slice(0, 16).forEach((item) => {
    y = addBar(doc, PAGE.m + 40, y, PAGE.w - PAGE.m * 2 - 80, item.month, item.excessDiscount, max, C.red, formatCurrency(item.excessDiscount));
  });
  if (!trends.length) {
    setText(doc, C.muted);
    doc.setFontSize(16);
    doc.text('No trend data available', PAGE.w / 2, 740, { align: 'center' });
  }

  addFooter(doc, 'Trend Analysis');
};

const addExceptionsPage = (doc, data) => {
  doc.addPage();
  addPageBackground(doc);
  addHeader(doc, 'Exceptions', 'High Risk / Excess Discount Cases', 'Top transactions requiring management review.');

  const rows = safeArray(data?.exceptions);
  addPanel(doc, PAGE.m, 190, PAGE.w - PAGE.m * 2, 1050, C.panel);

  const headers = ['S No.', 'Customer', 'Showroom', 'Model', 'Executive', 'Excess'];
  const widths = [55, 190, 220, 160, 170, 150];
  let x = PAGE.m + 25;
  let y = 245;

  setText(doc, C.muted);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  headers.forEach((header, index) => {
    doc.text(header.toUpperCase(), x, y, { charSpace: 1.5 });
    x += widths[index];
  });

  setDraw(doc, C.border);
  doc.line(PAGE.m + 20, y + 18, PAGE.w - PAGE.m - 20, y + 18);
  y += 52;

  rows.slice(0, 18).forEach((item, index) => {
    x = PAGE.m + 25;
    const values = [
      index + 1,
      item?.customer || '-',
      item?.showroom || '-',
      item?.model || '-',
      item?.executive || '-',
      formatCurrency(item?.excessDiscount),
    ];

    values.forEach((value, colIndex) => {
      setText(doc, colIndex === 5 ? C.red : C.muted2);
      doc.setFontSize(10.5);
      doc.text(truncate(doc, value, widths[colIndex] - 12), x, y);
      x += widths[colIndex];
    });

    setDraw(doc, '#182236');
    doc.line(PAGE.m + 20, y + 18, PAGE.w - PAGE.m - 20, y + 18);
    y += 48;
  });

  if (!rows.length) {
    setText(doc, C.muted);
    doc.setFontSize(16);
    doc.text('No exception data available', PAGE.w / 2, 650, { align: 'center' });
  }

  addFooter(doc, 'Exceptions');
};

export async function generateVisualMisReportPdf({
  reportData = {},
  periodType = 'monthly',
  reportTitle = 'Automobile Sales Audit MIS Report',
}) {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'px',
    format: [PAGE.w, PAGE.h],
    compress: true,
  });

  try {
    addCoverPage(doc, reportTitle, periodType, reportData);
    addExecutivePage(doc, reportData);
    addCarsPages(doc, reportData);
    addShowroomPage(doc, reportData);
    addRtoPage(doc, reportData);
    addTrendPage(doc, reportData);
    addExceptionsPage(doc, reportData);

    const fileName = `MIS_${periodType}_visual_report_${new Date()
      .toISOString()
      .slice(0, 10)}.pdf`;

    doc.save(fileName);
  } catch (error) {
    console.error('Vector PDF generation error:', error);
    throw error;
  }
}