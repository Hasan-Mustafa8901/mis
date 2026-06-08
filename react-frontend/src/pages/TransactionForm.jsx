// react-frontend/src/pages/TransactionFormPage.jsx

import React, { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Car,
  User,
  CheckSquare,
  BookOpen,
  IndianRupee,
  Wrench,
  ClipboardList,
  FileWarning,
  ReceiptText,
  CreditCard,
  Save,
} from "lucide-react";
import { api } from "../services/apiClient";

const CONDITION_KEYS = {
  "Customer / Commercial": [
    ["exchange", "Exchange"],
    ["corporate", "Corporate"],
    ["govt_employee", "Govt Employee"],
    ["scrap", "Scrap"],
    ["upgrade", "Upgrade"],
  ],
  "Add-on / Insurance": [
    ["self_insurance", "Self Insurance"],
    ["fastag", "FasTag"],
    ["extended_warranty", "Extended Warranty"],
    ["shield_of_trust", "Shield Of Trust"],
    ["tr_case", "TR Case"],
  ],
};

const BOOKING_CHECK_KEYS = [
  ["booking_form", "Booking Form"],
  ["customer_id", "Customer ID"],
  ["pan_card", "PAN Card"],
  ["address_proof", "Address Proof"],
  ["booking_receipt", "Booking Receipt"],
  ["quotation", "Quotation"],
  ["approval", "Approval"],
];

const DELIVERY_CHECK_KEYS = [
  ["invoice", "Invoice"],
  ["insurance", "Insurance"],
  ["rc", "RC"],
  ["gate_pass", "Gate Pass"],
  ["delivery_note", "Delivery Note"],
  ["payment_verified", "Payment Verified"],
  ["file_complete", "File Complete"],
];

const DEFAULT_DISC = new Set([
  "Cash Discount All Customers",
  "Additional Discount From Dealer",
  "Maximum benefit due to price increase",
]);

const CONDITION_DISC_MAP = {
  exchange: ["Exchange Bonus", "Exchange", "Green Bonus"],
  corporate: ["Corporate"],
  scrap: ["Scrappage", "Scrap"],
  upgrade: ["Loyalty", "Upgrade"],
  govt_employee: ["Govt", "Government"],
  tr_case: ["TR Case", "TR"],
};

const CONDITION_PRICE_HIDE_MAP = {
  self_insurance: ["Insurance"],
  fastag: ["FasTag", "Fastag", "FASTag"],
  extended_warranty: ["Extended Warranty", "Entended Warranty"],
  shield_of_trust: ["Shield Of Trust", "Shield of Trust"],
};

const todayISO = () => new Date().toISOString().slice(0, 10);

const cleanNumber = (value) => {
  if (value === null || value === undefined || value === "") return 0;
  const num = String(value).replace(/[₹,\s]/g, "");
  return Number(num || 0);
};

const formatINR = (value) => {
  const num = cleanNumber(value);
  return `₹${num.toLocaleString("en-IN")}`;
};

const conditionBadge = (name) => {
  for (const [key, words] of Object.entries(CONDITION_DISC_MAP)) {
    if (
      words.some((word) =>
        String(name).toLowerCase().includes(word.toLowerCase())
      )
    ) {
      return key;
    }
  }
  return null;
};

const shouldHidePriceComponent = (componentName, conditions) => {
  const name = String(componentName || "").toLowerCase();

  return Object.entries(CONDITION_PRICE_HIDE_MAP).some(
    ([conditionKey, keywords]) => {
      if (!conditions?.[conditionKey]) return false;

      return keywords.some((keyword) =>
        name.includes(String(keyword).toLowerCase())
      );
    }
  );
};

function getSearchParams() {
  return new URLSearchParams(window.location.search);
}

function goTo(path) {
  window.location.href = path;
}

function SectionCard({ icon, title, children, right }) {
  return (
    <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-center gap-2 border-b border-slate-100 pb-3">
        <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-50 text-slate-700">
          {icon}
        </span>
        <h2 className="flex-1 text-[15px] font-bold text-slate-950">
          {title}
        </h2>
        {right}
      </div>
      {children}
    </section>
  );
}

function Input({
  label,
  value,
  onChange,
  type = "text",
  placeholder = "",
  required = false,
  className = "",
  readOnly = false,
}) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </span>
      <input
        type={type}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        readOnly={readOnly}
        className="h-10 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100 disabled:bg-slate-100"
      />
    </label>
  );
}

function TextArea({ label, value, onChange, placeholder = "", className = "" }) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </span>
      <textarea
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={3}
        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100"
      />
    </label>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </span>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : "")}
        className="h-10 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100"
      >
        <option value="">Select</option>
        {(options || []).map((item) => (
          <option key={item.id} value={item.id}>
            {item.name ||
              item.variant_name ||
              item.employee_name ||
              item.executive_name ||
              item.title}
          </option>
        ))}
      </select>
    </label>
  );
}

function MoneyInput({
  label,
  value,
  onChange,
  placeholder = "₹0",
  readOnly = false,
}) {
  return (
    <Input
      label={label}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      readOnly={readOnly}
    />
  );
}

function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 rounded-full transition ${
        checked ? "bg-emerald-500" : "bg-slate-300"
      }`}
    >
      <span
        className={`absolute top-1 h-4 w-4 rounded-full bg-white shadow transition ${
          checked ? "left-6" : "left-1"
        }`}
      />
    </button>
  );
}

export default function TransactionFormPage() {
  const searchParams = getSearchParams();

  const stage = searchParams.get("stage") || "booking";
  const mode = searchParams.get("mode") || "booking";
  const transactionId = searchParams.get("transaction_id");

  const isDelivery = stage === "delivery";
  const isDirectDelivery = mode === "direct";

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [cars, setCars] = useState([]);
  const [variants, setVariants] = useState([]);
  const [outlets, setOutlets] = useState([]);
  const [executives, setExecutives] = useState([]);
  const [components, setComponents] = useState([]);
  const [accessories, setAccessories] = useState([]);

  const [formMode, setFormMode] = useState("booking_create");
  const [bookingData, setBookingData] = useState(null);

  const [form, setForm] = useState({
    car_id: "",
    variant_id: "",
    outlet_id: "",
    sales_executive_id: "",
    customer_file_number: "",
    vin_number: "",
    engine_number: "",
    model_year: "2026",
    registration_number: "",
    registration_date: "",
    color: "",

    customer_name: "",
    mobile_number: "",
    email: "",
    relative_name: "",
    address: "",
    city: "",
    pin_code: "",
    pan_number: "",
    aadhar_number: "",
    other_id_proof: "",

    booking_date: todayISO(),
    booking_amt: "",
    booking_receipt_num: "",
    delivery_date: "",

    invoice_number: "",
    invoice_date: "",
    ex_showroom_price: "",
    discount: "",
    taxable_value: "",
    cgst: "",
    sgst: "",
    igst: "",
    cess: "",
    total_amount: "",

    payment_cash: "",
    payment_bank: "",
    payment_finance: "",
    payment_exchange: "",

    audit_observations: "",
    audit_follow_up_action: "",

    booking_file_incomplete: false,
    booking_file_incomplete_remarks: "",
    delivery_file_incomplete: false,
    delivery_file_incomplete_remarks: "",

    other_discount: "",
    adjustment: "",
    accessory_charged: "",
  });

  const [conditions, setConditions] = useState({});
  const [bookingChecks, setBookingChecks] = useState({});
  const [deliveryChecks, setDeliveryChecks] = useState({});
  const [selectedAccessories, setSelectedAccessories] = useState([]);

  const [actualAmounts, setActualAmounts] = useState({});
  const [allowedAmounts, setAllowedAmounts] = useState({});
  const [priceMatches, setPriceMatches] = useState({});
  const [discountMatches, setDiscountMatches] = useState({});

  useEffect(() => {
    if (!form.variant_id || !form.booking_date || !form.model_year) return;

    let cancelled = false;

    async function fetchPriceListPreview() {
      try {
        const preview = await api.get("/price-list/preview", {
          variant_id: form.variant_id,
          booking_date: form.booking_date,
          model_year: Number(form.model_year),
        });

        if (cancelled) return;

        const nextAllowed = {};
        const nextActual = {};

        Object.entries(preview || {}).forEach(([name, value]) => {
          nextAllowed[name] = cleanNumber(value);

          const matchingComponent = components.find(
            (comp) => comp.name === name
          );

          const isPriceComponent = matchingComponent?.type === "price";
          const isDiscountComponent = matchingComponent?.type === "discount";

          if (!transactionId && isPriceComponent) {
            nextActual[name] = cleanNumber(value);
          }

          if (!transactionId && isDiscountComponent) {
            nextActual[name] = 0;
          }
        });

        setAllowedAmounts(nextAllowed);

        if (!transactionId) {
          setActualAmounts((prev) => ({
            ...prev,
            ...nextActual,
          }));
        }

        if (preview?.["Ex Showroom Price"] !== undefined) {
          setForm((prev) => ({
            ...prev,
            ex_showroom_price: preview["Ex Showroom Price"],
          }));
        }
      } catch (err) {
        if (!cancelled) {
          setAllowedAmounts({});
          console.error("Price list preview failed:", err);
        }
      }
    }

    fetchPriceListPreview();

    return () => {
      cancelled = true;
    };
  }, [form.variant_id, form.booking_date, form.model_year, transactionId, components]);

  const updateForm = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const priceComponents = useMemo(
    () =>
      components
        .filter((c) => c.type === "price")
        .sort((a, b) => (a.order || 99) - (b.order || 99)),
    [components]
  );

  const visiblePriceComponents = useMemo(() => {
    return priceComponents.filter(
      (comp) => !shouldHidePriceComponent(comp.name, conditions)
    );
  }, [priceComponents, conditions]);

  const discountComponents = useMemo(
    () =>
      components
        .filter((c) => c.type === "discount")
        .sort((a, b) => (a.order || 99) - (b.order || 99)),
    [components]
  );

  const filteredVariants = useMemo(() => {
    return variants.filter((v) => Number(v.car_id) === Number(form.car_id));
  }, [variants, form.car_id]);

  const visibleDiscounts = useMemo(() => {
    return discountComponents.filter((comp) => {
      if (DEFAULT_DISC.has(comp.name)) return true;
      const key = conditionBadge(comp.name);
      return key ? Boolean(conditions[key]) : false;
    });
  }, [discountComponents, conditions]);

  const bookingActualAmounts = useMemo(() => {
    if (!isDelivery || isDirectDelivery || !bookingData) return {};

    const map = {};

    if (
      bookingData.actual_amounts &&
      typeof bookingData.actual_amounts === "object"
    ) {
      Object.entries(bookingData.actual_amounts).forEach(([name, value]) => {
        map[name] = cleanNumber(value);
      });
    }

    Object.entries(bookingData || {}).forEach(([rawKey, value]) => {
      if (value === null || value === undefined || value === "") return;

      if (rawKey.endsWith("_actual")) {
        const clean = rawKey.replace(/_actual$/g, "").trim();
        map[clean] = cleanNumber(value);
      }
    });

    return map;
  }, [bookingData, isDelivery, isDirectDelivery]);

  const hydrateAmountsFromTransaction = (txn) => {
    const allowed = {};
    const actual = {};

    Object.entries(txn || {}).forEach(([rawKey, value]) => {
      if (value === null || value === undefined) return;

      const isActual = rawKey.endsWith("_actual");
      const isAllowed =
        rawKey.endsWith("_allowed") || rawKey.endsWith("_listed");
      const clean = rawKey.replace(/_(actual|allowed|listed)$/g, "").trim();

      if (isActual) actual[clean] = value;
      if (isAllowed) allowed[clean] = value;
    });

    setAllowedAmounts((prev) => ({ ...prev, ...allowed }));
    setActualAmounts((prev) => ({ ...prev, ...actual }));
  };

  const hydrateTransaction = (txn) => {
    if (!txn) return;

    setBookingData(txn);
    hydrateAmountsFromTransaction(txn);

    setForm((prev) => ({
      ...prev,
      car_id: txn.car_id || "",
      variant_id: txn.variant_id || "",
      outlet_id: txn.outlet_id || "",
      sales_executive_id: txn.sales_executive_id || "",
      customer_file_number: txn.customer_file_number || "",
      vin_number: txn.vin_number || "",
      engine_number: txn.engine_number || "",
      model_year: txn.model_year || "2026",
      registration_number: txn.registration_number || "",
      registration_date: txn.registration_date || "",
      color: txn.color || "",

      customer_name: txn.customer_name || "",
      mobile_number: txn.mobile_number || "",
      email: txn.email || "",
      address: txn.address || "",
      city: txn.city || "",
      pin_code: txn.pin_code || "",
      pan_number: txn.pan_number || "",
      aadhar_number: txn.aadhar_number || "",

      booking_date: txn.booking_date || todayISO(),
      booking_amt: txn.booking_amt || "",
      booking_receipt_num: txn.booking_receipt_num || "",
      delivery_date: txn.delivery_date || "",

      invoice_number: txn.invoice_number || "",
      invoice_date: txn.invoice_date || "",
      ex_showroom_price: txn.ex_showroom_price || "",
      discount: txn.discount || "",
      taxable_value: txn.taxable_value || "",
      cgst: txn.cgst || "",
      sgst: txn.sgst || "",
      igst: txn.igst || "",
      cess: txn.cess || "",
      total_amount: txn.total_amount || txn.total || "",

      audit_observations: txn.audit_info?.observations || "",
      audit_follow_up_action: txn.audit_info?.follow_up_action || "",
    }));

    setConditions(txn.conditions || {});
    setBookingChecks(txn.booking_checklist || {});
    setDeliveryChecks(txn.delivery_checks || txn.delivery_checklist || {});
  };

  useEffect(() => {
    async function init() {
      try {
        setLoading(true);
        setError("");

        const ref = await api.get("/reference-data").catch(async () => {
          const [
            carsData,
            variantsData,
            outletsData,
            execData,
            compsData,
            accData,
          ] = await Promise.all([
            api.get("/cars"),
            api.get("/variants"),
            api.get("/outlets"),
            api.get("/sales-executives"),
            api.get("/components"),
            api.get("/accessories"),
          ]);

          return {
            cars: carsData,
            variants: variantsData,
            outlets: outletsData,
            executives: execData,
            components: compsData,
            accessories: accData,
          };
        });

        setCars(ref.cars || []);
        setVariants(ref.variants || []);
        setOutlets(ref.outlets || []);
        setExecutives(ref.executives || ref.sales_executives || []);
        setComponents(ref.components || []);
        setAccessories(ref.accessories || []);

        let resolvedMode = "booking_create";
        let txn = null;

        if (stage === "booking") {
          resolvedMode = transactionId ? "booking_edit" : "booking_create";
        }

        if (stage === "delivery") {
          if (mode === "direct") {
            resolvedMode = transactionId
              ? "delivery_edit"
              : "delivery_direct_create";
          } else if (transactionId) {
            txn = await api.get(`/transactions/${transactionId}`);
            resolvedMode =
              txn.stage === "delivery"
                ? "delivery_edit"
                : "delivery_from_booking";
          } else {
            resolvedMode = "delivery_direct_create";
          }
        }

        if (transactionId && !txn) {
          txn = await api.get(`/transactions/${transactionId}`);
        }

        setFormMode(resolvedMode);
        if (txn) hydrateTransaction(txn);
      } catch (err) {
        setError(err.message || "Unable to load form.");
      } finally {
        setLoading(false);
      }
    }

    init();
  }, [stage, mode, transactionId]);

  const accessoryListedTotal = useMemo(() => {
    return selectedAccessories.reduce((sum, id) => {
      const acc = accessories.find((a) => Number(a.id) === Number(id));
      return sum + cleanNumber(acc?.listed_price || 0);
    }, 0);
  }, [selectedAccessories, accessories]);

  useEffect(() => {
    if (accessoryListedTotal && !form.accessory_charged) {
      updateForm("accessory_charged", accessoryListedTotal);
    }
  }, [accessoryListedTotal]);

  const totals = useMemo(() => {
    let totalListedPrice = 0;
    let totalChargedPrice = 0;
    let totalPriceDiff = 0;

    visiblePriceComponents.forEach((comp) => {
      const allowed = cleanNumber(allowedAmounts[comp.name]);
      const actual = cleanNumber(actualAmounts[comp.name]);

      totalListedPrice += allowed;
      totalChargedPrice += actual;

      const diff = allowed - actual;
      if (diff > 0) totalPriceDiff += diff;
    });

    let totalAllowedDiscount = 0;
    let totalGivenDiscount = 0;

    visibleDiscounts.forEach((comp) => {
      const allowed = cleanNumber(allowedAmounts[comp.name]);
      const given = cleanNumber(actualAmounts[comp.name]);
      totalAllowedDiscount += allowed;
      totalGivenDiscount += given;
    });

    const accessoryDiff = Math.max(
      0,
      accessoryListedTotal - cleanNumber(form.accessory_charged)
    );

    const adjustment = cleanNumber(form.adjustment);
    const otherDiscount = cleanNumber(form.other_discount);

    const totalDiscountGiven =
      totalGivenDiscount +
      otherDiscount -
      adjustment;

    const excessDiscount = Math.max(0, totalDiscountGiven - totalAllowedDiscount);

    return {
      totalListedPrice,
      totalChargedPrice,
      totalPriceDiff,
      totalAllowedDiscount,
      totalDiscountGiven,
      excessDiscount,
      accessoryDiff,
    };
  }, [
    visiblePriceComponents,
    visibleDiscounts,
    allowedAmounts,
    actualAmounts,
    accessoryListedTotal,
    form.accessory_charged,
    form.other_discount,
    form.adjustment,
  ]);

  const validate = () => {
    if (!form.variant_id) return "Please select a Car and Variant.";
    if (!form.outlet_id) return "Please select Showroom.";
    if (!form.sales_executive_id) return "Please select Team Leader.";
    if (!String(form.customer_name || "").trim())
      return "Customer name is required.";

    if (!/^[6-9]\d{9}$/.test(form.mobile_number || "")) {
      return "Mobile must be 10 digits starting with 6–9.";
    }

    if (!String(form.address || "").trim()) return "Address is required.";
    if (!String(form.city || "").trim()) return "City is required.";

    if (
      form.pan_number &&
      !/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(form.pan_number.toUpperCase())
    ) {
      return "Valid PAN required.";
    }

    if (!String(form.model_year || "").match(/^\d{4}$/)) {
      return "Valid Model Year is required.";
    }

    if (conditions.tr_case && !form.other_id_proof) {
      return "Other ID Proof required for TR Case.";
    }

    if (
      ["delivery_edit", "delivery_direct_create", "delivery_from_booking"].includes(
        formMode
      )
    ) {
      if (!form.vin_number) return "VIN Number is required.";
      if (!form.engine_number) return "Engine Number is required.";
    }

    return "";
  };

  const buildPayload = () => {
    const selectedItems = selectedAccessories.map((id) => {
      const acc = accessories.find((a) => Number(a.id) === Number(id));
      return {
        id,
        name: acc?.name,
        price: cleanNumber(acc?.listed_price),
      };
    });

    const visiblePriceNames = new Set(
      visiblePriceComponents.map((comp) => comp.name)
    );

    const filteredActualAmounts = Object.fromEntries(
      Object.entries(actualAmounts)
        .filter(([name]) => {
          const isPriceComponent = priceComponents.some(
            (comp) => comp.name === name
          );
          return !isPriceComponent || visiblePriceNames.has(name);
        })
        .map(([name, value]) => [name, cleanNumber(value)])
    );

    const filteredAllowedAmounts = Object.fromEntries(
      Object.entries(allowedAmounts)
        .filter(([name]) => {
          const isPriceComponent = priceComponents.some(
            (comp) => comp.name === name
          );
          return !isPriceComponent || visiblePriceNames.has(name);
        })
        .map(([name, value]) => [name, cleanNumber(value)])
    );

    return {
      variant_id: form.variant_id || null,
      booking_date: form.booking_date || null,
      booking_amt: cleanNumber(form.booking_amt),
      booking_receipt_num: form.booking_receipt_num || null,
      outlet_id: form.outlet_id || null,
      sales_executive_id: form.sales_executive_id || null,

      customer: {
        name: form.customer_name,
        mobile_number: form.mobile_number,
        email: form.email,
        pan_number: form.pan_number?.toUpperCase(),
        aadhar_number: form.aadhar_number,
        address: form.address,
        city: form.city,
        pin_code: form.pin_code,
      },

      customer_file_number: form.customer_file_number,
      vin_number: form.vin_number,
      color: form.color,
      engine_number: form.engine_number,
      model_year: form.model_year,
      registration_number: form.registration_number,
      registration_date: form.registration_date,
      price_adjustment: cleanNumber(form.adjustment),

      actual_amounts: filteredActualAmounts,
      allowed_amounts: filteredAllowedAmounts,
      conditions,

      booking_checklist: bookingChecks,
      delivery_checklist: deliveryChecks,

      accessories_details: {
        items: selectedItems,
        charged_amount: cleanNumber(form.accessory_charged),
        allowed_amount: accessoryListedTotal,
      },
      accessory_ids: selectedAccessories,

      invoice_details: {
        invoice_number: form.invoice_number,
        invoice_date: form.invoice_date,
        ex_showroom_price: cleanNumber(form.ex_showroom_price),
        discount: cleanNumber(form.discount),
        taxable_value: cleanNumber(form.taxable_value),
        cgst: cleanNumber(form.cgst),
        sgst: cleanNumber(form.sgst),
        igst: cleanNumber(form.igst),
        cess: cleanNumber(form.cess),
        total: cleanNumber(form.total_amount),
      },

      payment_details: {
        cash: cleanNumber(form.payment_cash),
        bank: cleanNumber(form.payment_bank),
        finance: cleanNumber(form.payment_finance),
        exchange: cleanNumber(form.payment_exchange),
      },

      audit_info: {
        observations: form.audit_observations,
        follow_up_action: form.audit_follow_up_action,
      },

      file_status: {
        booking_file_incomplete: form.booking_file_incomplete,
        booking_file_incomplete_remarks: form.booking_file_incomplete_remarks,
        delivery_file_incomplete: form.delivery_file_incomplete,
        delivery_file_incomplete_remarks: form.delivery_file_incomplete_remarks,
      },

      stage,
      delivery_date: form.delivery_date || null,
      discount_booking: !isDelivery ? cleanNumber(form.other_discount) : 0,
      other_discount_delivery: isDelivery ? cleanNumber(form.other_discount) : 0,
      adjustment_booking: cleanNumber(form.adjustment),
    };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const msg = validate();

    if (msg) {
      setError(msg);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }

    try {
      setSaving(true);
      setError("");

      const payload = buildPayload();

      if (transactionId) {
        await api.put(`/transactions/${transactionId}`, payload);
      } else {
        await api.post("/transactions", payload);
      }

      goTo(isDelivery ? "/delivery-mis" : "/booking-mis");
    } catch (err) {
      setError(err.message || "Unable to save transaction.");
    } finally {
      setSaving(false);
    }
  };

  const submitText =
    formMode === "booking_edit"
      ? "Update Booking"
      : formMode === "delivery_from_booking"
      ? "Convert to Delivery"
      : formMode === "delivery_edit"
      ? "Update Delivery"
      : isDelivery
      ? "Create Delivery"
      : "Save Booking";

  if (loading) {
    return (
      <div className="flex min-h-[70vh] items-center justify-center bg-slate-50">
        <div className="rounded-2xl bg-white px-6 py-4 text-sm font-semibold text-slate-600 shadow">
          Loading form...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <form onSubmit={handleSubmit} className="mx-auto max-w-[1200px] px-6 py-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-slate-950">
              {transactionId
                ? `Edit Entry #${transactionId}`
                : "New Transaction Entry"}
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              {isDelivery ? "Delivery audit workflow" : "Booking audit workflow"}
            </p>
          </div>

          <span
            className={`rounded-full border px-4 py-1.5 text-xs font-bold uppercase tracking-wide ${
              isDelivery
                ? "border-blue-200 bg-blue-50 text-blue-700"
                : "border-emerald-200 bg-emerald-50 text-emerald-700"
            }`}
          >
            {isDelivery
              ? isDirectDelivery
                ? "Direct Delivery"
                : "Delivery Stage"
              : "Booking Stage"}
          </span>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
            <FileWarning size={18} />
            {error}
          </div>
        )}

        <div className="sticky top-2 z-20 mb-5 flex flex-wrap items-center gap-6 rounded-2xl bg-[#0F1623] px-6 py-3 text-white shadow-xl">
          <span className="text-[10px] font-bold uppercase tracking-[1.2px] text-white/40">
            Live Totals
          </span>
          <span className="hidden h-5 w-px bg-white/10 md:block" />
          <div className="text-xs text-white/50">
            Allowable Discount:{" "}
            <strong className="font-mono text-base text-white">
              {formatINR(totals.totalAllowedDiscount)}
            </strong>
          </div>
          <div className="text-xs text-white/50">
            Discount Given:{" "}
            <strong className="font-mono text-base text-white">
              {formatINR(totals.totalDiscountGiven)}
            </strong>
          </div>
          <div className="text-xs text-white/50">
            Excess Discount:{" "}
            <strong
              className={`font-mono text-base ${
                totals.excessDiscount > 0 ? "text-red-300" : "text-emerald-300"
              }`}
            >
              {formatINR(totals.excessDiscount)}
            </strong>
          </div>
        </div>

        <SectionCard icon={<Car size={18} />} title="Vehicle Details">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            <Select
              label="Car *"
              value={form.car_id}
              onChange={(value) => {
                updateForm("car_id", value);
                updateForm("variant_id", "");
              }}
              options={cars}
            />

            <Select
              label="Variant *"
              value={form.variant_id}
              onChange={(value) => {
                updateForm("variant_id", value);
              }}
              options={filteredVariants}
            />

            <Input
              label="Car Colour"
              value={form.color}
              onChange={(v) => updateForm("color", v)}
            />

            <Select
              label="Team Leader *"
              value={form.sales_executive_id}
              onChange={(value) => updateForm("sales_executive_id", value)}
              options={executives}
            />

            <Input
              label="Customer File No *"
              value={form.customer_file_number}
              onChange={(v) => updateForm("customer_file_number", v)}
            />

            <Input
              label="Model Year *"
              value={form.model_year}
              onChange={(v) => updateForm("model_year", v)}
              placeholder="e.g. 2026"
            />

            <Select
              label="Outlet *"
              value={form.outlet_id}
              onChange={(value) => updateForm("outlet_id", value)}
              options={outlets}
            />

            {isDelivery && (
              <>
                <Input
                  label="VIN Number *"
                  value={form.vin_number}
                  onChange={(v) => updateForm("vin_number", v.toUpperCase())}
                  placeholder="XXX000000XXX00000"
                />
                <Input
                  label="Delivery Date *"
                  type="date"
                  value={form.delivery_date}
                  onChange={(v) => updateForm("delivery_date", v)}
                />
                <Input
                  label="Engine Number *"
                  value={form.engine_number}
                  onChange={(v) => updateForm("engine_number", v.toUpperCase())}
                />
                <Input
                  label="Vehicle Regn Number"
                  value={form.registration_number}
                  onChange={(v) =>
                    updateForm("registration_number", v.toUpperCase())
                  }
                  placeholder="UP32AB0000"
                />
                <Input
                  label="Date of Registration"
                  type="date"
                  value={form.registration_date}
                  onChange={(v) => updateForm("registration_date", v)}
                />
              </>
            )}
          </div>
        </SectionCard>

        <SectionCard icon={<BookOpen size={18} />} title="Booking Details">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            <Input
              label="Booking Date *"
              type="date"
              value={form.booking_date}
              onChange={(v) => updateForm("booking_date", v)}
            />
            <MoneyInput
              label="Booking Amount"
              value={form.booking_amt}
              onChange={(v) => updateForm("booking_amt", v)}
              placeholder="Enter Amount"
            />
            <Input
              label="Booking Receipt Number *"
              value={form.booking_receipt_num}
              onChange={(v) => updateForm("booking_receipt_num", v)}
              placeholder="Enter Receipt Number"
            />
          </div>
        </SectionCard>

        <SectionCard icon={<User size={18} />} title="Customer Details">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            <Input
              label="Name *"
              value={form.customer_name}
              onChange={(v) => updateForm("customer_name", v)}
              placeholder="Full name"
            />
            <Input
              label="Mobile *"
              value={form.mobile_number}
              onChange={(v) => updateForm("mobile_number", v)}
              placeholder="10-digit"
            />
            <Input
              label="Email"
              value={form.email}
              onChange={(v) => updateForm("email", v)}
              placeholder="optional"
            />
            <Input
              label="Relative Name"
              value={form.relative_name}
              onChange={(v) => updateForm("relative_name", v)}
              placeholder="optional"
            />
            <TextArea
              label="Address *"
              value={form.address}
              onChange={(v) => updateForm("address", v)}
              className="md:col-span-2"
            />
            <Input
              label="City *"
              value={form.city}
              onChange={(v) => updateForm("city", v)}
            />
            <Input
              label="Pin Code *"
              value={form.pin_code}
              onChange={(v) => updateForm("pin_code", v)}
              placeholder="6 digits"
            />
            <Input
              label="PAN *"
              value={form.pan_number}
              onChange={(v) => updateForm("pan_number", v.toUpperCase())}
              placeholder="ABCDE1234F"
            />
            <Input
              label="Aadhar"
              value={form.aadhar_number}
              onChange={(v) => updateForm("aadhar_number", v)}
              placeholder="12 digits"
            />
            <Input
              label="Other ID Proof"
              value={form.other_id_proof}
              onChange={(v) => updateForm("other_id_proof", v)}
            />
          </div>
        </SectionCard>

        <SectionCard icon={<CheckSquare size={18} />} title="Sale Conditions">
          <div className="space-y-4">
            {Object.entries(CONDITION_KEYS).map(([group, rows]) => (
              <div key={group}>
                <h3 className="mb-2 text-sm font-bold text-slate-800">
                  {group}
                </h3>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  {rows.map(([key, label]) => (
                    <label
                      key={key}
                      className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700"
                    >
                      <input
                        type="checkbox"
                        checked={Boolean(conditions[key])}
                        onChange={(e) =>
                          setConditions((prev) => ({
                            ...prev,
                            [key]: e.target.checked,
                          }))
                        }
                        className="h-4 w-4 accent-red-600"
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard icon={<Wrench size={18} />} title="Accessories">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            <label className="block">
              <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                Select Accessories
              </span>
              <select
                multiple
                value={selectedAccessories.map(String)}
                onChange={(e) =>
                  setSelectedAccessories(
                    Array.from(e.target.selectedOptions).map((o) =>
                      Number(o.value)
                    )
                  )
                }
                className="min-h-[110px] w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-red-500"
              >
                {accessories.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name} ({formatINR(acc.listed_price)})
                  </option>
                ))}
              </select>
            </label>

            <div className="flex items-center rounded-xl border border-slate-200 bg-slate-50 px-4 text-lg font-bold text-slate-800">
              Total: {formatINR(accessoryListedTotal)}
            </div>

            <MoneyInput
              label="Actual Charged (₹)"
              value={form.accessory_charged}
              onChange={(v) => updateForm("accessory_charged", v)}
            />
          </div>
        </SectionCard>

        <SectionCard
          icon={<IndianRupee size={18} />}
          title="Prices & Discount"
          right={
            <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-slate-600">
              {isDelivery
                ? isDirectDelivery
                  ? "Direct Delivery"
                  : "Delivery Stage"
                : "Booking Stage"}
            </span>
          }
        >
          <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-900">
            Price charged as per books of accounts
          </h3>

          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2 text-left">Particular</th>
                  <th className="px-3 py-2 text-right">Price List</th>
                  {isDelivery && !isDirectDelivery && (
                    <th className="px-3 py-2 text-right">Booking</th>
                  )}
                  <th className="px-3 py-2 text-center">Match</th>
                  <th className="px-3 py-2 text-right">Charged</th>
                  <th className="px-3 py-2 text-right">Difference</th>
                </tr>
              </thead>
              <tbody>
                {visiblePriceComponents.map((comp) => {
                  const allowed = cleanNumber(allowedAmounts[comp.name]);
                  const actual = cleanNumber(actualAmounts[comp.name]);
                  const diff = Math.max(0, allowed - actual);

                  return (
                    <tr
                      key={comp.id || comp.name}
                      className="border-t border-slate-100"
                    >
                      <td className="px-3 py-2 font-medium text-slate-800">
                        {comp.name}
                      </td>
                      <td className="px-3 py-2 text-right font-mono">
                        {formatINR(allowed)}
                      </td>
                      {isDelivery && !isDirectDelivery && (
                        <td className="px-3 py-2 text-right font-mono text-blue-500">
                          {formatINR(bookingActualAmounts[comp.name])}
                        </td>
                      )}
                      <td className="px-3 py-2 text-center">
                        <Toggle
                          checked={Boolean(priceMatches[comp.name])}
                          onChange={(checked) => {
                            setPriceMatches((prev) => ({
                              ...prev,
                              [comp.name]: checked,
                            }));
                            if (checked) {
                              setActualAmounts((prev) => ({
                                ...prev,
                                [comp.name]: cleanNumber(allowedAmounts[comp.name]),
                              }));
                            }
                          }}
                        />
                      </td>
                      <td className="px-3 py-2">
                        <input
                          value={actualAmounts[comp.name] ?? ""}
                          disabled={Boolean(priceMatches[comp.name])}
                          onChange={(e) =>
                            setActualAmounts((prev) => ({
                              ...prev,
                              [comp.name]: e.target.value.replace(/[^\d.]/g, ""),
                            }))
                          }
                          className="ml-auto block h-9 w-36 rounded-lg border border-slate-300 px-2 text-right font-mono outline-none focus:border-red-500 disabled:bg-slate-100"
                          placeholder="₹0"
                        />
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-slate-500">
                        {formatINR(diff)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot className="border-t-2 border-slate-200 bg-slate-50 font-bold">
                <tr>
                  <td className="px-3 py-3 uppercase">Total on-road price</td>
                  <td className="px-3 py-3 text-right font-mono">
                    {formatINR(totals.totalListedPrice)}
                  </td>
                  {isDelivery && !isDirectDelivery && <td />}
                  <td />
                  <td className="px-3 py-3 text-right font-mono">
                    {formatINR(totals.totalChargedPrice)}
                  </td>
                  <td className="px-3 py-3 text-right font-mono">
                    {formatINR(totals.totalPriceDiff)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          <h3 className="mb-2 mt-6 text-sm font-bold uppercase tracking-wide text-slate-900">
            Discounts offered as per books of accounts
          </h3>

          {isDelivery && bookingData && (
            <div className="mb-4 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3">
              <h4 className="mb-2 text-[11px] font-bold uppercase tracking-wide text-blue-700">
                Discounts at time of booking
              </h4>
              <p className="text-xs text-blue-500">
                Booking reference values are retained for delivery audit review.
              </p>
            </div>
          )}

          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2 text-left">Particular</th>
                  <th className="px-3 py-2 text-right">Allowed</th>
                  {isDelivery && !isDirectDelivery && (
                    <th className="px-3 py-2 text-right">Booking</th>
                  )}
                  <th className="px-3 py-2 text-center">Match</th>
                  <th className="px-3 py-2 text-right">Given</th>
                  <th className="px-3 py-2 text-right">Difference</th>
                </tr>
              </thead>
              <tbody>
                {visibleDiscounts.map((comp) => {
                  const allowed = cleanNumber(allowedAmounts[comp.name]);
                  const given = cleanNumber(actualAmounts[comp.name]);
                  const diff = Math.max(0, given - allowed);

                  return (
                    <tr
                      key={comp.id || comp.name}
                      className="border-t border-slate-100"
                    >
                      <td className="px-3 py-2 font-medium text-slate-800">
                        {comp.name}
                      </td>
                      <td className="px-3 py-2 text-right font-mono">
                        {formatINR(allowed)}
                      </td>
                      {isDelivery && !isDirectDelivery && (
                        <td className="px-3 py-2 text-right font-mono text-blue-500">
                          {formatINR(bookingActualAmounts[comp.name])}
                        </td>
                      )}
                      <td className="px-3 py-2 text-center">
                        <Toggle
                          checked={Boolean(discountMatches[comp.name])}
                          onChange={(checked) => {
                            setDiscountMatches((prev) => ({
                              ...prev,
                              [comp.name]: checked,
                            }));
                            if (checked) {
                              setActualAmounts((prev) => ({
                                ...prev,
                                [comp.name]: cleanNumber(allowedAmounts[comp.name]),
                              }));
                            }
                          }}
                        />
                      </td>
                      <td className="px-3 py-2">
                        <input
                          value={actualAmounts[comp.name] ?? ""}
                          disabled={Boolean(discountMatches[comp.name])}
                          onChange={(e) =>
                            setActualAmounts((prev) => ({
                              ...prev,
                              [comp.name]: e.target.value.replace(/[^\d.]/g, ""),
                            }))
                          }
                          className="ml-auto block h-9 w-36 rounded-lg border border-slate-300 px-2 text-right font-mono outline-none focus:border-red-500 disabled:bg-slate-100"
                          placeholder="₹0"
                        />
                      </td>
                      <td
                        className={`px-3 py-2 text-right font-mono ${
                          diff > 0
                            ? "font-bold text-red-600"
                            : "text-slate-400"
                        }`}
                      >
                        {formatINR(diff)}
                      </td>
                    </tr>
                  );
                })}

                <tr className="border-t border-dashed border-slate-200">
                  <td className="px-3 py-3 font-semibold">Other Discount</td>
                  <td className="px-3 py-3 text-right font-mono">—</td>
                  {isDelivery && !isDirectDelivery && <td />}
                  <td />
                  <td className="px-3 py-3">
                    <input
                      value={form.other_discount}
                      onChange={(e) =>
                        updateForm("other_discount", e.target.value)
                      }
                      className="ml-auto block h-9 w-36 rounded-lg border border-slate-300 px-2 text-right font-mono outline-none focus:border-red-500"
                      placeholder="₹0"
                    />
                  </td>
                  <td />
                </tr>

                <tr className="border-t border-dashed border-slate-200">
                  <td className="px-3 py-3 font-semibold">Adjustment</td>
                  <td className="px-3 py-3 text-right font-mono">—</td>
                  {isDelivery && !isDirectDelivery && <td />}
                  <td />
                  <td className="px-3 py-3">
                    <input
                      value={form.adjustment}
                      onChange={(e) => updateForm("adjustment", e.target.value)}
                      className="ml-auto block h-9 w-36 rounded-lg border border-slate-300 px-2 text-right font-mono outline-none focus:border-red-500"
                      placeholder="₹0"
                    />
                  </td>
                  <td />
                </tr>
              </tbody>
              <tfoot className="border-t-2 border-slate-200 bg-slate-50 font-bold">
                <tr>
                  <td className="px-3 py-3 uppercase">Discount Summary</td>
                  <td className="px-3 py-3 text-right font-mono">
                    {formatINR(totals.totalAllowedDiscount)}
                  </td>
                  {isDelivery && !isDirectDelivery && <td />}
                  <td />
                  <td className="px-3 py-3 text-right font-mono">
                    {formatINR(totals.totalDiscountGiven)}
                  </td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>

          <div className="mt-4 flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
            <div>
              <p className="text-sm font-bold uppercase tracking-wide text-slate-600">
                Excess Discount
              </p>
              <p className="text-xs text-slate-400">
                Discount given minus allowed limit
              </p>
            </div>
            <p
              className={`font-mono text-2xl font-black ${
                totals.excessDiscount > 0 ? "text-red-600" : "text-slate-400"
              }`}
            >
              {formatINR(totals.excessDiscount)}
            </p>
          </div>
        </SectionCard>

        <SectionCard
          icon={<CheckSquare size={18} />}
          title={isDelivery ? "Delivery Checklist" : "Booking Checklist"}
        >
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {(isDelivery ? DELIVERY_CHECK_KEYS : BOOKING_CHECK_KEYS).map(
              ([key, label]) => (
                <label
                  key={key}
                  className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700"
                >
                  <input
                    type="checkbox"
                    checked={Boolean(
                      isDelivery ? deliveryChecks[key] : bookingChecks[key]
                    )}
                    onChange={(e) =>
                      isDelivery
                        ? setDeliveryChecks((prev) => ({
                            ...prev,
                            [key]: e.target.checked,
                          }))
                        : setBookingChecks((prev) => ({
                            ...prev,
                            [key]: e.target.checked,
                          }))
                    }
                    className="h-4 w-4 accent-red-600"
                  />
                  {label}
                </label>
              )
            )}
          </div>
        </SectionCard>

        <SectionCard icon={<FileWarning size={18} />} title="File Status">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            {!isDelivery ? (
              <>
                <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    checked={form.booking_file_incomplete}
                    onChange={(e) =>
                      updateForm("booking_file_incomplete", e.target.checked)
                    }
                    className="h-4 w-4 accent-red-600"
                  />
                  Booking File Incomplete
                </label>
                <TextArea
                  label="Reason For Incomplete"
                  value={form.booking_file_incomplete_remarks}
                  onChange={(v) =>
                    updateForm("booking_file_incomplete_remarks", v)
                  }
                  placeholder="Reason for marking incomplete..."
                />
              </>
            ) : (
              <>
                <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    checked={form.delivery_file_incomplete}
                    onChange={(e) =>
                      updateForm("delivery_file_incomplete", e.target.checked)
                    }
                    className="h-4 w-4 accent-red-600"
                  />
                  Delivery File Incomplete
                </label>
                <TextArea
                  label="Reason For Incomplete"
                  value={form.delivery_file_incomplete_remarks}
                  onChange={(v) =>
                    updateForm("delivery_file_incomplete_remarks", v)
                  }
                  placeholder="Reason for marking incomplete..."
                />
              </>
            )}
          </div>
        </SectionCard>

        {isDelivery && (
          <>
            <SectionCard icon={<ReceiptText size={18} />} title="Invoice Details">
              <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
                <Input
                  label="Invoice Number"
                  value={form.invoice_number}
                  onChange={(v) =>
                    updateForm("invoice_number", v.toUpperCase())
                  }
                />
                <Input
                  label="Invoice Date"
                  type="date"
                  value={form.invoice_date}
                  onChange={(v) => updateForm("invoice_date", v)}
                />
                <MoneyInput
                  label="Ex-Showroom Price"
                  value={form.ex_showroom_price}
                  onChange={(v) => updateForm("ex_showroom_price", v)}
                />
                <MoneyInput
                  label="Discount"
                  value={form.discount}
                  onChange={(v) => updateForm("discount", v)}
                />
                <MoneyInput
                  label="Taxable Value"
                  value={form.taxable_value}
                  onChange={(v) => updateForm("taxable_value", v)}
                />
                <MoneyInput
                  label="CGST"
                  value={form.cgst}
                  onChange={(v) => updateForm("cgst", v)}
                />
                <MoneyInput
                  label="SGST"
                  value={form.sgst}
                  onChange={(v) => updateForm("sgst", v)}
                />
                <MoneyInput
                  label="IGST"
                  value={form.igst}
                  onChange={(v) => updateForm("igst", v)}
                />
                <MoneyInput
                  label="CESS"
                  value={form.cess}
                  onChange={(v) => updateForm("cess", v)}
                />
                <MoneyInput
                  label="Total Invoice Value"
                  value={form.total_amount}
                  onChange={(v) => updateForm("total_amount", v)}
                />
              </div>
            </SectionCard>

            <SectionCard icon={<CreditCard size={18} />} title="Payment Received">
              <div className="grid grid-cols-1 gap-5 md:grid-cols-4">
                <MoneyInput
                  label="Cash Payment"
                  value={form.payment_cash}
                  onChange={(v) => updateForm("payment_cash", v)}
                />
                <MoneyInput
                  label="Bank Payment"
                  value={form.payment_bank}
                  onChange={(v) => updateForm("payment_bank", v)}
                />
                <MoneyInput
                  label="Finance"
                  value={form.payment_finance}
                  onChange={(v) => updateForm("payment_finance", v)}
                />
                <MoneyInput
                  label="Exchange"
                  value={form.payment_exchange}
                  onChange={(v) => updateForm("payment_exchange", v)}
                />
              </div>
            </SectionCard>
          </>
        )}

        <SectionCard icon={<ClipboardList size={18} />} title="Audit">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <TextArea
              label="Observations"
              value={form.audit_observations}
              onChange={(v) => updateForm("audit_observations", v)}
              placeholder="Enter observations..."
            />
            <TextArea
              label="Follow-up Action"
              value={form.audit_follow_up_action}
              onChange={(v) => updateForm("audit_follow_up_action", v)}
              placeholder="Enter actions..."
            />
          </div>
        </SectionCard>

        <div className="flex items-center justify-between py-5">
          <button
            type="button"
            onClick={() => goTo(isDelivery ? "/delivery-mis" : "/booking-mis")}
            className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-100 hover:text-slate-800"
          >
            <ArrowLeft size={16} />
            Back to Dashboard
          </button>

          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#E8402A] to-[#c73019] px-8 py-3 text-sm font-black text-white shadow-lg shadow-red-500/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Save size={16} />
            {saving ? "Saving..." : submitText}
          </button>
        </div>
      </form>
    </div>
  );
}