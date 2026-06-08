import { Edit, RefreshCw, Save } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import Alert from '../components/Alert';
import Button from '../components/Button';
import DataTable from '../components/DataTable';
import Field, { Input, Select } from '../components/Field';
import Loader from '../components/Loader';
import PageHeader from '../components/PageHeader';
import { api } from '../services/apiClient';

const today = new Date().toISOString().slice(0, 10);

const EMPTY_FORM = {
  id: null,
  complaint_code: '',

  complainant_dealership: '',
  complainant_showroom: '',
  complainee_dealership: 'X',
  complainee_showroom: 'X',

  customer_name: '',
  customer_mobile: '',
  email: '',
  customer_address: '',
  customer_city: '',
  customer_pin: '',
  customer_pan: '',
  customer_aadhar: '',

  car_id: '',
  variant_id: '',
  vin_number: '',
  engine_number: '',
  registration_number: '',
  registration_date: '',
  car_color: '',

  quotation_number: '',
  quotation_date: '',
  tcs_amount: '',
  total_offered_price: '',
  net_offered_price: '',

  booking_file_number: '',
  receipt_number: '',
  booking_amount: '',
  mode_of_payment: '',
  instrument_date: '',
  instrument_number: '',
  bank_name: '',

  complaint_raised_date: today,
  aa_name: '',
  remarks_by_complainant: '',
  remarks_by_aa: '',
  status: '',

  ex_showroom_price: '',
  insurance: '',
  registration_road_tax: '',
  discount: '',
  accessories_charged: '',
};

const modeOfPaymentOptions = [
  'Cash',
  'Credit Card',
  'Debit Card',
  'Net Banking',
  'UPI',
  'Other',
];

const isValidDate = (value) => {
  if (!value) return false;
  const d = new Date(value);
  return !Number.isNaN(d.getTime());
};

const cleanNumber = (value) => {
  if (value === null || value === undefined || value === '') return 0;

  const cleaned = String(value).replace(/[₹,\s]/g, '').trim();

  if (!cleaned) return 0;

  try {
    if (/^[\d+\-*/().\s]+$/.test(cleaned)) {
      // eslint-disable-next-line no-new-func
      return Math.trunc(Number(Function(`"use strict"; return (${cleaned})`)()));
    }

    return Math.trunc(Number(cleaned) || 0);
  } catch {
    return 0;
  }
};

const getQueryParam = (key) => {
  return new URLSearchParams(window.location.search).get(key);
};

const Section = ({ icon, title, children }) => {
  return (
    <section className="card mb-6 p-6">
      <div className="mb-5 flex items-center gap-2 border-b border-slate-100 pb-3 dark:border-slate-800">
        <span className="select-none text-xl">{icon}</span>
        <h2 className="text-base font-bold text-slate-900 dark:text-white">
          {title}
        </h2>
      </div>

      {children}
    </section>
  );
};

const TextAreaField = ({ label, value, onChange, required }) => {
  return (
    <Field label={label}>
      <textarea
        value={value || ''}
        onChange={onChange}
        rows={3}
        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-800 outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-100 dark:border-slate-700 dark:bg-slate-950 dark:text-white dark:focus:border-amber-400 dark:focus:ring-amber-400/10"
        required={required}
      />
    </Field>
  );
};

const normaliseComplaintForEdit = (complaint) => {
  if (!complaint) return EMPTY_FORM;

  return {
    ...EMPTY_FORM,

    id: complaint.id || complaint.transaction_id || null,
    complaint_code: complaint.complaint_code || '',

    complainant_dealership:
      complaint.complainant_dealer_name ||
      complaint.complainant_dealership ||
      complaint?.dealer_showroom_details?.complainant_dealership ||
      '',

    complainant_showroom:
      complaint.complainant_showroom_name ||
      complaint.complainant_showroom ||
      complaint?.dealer_showroom_details?.complainant_showroom ||
      '',

    complainee_dealership:
      complaint.complainee_dealer_name ||
      complaint.complainee_dealership ||
      complaint?.dealer_showroom_details?.complainee_dealership ||
      'X',

    complainee_showroom:
      complaint.complainee_showroom_name ||
      complaint.complainee_showroom ||
      complaint?.dealer_showroom_details?.complainee_showroom ||
      'X',

    customer_name:
      complaint.customer_name ||
      complaint?.customer_details?.customer_name ||
      '',

    customer_mobile:
      complaint.customer_mobile ||
      complaint.contact_number ||
      complaint?.customer_details?.contact_number ||
      '',

    email:
      complaint.email ||
      complaint?.customer_details?.email ||
      '',

    customer_address:
      complaint.customer_address ||
      complaint.address ||
      complaint?.customer_details?.address ||
      '',

    customer_city:
      complaint.customer_city ||
      complaint.city ||
      complaint?.customer_details?.city ||
      '',

    customer_pin:
      complaint.customer_pin ||
      complaint.pin ||
      complaint?.customer_details?.pin ||
      '',

    customer_pan:
      complaint.customer_pan ||
      complaint.pan ||
      complaint?.customer_details?.pan ||
      '',

    customer_aadhar:
      complaint.customer_aadhar ||
      complaint.aadhar ||
      complaint?.customer_details?.aadhar ||
      '',

    car_id: complaint.car_id || '',
    variant_id: complaint.variant_id || '',

    vin_number:
      complaint.vin_number ||
      complaint?.vehicle_details?.vin_number ||
      '',

    engine_number:
      complaint.engine_number ||
      complaint?.vehicle_details?.engine_number ||
      '',

    registration_number:
      complaint.registration_number ||
      complaint?.vehicle_details?.registration_number ||
      '',

    registration_date:
      complaint.registration_date ||
      complaint?.vehicle_details?.registration_date ||
      '',

    car_color:
      complaint.car_color ||
      complaint?.vehicle_details?.car_color ||
      '',

    quotation_number:
      complaint.quotation_number ||
      complaint?.quotation_details?.quotation_number ||
      '',

    quotation_date:
      complaint.quotation_date ||
      complaint?.quotation_details?.quotation_date ||
      '',

    tcs_amount:
      complaint.tcs_amount ||
      complaint?.quotation_details?.tcs_amount ||
      '',

    total_offered_price:
      complaint.total_offered_price ||
      complaint?.quotation_details?.total_offered_price ||
      '',

    net_offered_price:
      complaint.net_offered_price ||
      complaint?.quotation_details?.net_offered_price ||
      '',

    booking_file_number:
      complaint.booking_file_number ||
      complaint?.booking_details?.booking_file_number ||
      '',

    receipt_number:
      complaint.receipt_number ||
      complaint?.booking_details?.receipt_number ||
      '',

    booking_amount:
      complaint.booking_amount ||
      complaint?.booking_details?.booking_amount ||
      '',

    mode_of_payment:
      complaint.mode_of_payment ||
      complaint?.booking_details?.mode_of_payment ||
      '',

    instrument_date:
      complaint.instrument_date ||
      complaint?.booking_details?.instrument_date ||
      '',

    instrument_number:
      complaint.instrument_number ||
      complaint?.booking_details?.instrument_number ||
      '',

    bank_name:
      complaint.bank_name ||
      complaint?.booking_details?.bank_name ||
      '',

    complaint_raised_date:
      complaint.date_of_complaint ||
      complaint.complaint_raised_date ||
      complaint?.remarks_page?.complaint_raised_date ||
      today,

    aa_name:
      complaint.remark_complainee_aa ||
      complaint.aa_name ||
      complaint?.remarks_page?.aa_name ||
      '',

    remarks_by_complainant:
      complaint.remarks_complainant ||
      complaint.remarks_by_complainant ||
      complaint?.remarks_page?.remarks_by_complainant ||
      '',

    remarks_by_aa:
      complaint.remark_admin ||
      complaint.remarks_by_aa ||
      complaint?.remarks_page?.remarks_by_aa ||
      '',

    status: complaint.status || '',

    ex_showroom_price:
      complaint.ex_showroom_price ||
      complaint?.price_info?.ex_showroom_price ||
      '',

    insurance:
      complaint.insurance ||
      complaint?.price_info?.insurance ||
      '',

    registration_road_tax:
      complaint.registration_road_tax ||
      complaint?.price_info?.registration_road_tax ||
      '',

    discount:
      complaint.discount ||
      complaint?.price_info?.discount ||
      '',

    accessories_charged:
      complaint.accessories_charged ||
      complaint?.price_info?.accessories_charged ||
      '',
  };
};

const buildComplaintPayload = (form) => {
  return {
    stage: 'complaint',
    variant_id: form.variant_id || null,
    employee_id: 'unknown',

    dealer_showroom_details: {
      complainant_dealership: form.complainant_dealership || null,
      complainant_showroom: form.complainant_showroom || null,
      complainee_dealership: form.complainee_dealership || null,
      complainee_showroom: form.complainee_showroom || null,
    },

    customer_details: {
      customer_name: form.customer_name || null,
      contact_number: form.customer_mobile || null,
      email: form.email || null,
      address: form.customer_address || null,
      city: form.customer_city || null,
      pin: form.customer_pin || null,
      pan: form.customer_pan || null,
      aadhar: form.customer_aadhar || null,
    },

    vehicle_details: {
      vin_number: form.vin_number || null,
      engine_number: form.engine_number || null,
      registration_number: form.registration_number || null,
      registration_date: form.registration_date || null,
      car_color: form.car_color || null,
    },

    quotation_details: {
      quotation_number: form.quotation_number || null,
      quotation_date: form.quotation_date || null,
      tcs_amount: cleanNumber(form.tcs_amount),
      total_offered_price: cleanNumber(form.total_offered_price),
      net_offered_price: cleanNumber(form.net_offered_price),
    },

    booking_details: {
      booking_file_number: form.booking_file_number || null,
      receipt_number: form.receipt_number || null,
      booking_amount: cleanNumber(form.booking_amount),
      mode_of_payment: form.mode_of_payment || null,
      instrument_date: form.instrument_date || null,
      instrument_number: form.instrument_number || null,
      bank_name: form.bank_name || null,
    },

    remarks_page: {
      complaint_raised_date: form.complaint_raised_date || null,
      aa_name: form.aa_name || null,
      remarks_by_complainant: form.remarks_by_complainant || null,
      remarks_by_aa: form.remarks_by_aa || null,
    },

    price_info: {
      ex_showroom_price: cleanNumber(form.ex_showroom_price),
      insurance: cleanNumber(form.insurance),
      registration_road_tax: cleanNumber(form.registration_road_tax),
      discount: cleanNumber(form.discount),
      accessories_charged: cleanNumber(form.accessories_charged),
    },
  };
};

const normalisePageMode = (mode) => {
  const path = String(window.location.pathname || '').toLowerCase();

  if (mode === 'form' || path.includes('/complaints/form')) return 'form';
  if (mode === 'register' || path.includes('/complaints/register')) return 'register';

  return 'both';
};

export default function ComplaintsPage({ mode = 'both' }) {
  const pageMode = normalisePageMode(mode);

  const showForm = pageMode === 'form' || pageMode === 'both';
  const showRegister = pageMode === 'register' || pageMode === 'both';

  const transactionId = getQueryParam('transaction_id');
  const complaintCode = getQueryParam('complaint_code');

  const isEditMode = Boolean(transactionId || complaintCode);

  const [form, setForm] = useState(EMPTY_FORM);

  const [reference, setReference] = useState({
    dealerships: [],
    outlets: [],
    cars: [],
    variants: [],
  });

  const [complaints, setComplaints] = useState([]);
  const [complainantOutlets, setComplainantOutlets] = useState([]);
  const [complaineeOutlets, setComplaineeOutlets] = useState(['X']);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [search, setSearch] = useState('');

  const complaintTitle = isEditMode
    ? complaintCode
      ? `Edit Complaint ${complaintCode}`
      : `Edit Complaint #${transactionId}`
    : 'New Complaint';

  const pageTitle =
    pageMode === 'form'
      ? 'Raise Complaint'
      : pageMode === 'register'
        ? 'Complaint Register'
        : 'Complaints';

  const pageDescription =
    pageMode === 'form'
      ? 'Submit a new inter-dealership complaint for review.'
      : pageMode === 'register'
        ? 'Review, search and edit inter-dealership complaint records.'
        : 'Create, edit and review inter-dealership complaint records.';

  const filteredComplaineeDealerships = useMemo(() => {
    const list = reference.dealerships || [];
    return list.filter((dealer) => dealer.name !== form.complainant_dealership);
  }, [reference.dealerships, form.complainant_dealership]);

  const filteredVariants = useMemo(() => {
    if (!form.car_id) return reference.variants || [];

    return (reference.variants || []).filter(
      (variant) =>
        String(variant.car_id || variant.carId || '') === String(form.car_id)
    );
  }, [reference.variants, form.car_id]);

  const filteredComplaints = useMemo(() => {
    const text = String(search || '').trim().toLowerCase();

    if (!text) return complaints;

    return complaints.filter((row) =>
      Object.values(row || {})
        .map((value) => String(value || '').toLowerCase())
        .join(' ')
        .includes(text)
    );
  }, [complaints, search]);

  const setValue = (key, value) => {
    setForm((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  async function fetchReferenceData() {
    try {
      const data = await api.get('/reference-data');

      setReference({
        dealerships: data?.dealerships || [],
        outlets: data?.outlets || [],
        cars: data?.cars || [],
        variants: data?.variants || [],
      });
    } catch {
      try {
        const [dealerships, outlets, cars, variants] = await Promise.all([
          api.get('/dealerships'),
          api.get('/outlets'),
          api.get('/cars'),
          api.get('/variants'),
        ]);

        setReference({
          dealerships: Array.isArray(dealerships) ? dealerships : [],
          outlets: Array.isArray(outlets) ? outlets : [],
          cars: Array.isArray(cars) ? cars : [],
          variants: Array.isArray(variants) ? variants : [],
        });
      } catch (e) {
        setError(e.message || 'Unable to load reference data.');
      }
    }
  }

  async function fetchComplaints() {
    try {
      const result = await api.get('/complaints/');
      const rows = Array.isArray(result)
        ? result
        : result?.data || result?.items || result?.results || [];

      setComplaints(rows);
    } catch (e) {
      setError(e.message || 'Unable to load complaints.');
    }
  }

  async function fetchOutletsByDealerName(dealerName, target) {
    if (!dealerName || dealerName === 'X') {
      if (target === 'complainant') setComplainantOutlets([]);
      if (target === 'complainee') setComplaineeOutlets(['X']);
      return;
    }

    try {
      const outlets = await api.get(
        `/complaints/dealerships/${encodeURIComponent(dealerName)}/outlets`
      );

      const list = Array.isArray(outlets) ? outlets : [];

      if (target === 'complainant') {
        setComplainantOutlets(list);
      }

      if (target === 'complainee') {
        setComplaineeOutlets(['X', ...list]);
      }
    } catch (e) {
      setError(e.message || 'Unable to fetch showroom list.');
    }
  }

  async function loadExistingComplaint() {
    if (!isEditMode) return;

    setLoading(true);
    setError('');

    try {
      const result = await api.get('/complaints/');
      const rows = Array.isArray(result)
        ? result
        : result?.data || result?.items || result?.results || [];

      const target = rows.find((item) => {
        if (complaintCode) return item.complaint_code === complaintCode;
        return String(item.id || item.transaction_id || '') === String(transactionId);
      });

      if (!target) {
        setError('Complaint not found.');
        return;
      }

      const normalised = normaliseComplaintForEdit(target);
      setForm(normalised);

      if (normalised.complainant_dealership) {
        await fetchOutletsByDealerName(
          normalised.complainant_dealership,
          'complainant'
        );
      }

      if (
        normalised.complainee_dealership &&
        normalised.complainee_dealership !== 'X'
      ) {
        await fetchOutletsByDealerName(
          normalised.complainee_dealership,
          'complainee'
        );
      }
    } catch (e) {
      setError(e.message || 'Unable to load complaint.');
    } finally {
      setLoading(false);
    }
  }

  function validate() {
    if (!form.complainant_dealership) {
      return 'Complainant Dealership is mandatory.';
    }

    if (!form.complainant_showroom) {
      return 'Complainant Showroom is mandatory.';
    }

    if (!form.complainee_dealership) {
      return 'Complainee Dealership is mandatory.';
    }

    if (!form.complainee_showroom) {
      return 'Complainee Showroom is mandatory.';
    }

    if (!form.customer_name) {
      return 'Customer Name is mandatory.';
    }

    if (!form.customer_mobile) {
      return 'Customer Mobile is mandatory.';
    }

    if (!form.remarks_by_complainant) {
      return 'Remarks by Complainant is mandatory.';
    }

    if (form.quotation_date && !isValidDate(form.quotation_date)) {
      return 'Quotation Date is invalid.';
    }

    if (form.instrument_date && !isValidDate(form.instrument_date)) {
      return 'Instrument Date is invalid.';
    }

    if (form.registration_date && !isValidDate(form.registration_date)) {
      return 'Registration Date is invalid.';
    }

    if (form.complaint_raised_date && !isValidDate(form.complaint_raised_date)) {
      return 'Date of Complaint Raised is invalid.';
    }

    return '';
  }

  async function saveComplaint() {
    setError('');
    setSuccess('');

    const validationError = validate();

    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);

    try {
      const payload = buildComplaintPayload(form);

      if (isEditMode) {
        payload.id = form.id || transactionId || null;
        payload.complaint_code = form.complaint_code || complaintCode || null;
      }

      await api.post('/complaints/save-complaint', payload);

      setSuccess('Complaint submitted successfully.');

      if (!isEditMode) {
        setForm({ ...EMPTY_FORM, complaint_raised_date: today });
        setComplainantOutlets([]);
        setComplaineeOutlets(['X']);
      }

      if (showRegister || isEditMode) {
        await fetchComplaints();
      }
    } catch (e) {
      setError(e.message || 'Unable to submit complaint.');
    } finally {
      setSaving(false);
    }
  }

  function editComplaint(row) {
    const code = row.complaint_code;

    if (code) {
      window.location.href = `/complaints/form?complaint_code=${encodeURIComponent(
        code
      )}`;
      return;
    }

    const id = row.id || row.transaction_id;

    if (id) {
      window.location.href = `/complaints/form?transaction_id=${id}`;
    }
  }

  useEffect(() => {
    fetchReferenceData();

    if (showRegister || isEditMode) {
      fetchComplaints();
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadExistingComplaint();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [transactionId, complaintCode]);

  const complaintColumns = [
    'complaint_code',
    'customer_name',
    'customer_mobile',
    'complainant_dealer_name',
    'complainant_showroom_name',
    'complainee_dealer_name',
    'complainee_showroom_name',
    'status',
    'date_of_complaint',
  ];

  return (
    <>
      <PageHeader
        title={pageTitle}
        description={pageDescription}
        actions={
          showRegister ? (
            <Button onClick={() => (window.location.href = '/complaints/form')}>
              New Complaint
            </Button>
          ) : null
        }
      />

      <Alert type="error">{error}</Alert>
      <Alert type="success">{success}</Alert>

      {loading ? (
        <Loader />
      ) : (
        <div className="mx-auto max-w-[1100px]">
          {showForm ? (
            <>
              <h1 className="mb-5 text-2xl font-bold text-slate-900 dark:text-white">
                {complaintTitle}
              </h1>

              <Section icon="🏢" title="Dealership Details">
                <div className="grid gap-5 md:grid-cols-2">
                  <Field label="Complainant Dealership *">
                    <Select
                      value={form.complainant_dealership}
                      onChange={async (e) => {
                        const value = e.target.value;

                        setForm((prev) => ({
                          ...prev,
                          complainant_dealership: value,
                          complainant_showroom: '',
                          complainee_dealership:
                            prev.complainee_dealership === value
                              ? 'X'
                              : prev.complainee_dealership,
                          complainee_showroom:
                            prev.complainee_dealership === value
                              ? 'X'
                              : prev.complainee_showroom,
                        }));

                        await fetchOutletsByDealerName(value, 'complainant');
                      }}
                    >
                      <option value="">Select</option>

                      {reference.dealerships.map((dealer) => (
                        <option key={dealer.id || dealer.name} value={dealer.name}>
                          {dealer.name}
                        </option>
                      ))}
                    </Select>
                  </Field>

                  <Field label="Showroom *">
                    <Select
                      value={form.complainant_showroom}
                      onChange={(e) =>
                        setValue('complainant_showroom', e.target.value)
                      }
                    >
                      <option value="">Select</option>

                      {complainantOutlets.map((outlet) => (
                        <option key={outlet} value={outlet}>
                          {outlet}
                        </option>
                      ))}
                    </Select>
                  </Field>

                  <Field label="Complainee Dealership *">
                    <Select
                      value={form.complainee_dealership}
                      onChange={async (e) => {
                        const value = e.target.value;

                        setForm((prev) => ({
                          ...prev,
                          complainee_dealership: value,
                          complainee_showroom: value === 'X' ? 'X' : '',
                        }));

                        await fetchOutletsByDealerName(value, 'complainee');
                      }}
                    >
                      <option value="X">X</option>

                      {filteredComplaineeDealerships.map((dealer) => (
                        <option key={dealer.id || dealer.name} value={dealer.name}>
                          {dealer.name}
                        </option>
                      ))}
                    </Select>
                  </Field>

                  <Field label="Showroom *">
                    <Select
                      value={form.complainee_showroom}
                      onChange={(e) =>
                        setValue('complainee_showroom', e.target.value)
                      }
                    >
                      {complaineeOutlets.map((outlet) => (
                        <option key={outlet} value={outlet}>
                          {outlet}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>
              </Section>

              <Section icon="👤" title="Customer Details">
                <div className="grid gap-5 md:grid-cols-2">
                  <Field label="Customer Name *">
                    <Input
                      value={form.customer_name}
                      onChange={(e) => setValue('customer_name', e.target.value)}
                    />
                  </Field>

                  <Field label="Mobile Number *">
                    <Input
                      value={form.customer_mobile}
                      onChange={(e) => setValue('customer_mobile', e.target.value)}
                    />
                  </Field>

                  <Field label="Email">
                    <Input
                      value={form.email}
                      onChange={(e) => setValue('email', e.target.value)}
                    />
                  </Field>

                  <Field label="City">
                    <Input
                      value={form.customer_city}
                      onChange={(e) => setValue('customer_city', e.target.value)}
                    />
                  </Field>

                  <Field label="PIN Code">
                    <Input
                      value={form.customer_pin}
                      onChange={(e) => setValue('customer_pin', e.target.value)}
                    />
                  </Field>

                  <Field label="PAN">
                    <Input
                      value={form.customer_pan}
                      onChange={(e) => setValue('customer_pan', e.target.value)}
                    />
                  </Field>

                  <Field label="Aadhar">
                    <Input
                      value={form.customer_aadhar}
                      onChange={(e) => setValue('customer_aadhar', e.target.value)}
                    />
                  </Field>

                  <Field label="Address">
                    <Input
                      value={form.customer_address}
                      onChange={(e) => setValue('customer_address', e.target.value)}
                    />
                  </Field>
                </div>
              </Section>

              <Section icon="🚘" title="Vehicle Details">
                <div className="grid gap-5 md:grid-cols-3">
                  <Field label="Car Model">
                    <Select
                      value={form.car_id}
                      onChange={(e) =>
                        setForm((prev) => ({
                          ...prev,
                          car_id: e.target.value,
                          variant_id: '',
                        }))
                      }
                    >
                      <option value="">Select</option>

                      {reference.cars.map((car) => (
                        <option key={car.id} value={car.id}>
                          {car.name}
                        </option>
                      ))}
                    </Select>
                  </Field>

                  <Field label="Variant">
                    <Select
                      value={form.variant_id}
                      onChange={(e) => setValue('variant_id', e.target.value)}
                    >
                      <option value="">Select</option>

                      {filteredVariants.map((variant) => (
                        <option key={variant.id} value={variant.id}>
                          {variant.name ||
                            variant.variant_name ||
                            variant.full_variant_name}
                        </option>
                      ))}
                    </Select>
                  </Field>

                  <Field label="Colour">
                    <Input
                      value={form.car_color}
                      onChange={(e) => setValue('car_color', e.target.value)}
                    />
                  </Field>

                  <Field label="VIN Number">
                    <Input
                      value={form.vin_number}
                      onChange={(e) => setValue('vin_number', e.target.value)}
                    />
                  </Field>

                  <Field label="Engine Number">
                    <Input
                      value={form.engine_number}
                      onChange={(e) => setValue('engine_number', e.target.value)}
                    />
                  </Field>

                  <Field label="Registration Number">
                    <Input
                      value={form.registration_number}
                      onChange={(e) =>
                        setValue('registration_number', e.target.value)
                      }
                    />
                  </Field>

                  <Field label="Registration Date">
                    <Input
                      type="date"
                      value={form.registration_date}
                      onChange={(e) =>
                        setValue('registration_date', e.target.value)
                      }
                    />
                  </Field>
                </div>
              </Section>

              <Section icon="📋" title="Complaint Quotation Details">
                <div className="grid gap-5 md:grid-cols-3">
                  <Field label="Quotation Number">
                    <Input
                      value={form.quotation_number}
                      onChange={(e) =>
                        setValue('quotation_number', e.target.value)
                      }
                    />
                  </Field>

                  <Field label="Quotation Date">
                    <Input
                      type="date"
                      value={form.quotation_date}
                      onChange={(e) => setValue('quotation_date', e.target.value)}
                    />
                  </Field>

                  <Field label="TCS">
                    <Input
                      value={form.tcs_amount}
                      onChange={(e) => setValue('tcs_amount', e.target.value)}
                    />
                  </Field>

                  <Field label="Total Offered Price">
                    <Input
                      value={form.total_offered_price}
                      onChange={(e) =>
                        setValue('total_offered_price', e.target.value)
                      }
                    />
                  </Field>

                  <Field label="Net Offered Price">
                    <Input
                      value={form.net_offered_price}
                      onChange={(e) =>
                        setValue('net_offered_price', e.target.value)
                      }
                    />
                  </Field>
                </div>
              </Section>

              <Section icon="📝" title="Complaint Booking Details">
                <div className="grid gap-5 md:grid-cols-3">
                  <Field label="Booking File Number">
                    <Input
                      value={form.booking_file_number}
                      onChange={(e) =>
                        setValue('booking_file_number', e.target.value)
                      }
                    />
                  </Field>

                  <Field label="Receipt Number">
                    <Input
                      value={form.receipt_number}
                      onChange={(e) => setValue('receipt_number', e.target.value)}
                    />
                  </Field>

                  <Field label="Booking Amount">
                    <Input
                      value={form.booking_amount}
                      onChange={(e) => setValue('booking_amount', e.target.value)}
                    />
                  </Field>

                  <Field label="Mode of Payment">
                    <Input
                      list="mode-of-payment-options"
                      value={form.mode_of_payment}
                      onChange={(e) => setValue('mode_of_payment', e.target.value)}
                    />

                    <datalist id="mode-of-payment-options">
                      {modeOfPaymentOptions.map((option) => (
                        <option key={option} value={option} />
                      ))}
                    </datalist>
                  </Field>

                  <Field label="Instrument Date">
                    <Input
                      type="date"
                      value={form.instrument_date}
                      onChange={(e) => setValue('instrument_date', e.target.value)}
                    />
                  </Field>

                  <Field label="Instrument Number">
                    <Input
                      value={form.instrument_number}
                      onChange={(e) =>
                        setValue('instrument_number', e.target.value)
                      }
                    />
                  </Field>

                  <Field label="Bank Name">
                    <Input
                      value={form.bank_name}
                      onChange={(e) => setValue('bank_name', e.target.value)}
                    />
                  </Field>
                </div>
              </Section>

              <Section icon="💰" title="Price Information">
                <div className="grid gap-5 md:grid-cols-3">
                  <Field label="Ex Showroom Price">
                    <Input
                      value={form.ex_showroom_price}
                      onChange={(e) =>
                        setValue('ex_showroom_price', e.target.value)
                      }
                    />
                  </Field>

                  <Field label="Insurance">
                    <Input
                      value={form.insurance}
                      onChange={(e) => setValue('insurance', e.target.value)}
                    />
                  </Field>

                  <Field label="Registration / Road Tax">
                    <Input
                      value={form.registration_road_tax}
                      onChange={(e) =>
                        setValue('registration_road_tax', e.target.value)
                      }
                    />
                  </Field>

                  <Field label="Discount">
                    <Input
                      value={form.discount}
                      onChange={(e) => setValue('discount', e.target.value)}
                    />
                  </Field>

                  <Field label="Accessories Charged">
                    <Input
                      value={form.accessories_charged}
                      onChange={(e) =>
                        setValue('accessories_charged', e.target.value)
                      }
                    />
                  </Field>
                </div>
              </Section>

              <Section icon="💬" title="Remarks">
                <div className="grid gap-5 md:grid-cols-2">
                  <Field label="Date of Complaint Raised">
                    <Input
                      type="date"
                      value={form.complaint_raised_date}
                      onChange={(e) =>
                        setValue('complaint_raised_date', e.target.value)
                      }
                    />
                  </Field>

                  <Field label="Audit Assistant Name at Complainee">
                    <Input
                      value={form.aa_name}
                      onChange={(e) => setValue('aa_name', e.target.value)}
                    />
                  </Field>

                  <TextAreaField
                    label="Remarks by Complainant *"
                    value={form.remarks_by_complainant}
                    onChange={(e) =>
                      setValue('remarks_by_complainant', e.target.value)
                    }
                    required
                  />

                  <TextAreaField
                    label="Remarks by Audit Assistant at Complainant"
                    value={form.remarks_by_aa}
                    onChange={(e) => setValue('remarks_by_aa', e.target.value)}
                  />
                </div>
              </Section>

              <div className="mb-8 flex items-center justify-between py-4">
                <Button
                  variant="secondary"
                  onClick={() => {
                    window.location.href =
                      pageMode === 'form' ? '/' : '/complaints/register';
                  }}
                >
                  ← {pageMode === 'form' ? 'Back to Dashboard' : 'Back to Register'}
                </Button>

                <Button onClick={saveComplaint} disabled={saving}>
                  <Save size={16} />
                  {saving ? 'Submitting...' : 'Submit Complaint'}
                </Button>
              </div>
            </>
          ) : null}

          {showRegister ? (
            <Section icon="📑" title="Complaint Register">
              <div className="mb-4 flex items-center gap-3">
                <div className="max-w-md flex-1">
                  <Input
                    placeholder="Search complaints..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </div>

                <Button variant="secondary" onClick={fetchComplaints}>
                  <RefreshCw size={16} />
                  Refresh
                </Button>
              </div>

              <DataTable
                columns={complaintColumns}
                rows={filteredComplaints}
                actions={(row) => (
                  <button
                    type="button"
                    onClick={() => editComplaint(row)}
                    className="rounded-lg border border-slate-200 p-2 transition hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-900"
                    title="Edit Complaint"
                  >
                    <Edit size={15} />
                  </button>
                )}
              />
            </Section>
          ) : null}
        </div>
      )}
    </>
  );
}
