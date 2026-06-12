import { useEffect, useMemo, useState } from "react";
import Alert from "../components/Alert";
import Field, { Select } from "../components/Field";
import Loader from "../components/Loader";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/apiClient";
import GenerateReportButton from '../components/GenerateReportButton';

const DISCOUNT_KEYS = [
  "Cash Discount All Customers",
  "Additional Discount From Dealer",
  "Additional for POI /Corporate Customers",
  "Additional for Exchange Customers",
  "Additional for Scrappage Customers",
  "Additional Loyalty (EV TO EV)",
  "Additional Loyalty (ICE TO EV)",
  "Maximum benefit due to price increase",
];

const PIE_COLORS = [
  "#6366f1",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#06b6d4",
  "#f97316",
  "#84cc16",
];

const CAR_MASTER_LIST = [
  { carName: "Curvv", slug: "curvv", image: "/cars/curvv.png" },
  { carName: "Harrier", slug: "harrier", image: "/cars/harrier.png" },
  { carName: "Safari", slug: "safari", image: "/cars/safari.png" },
  { carName: "Nexon", slug: "nexon", image: "/cars/nexon.png" },
  { carName: "Punch", slug: "punch", image: "/cars/punch.png" },
  { carName: "Tiago", slug: "tiago", image: "/cars/tiago.png" },
  { carName: "Tigor", slug: "tigor", image: "/cars/tigor.png" },
  { carName: "Altroz", slug: "altroz", image: "/cars/altroz.png" },
];

const RTO_CITY_MAP = {
  UP11: "Saharanpur",
  UP12: "Muzaffarnagar",
  UP13: "Bulandshahr",
  UP14: "Ghaziabad",
  UP15: "Meerut",
  UP16: "Noida",
  UP17: "Baghpat",
  UP19: "Shamli",
  UP20: "Bijnor",
  UP21: "Moradabad",
  UP22: "Rampur",
  UP23: "Jyotiba Phule Nagar",
  UP24: "Badaun",
  UP25: "Bareilly",
  UP26: "Pilibhit",
  UP27: "Shahjahanpur",
  UP30: "Hardoi",
  UP31: "Lakhimpur Kheri",
  UP32: "Lucknow",
  UP33: "Raebareli",
  UP34: "Sitapur",
  UP35: "Unnao",
  UP36: "Amethi",
  UP37: "Hapur",
  UP38: "Sambhal",
  UP40: "Bahraich",
  UP41: "Barabanki",
  UP42: "Faizabad / Ayodhya",
  UP43: "Gonda",
  UP44: "Sultanpur",
  UP45: "Ambedkar Nagar",
  UP46: "Shravasti",
  UP47: "Balrampur",
  UP50: "Azamgarh",
  UP51: "Basti",
  UP52: "Deoria",
  UP53: "Gorakhpur",
  UP54: "Mau",
  UP55: "Siddharth Nagar",
  UP56: "Maharajganj",
  UP57: "Kushinagar",
  UP58: "Sant Kabir Nagar",
  UP60: "Ballia",
  UP61: "Ghazipur",
  UP62: "Jaunpur",
  UP63: "Mirzapur",
  UP64: "Sonbhadra",
  UP65: "Varanasi",
  UP66: "Bhadohi",
  UP67: "Chandauli",
  UP70: "Prayagraj",
  UP71: "Fatehpur",
  UP72: "Pratapgarh",
  UP73: "Kaushambi",
  UP74: "Kannauj",
  UP75: "Etawah",
  UP76: "Farrukhabad",
  UP77: "Kanpur Dehat",
  UP78: "Kanpur Nagar",
  UP79: "Auraiya",
  UP80: "Agra",
  UP81: "Aligarh",
  UP82: "Etah",
  UP83: "Firozabad",
  UP84: "Mainpuri",
  UP85: "Mathura",
  UP86: "Hathras",
  UP87: "Kasganj",
  UP90: "Banda",
  UP91: "Hamirpur",
  UP92: "Jalaun",
  UP93: "Jhansi",
  UP94: "Lalitpur",
  UP95: "Mahoba",
  UP96: "Chitrakoot",
};

const cleanNumber = (value) => {
  const num = Number(value || 0);
  return Number.isFinite(num) ? num : 0;
};

const formatMoney = (value) => {
  return `₹${Math.round(cleanNumber(value)).toLocaleString("en-IN")}`;
};

const monthLabel = (ym) => {
  try {
    const [year, month] = String(ym).split("-");
    const date = new Date(Number(year), Number(month) - 1, 1);

    return date.toLocaleString("en-IN", {
      month: "short",
      year: "2-digit",
    });
  } catch {
    return ym;
  }
};

const getAllowedDiscountBooking = (txn) => {
  return DISCOUNT_KEYS.reduce((sum, key) => {
    return sum + cleanNumber(txn?.[`${key}_allowed`]);
  }, 0);
};

const getUserRole = (user) => {
  const role = Array.isArray(user?.role) ? user.role[0] : user?.role;
  return String(role || "").toLowerCase();
};

const getAllowedOutletIds = (user) => {
  const ids = user?.allowed_outlet_ids || user?.allowedOutletIds || [];
  return Array.isArray(ids) ? ids.map((id) => Number(id)) : [];
};

const getMonthMap = (transactions) => {
  const map = {};

  transactions.forEach((txn) => {
    const bookingDate = txn?.booking_date || "";

    if (bookingDate && bookingDate.length >= 7) {
      const month = bookingDate.slice(0, 7);

      if (!map[month]) map[month] = [];
      map[month].push(txn);
    }
  });

  return map;
};

const sortEntries = (obj, limit = 8) => {
  return Object.entries(obj || {})
    .sort((a, b) => cleanNumber(b[1]) - cleanNumber(a[1]))
    .slice(0, limit);
};

const slugify = (value) => {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
};

const normaliseCarName = (txn) => {
  const rawName = String(
    txn.car_name ||
    txn.car ||
    txn.model_name ||
    txn.car_model ||
    txn.variant_name ||
    txn.full_variant_name ||
    txn.variant ||
    "",
  ).toLowerCase();

  const matchedCar = CAR_MASTER_LIST.find((car) =>
    rawName.includes(car.slug.toLowerCase()),
  );

  if (matchedCar) return matchedCar.carName;

  return (
    txn.car_name ||
    txn.car ||
    txn.model_name ||
    txn.car_model ||
    (txn.variant_name ? String(txn.variant_name).split(" ")[0] : "") ||
    "Unknown Car"
  );
};

const getCarImage = (carName) => {
  const slug = slugify(carName);
  const found = CAR_MASTER_LIST.find((car) => car.slug === slug);
  return found?.image || "";
};

const createEmptyCarAnalytics = (car) => {
  return {
    carName: car.carName,
    slug: car.slug,
    image: car.image,
    bookings: 0,
    deliveries: 0,
    totalTransactions: 0,
    allowedDiscount: 0,
    actualDiscount: 0,
    excessDiscount: 0,
    bookingAmount: 0,
    priceOffered: 0,
    variants: {},
    outlets: {},
  };
};

const buildCarWiseAnalytics = (transactions) => {
  const map = {};

  CAR_MASTER_LIST.forEach((car) => {
    map[car.carName] = createEmptyCarAnalytics(car);
  });

  transactions.forEach((txn) => {
    const carName = normaliseCarName(txn);

    if (!map[carName]) {
      map[carName] = {
        carName,
        slug: slugify(carName),
        image: getCarImage(carName),
        bookings: 0,
        deliveries: 0,
        totalTransactions: 0,
        allowedDiscount: 0,
        actualDiscount: 0,
        excessDiscount: 0,
        bookingAmount: 0,
        priceOffered: 0,
        variants: {},
        outlets: {},
      };
    }

    const item = map[carName];
    const isDelivery = txn.stage === "delivery";

    item.totalTransactions += 1;
    item.bookings += isDelivery ? 0 : 1;
    item.deliveries += isDelivery ? 1 : 0;

    const allowed = isDelivery
      ? cleanNumber(txn.total_allowed_discount)
      : getAllowedDiscountBooking(txn);

    const actual = isDelivery
      ? cleanNumber(txn.total_actual_discount)
      : cleanNumber(txn.total_discount_booking);

    const excess = isDelivery
      ? cleanNumber(txn.total_excess_discount)
      : cleanNumber(txn.excess_booking);

    item.allowedDiscount += allowed;
    item.actualDiscount += actual;
    item.excessDiscount += excess;

    item.bookingAmount += cleanNumber(
      txn.booking_amt || txn.booking_amount || txn.bookingAmount,
    );

    item.priceOffered += cleanNumber(
      txn.price_offered ||
      txn.final_price ||
      txn.priceOffered ||
      txn.ex_showroom_price ||
      txn.ex_showroom_price_actual,
    );

    const variant =
      txn.variant_name ||
      txn.full_variant_name ||
      txn.variant ||
      "Unknown Variant";

    const outlet = txn.outlet_name || txn.outlet || "Unknown Outlet";

    item.variants[variant] = (item.variants[variant] || 0) + 1;
    item.outlets[outlet] = (item.outlets[outlet] || 0) + 1;
  });

  return Object.values(map).sort((a, b) => {
    const masterA = CAR_MASTER_LIST.findIndex(
      (car) => car.carName === a.carName,
    );
    const masterB = CAR_MASTER_LIST.findIndex(
      (car) => car.carName === b.carName,
    );

    const indexA = masterA === -1 ? 999 : masterA;
    const indexB = masterB === -1 ? 999 : masterB;

    if (indexA !== indexB) return indexA - indexB;

    return b.totalTransactions - a.totalTransactions;
  });
};

const normalizeNameKey = (value) => {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "")
    .trim();
};

const buildShowroomWiseAnalytics = (transactions, outlets = []) => {
  const map = {};
  const outletNameToKey = {};

  outlets.forEach((outlet) => {
    const showroomName =
      outlet?.name ||
      outlet?.outlet_name ||
      outlet?.showroom_name ||
      `Outlet #${outlet?.id}`;

    const showroomKey = outlet?.id
      ? `outlet-${outlet.id}`
      : `name-${normalizeNameKey(showroomName)}`;

    map[showroomKey] = {
      key: showroomKey,
      id: outlet?.id || showroomKey,
      showroomName,
      dealershipId: outlet?.dealership_id || outlet?.dealershipId || null,
      bookings: 0,
      deliveries: 0,
      totalTransactions: 0,
      allowedDiscount: 0,
      actualDiscount: 0,
      excessDiscount: 0,
      bookingAmount: 0,
      priceOffered: 0,
      cars: {},
      variants: {},
    };

    outletNameToKey[normalizeNameKey(showroomName)] = showroomKey;
  });

  transactions.forEach((txn) => {
    const outletId =
      txn.outlet_id ||
      txn.outletId ||
      txn.showroom_id ||
      txn.showroomId ||
      null;

    const outletName =
      txn.outlet_name ||
      txn.showroom_name ||
      txn.outlet ||
      txn.showroom ||
      "Unknown Showroom";

    const showroomKey = outletId
      ? `outlet-${outletId}`
      : outletNameToKey[normalizeNameKey(outletName)] ||
      `name-${normalizeNameKey(outletName)}`;

    if (!map[showroomKey]) {
      map[showroomKey] = {
        key: showroomKey,
        id: outletId || showroomKey,
        showroomName: outletName,
        dealershipId: txn.dealership_id || txn.dealershipId || null,
        bookings: 0,
        deliveries: 0,
        totalTransactions: 0,
        allowedDiscount: 0,
        actualDiscount: 0,
        excessDiscount: 0,
        bookingAmount: 0,
        priceOffered: 0,
        cars: {},
        variants: {},
      };
    }

    const item = map[showroomKey];
    const isDelivery = txn.stage === "delivery";

    item.totalTransactions += 1;
    item.bookings += isDelivery ? 0 : 1;
    item.deliveries += isDelivery ? 1 : 0;

    const allowed = isDelivery
      ? cleanNumber(txn.total_allowed_discount)
      : getAllowedDiscountBooking(txn);

    const actual = isDelivery
      ? cleanNumber(txn.total_actual_discount)
      : cleanNumber(txn.total_discount_booking);

    const excess = isDelivery
      ? cleanNumber(txn.total_excess_discount)
      : cleanNumber(txn.excess_booking);

    item.allowedDiscount += allowed;
    item.actualDiscount += actual;
    item.excessDiscount += excess;

    item.bookingAmount += cleanNumber(
      txn.booking_amt || txn.booking_amount || txn.bookingAmount,
    );

    item.priceOffered += cleanNumber(
      txn.price_offered ||
      txn.final_price ||
      txn.priceOffered ||
      txn.ex_showroom_price ||
      txn.ex_showroom_price_actual,
    );

    const carName = normaliseCarName(txn);

    const variant =
      txn.variant_name ||
      txn.full_variant_name ||
      txn.variant ||
      "Unknown Variant";

    item.cars[carName] = (item.cars[carName] || 0) + 1;
    item.variants[variant] = (item.variants[variant] || 0) + 1;
  });

  return Object.values(map).sort((a, b) => {
    if (b.totalTransactions !== a.totalTransactions) {
      return b.totalTransactions - a.totalTransactions;
    }

    return String(a.showroomName).localeCompare(String(b.showroomName));
  });
};

const extractRtoCode = (txn) => {
  const candidates = [
    txn.rto_code,
    txn.rtoCode,
    txn.rto_number,
    txn.rtoNumber,
    txn.rto_no,
    txn.rtoNo,
    txn.rto,
    txn.registration_rto,
    txn.registrationRto,
    txn.registration_no,
    txn.registrationNo,
    txn.registration_number,
    txn.registrationNumber,
    txn.vehicle_registration_number,
    txn.vehicleRegistrationNumber,
    txn.vehicle_reg_no,
    txn.vehicleRegNo,
    txn.reg_no,
    txn.regNo,
    txn.vehicle_no,
    txn.vehicleNo,
    txn.vehicle_number,
    txn.vehicleNumber,
    txn.customer_rto,
    txn.customerRto,
    txn.booking_rto,
    txn.bookingRto,
    txn.city_rto,
    txn.cityRto,
    txn.temp_registration_number,
    txn.tempRegistrationNumber,
    txn.permanent_registration_number,
    txn.permanentRegistrationNumber,
  ];

  for (const value of candidates) {
    const text = String(value || "")
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, "");
    const match = text.match(/UP(\d{2})/);

    if (match) return `UP${match[1]}`;
  }

  const fallbackText = Object.values(txn || {})
    .filter((value) => typeof value === "string" || typeof value === "number")
    .map((value) => String(value).toUpperCase())
    .join(" ")
    .replace(/[^A-Z0-9]/g, "");

  const fallbackMatch = fallbackText.match(/UP(\d{2})/);

  if (fallbackMatch) return `UP${fallbackMatch[1]}`;

  return "NOT_AVAILABLE";
};

const getRtoCity = (code) => {
  if (code === "UP32") return "Lucknow";
  if (code === "NOT_AVAILABLE") return "RTO Not Available";
  return RTO_CITY_MAP[code] || "Other City";
};

const buildRtoBookingAnalytics = (transactions) => {
  const rtoMap = {};

  transactions.forEach((txn) => {
    const rtoCode = extractRtoCode(txn);

    if (!rtoMap[rtoCode]) {
      rtoMap[rtoCode] = {
        rtoCode,
        city: getRtoCity(rtoCode),
        bookings: 0,
        totalAllowedDiscount: 0,
        totalActualDiscount: 0,
        totalExcessDiscount: 0,
        transactions: [],
      };
    }

    const isDelivery = txn.stage === "delivery";

    const allowed = isDelivery
      ? cleanNumber(txn.total_allowed_discount)
      : getAllowedDiscountBooking(txn);

    const actual = isDelivery
      ? cleanNumber(txn.total_actual_discount)
      : cleanNumber(txn.total_discount_booking);

    const excess = isDelivery
      ? cleanNumber(txn.total_excess_discount)
      : cleanNumber(txn.excess_booking);

    rtoMap[rtoCode].bookings += 1;
    rtoMap[rtoCode].totalAllowedDiscount += allowed;
    rtoMap[rtoCode].totalActualDiscount += actual;
    rtoMap[rtoCode].totalExcessDiscount += excess;
    rtoMap[rtoCode].transactions.push(txn);
  });

  const totalBookings = transactions.length;

  const rtoRows = Object.values(rtoMap)
    .map((row) => ({
      ...row,
      share: totalBookings
        ? Number(((cleanNumber(row.bookings) / totalBookings) * 100).toFixed(1))
        : 0,
    }))
    .sort((a, b) => {
      if (a.rtoCode === "UP32") return -1;
      if (b.rtoCode === "UP32") return 1;

      if (a.rtoCode === "NOT_AVAILABLE") return 1;
      if (b.rtoCode === "NOT_AVAILABLE") return -1;

      if (b.bookings !== a.bookings) return b.bookings - a.bookings;

      return String(a.rtoCode).localeCompare(String(b.rtoCode));
    });

  const lucknowRows = rtoRows.filter((row) => row.rtoCode === "UP32");

  const otherCityRows = rtoRows.filter(
    (row) => row.rtoCode !== "UP32" && row.rtoCode !== "NOT_AVAILABLE",
  );

  const notAvailableRows = rtoRows.filter(
    (row) => row.rtoCode === "NOT_AVAILABLE",
  );

  const lucknowBookings = lucknowRows.reduce(
    (sum, row) => sum + cleanNumber(row.bookings),
    0,
  );

  const otherCityBookings = otherCityRows.reduce(
    (sum, row) => sum + cleanNumber(row.bookings),
    0,
  );

  const notAvailableBookings = notAvailableRows.reduce(
    (sum, row) => sum + cleanNumber(row.bookings),
    0,
  );

  const getShare = (value) =>
    totalBookings
      ? Number(((cleanNumber(value) / totalBookings) * 100).toFixed(1))
      : 0;

  const summaryRows = [
    {
      key: "lucknow",
      label: "Lucknow Bookings",
      rtoDisplay: "UP32",
      bookings: lucknowBookings,
      share: getShare(lucknowBookings),
      rtoCount: lucknowRows.length,
      rows: lucknowRows,
    },
    {
      key: "other",
      label: "Other Cities Bookings",
      rtoDisplay: "Other Valid RTO Codes",
      bookings: otherCityBookings,
      share: getShare(otherCityBookings),
      rtoCount: otherCityRows.length,
      rows: otherCityRows,
    },
    {
      key: "not_available",
      label: "RTO Not Available",
      rtoDisplay: "Missing / Invalid RTO",
      bookings: notAvailableBookings,
      share: getShare(notAvailableBookings),
      rtoCount: notAvailableRows.length,
      rows: notAvailableRows,
    },
  ];

  return {
    totalBookings,
    rtoRows,
    summaryRows,
    lucknowRows,
    otherCityRows,
    notAvailableRows,
  };
};

const computeAnalytics = (transactions, stage) => {
  const data =
    stage === "delivery"
      ? transactions.filter((txn) => txn.stage === "delivery")
      : transactions;

  const getAllowed =
    stage === "delivery"
      ? (txn) => cleanNumber(txn.total_allowed_discount)
      : getAllowedDiscountBooking;

  const getActual =
    stage === "delivery"
      ? (txn) => cleanNumber(txn.total_actual_discount)
      : (txn) => cleanNumber(txn.total_discount_booking);

  const getExcess =
    stage === "delivery"
      ? (txn) => cleanNumber(txn.total_excess_discount)
      : (txn) => cleanNumber(txn.excess_booking);

  const totalEntries = data.length;
  const totalDiscount = data.reduce((sum, txn) => sum + getAllowed(txn), 0);
  const totalActualDiscount = data.reduce(
    (sum, txn) => sum + getActual(txn),
    0,
  );
  const totalExcess = data.reduce((sum, txn) => sum + getExcess(txn), 0);

  const excessCases = data.filter((txn) => getExcess(txn) > 0).length;
  const okCases = totalEntries - excessCases;

  const compliancePct = totalEntries
    ? Number(((okCases / totalEntries) * 100).toFixed(1))
    : 100;

  const avgDiscount = totalEntries
    ? Math.round(totalDiscount / totalEntries)
    : 0;
  const avgActualDiscount = totalEntries
    ? Math.round(totalActualDiscount / totalEntries)
    : 0;

  const monthMap = getMonthMap(data);
  const sortedMonths = Object.keys(monthMap).sort().reverse();

  const modelSales = {};
  const modelDiscount = {};
  const modelExcess = {};
  const variantExcess = {};
  const outletSales = {};
  const outletDiscount = {};
  const outletExcess = {};
  const conditionCount = {};

  data.forEach((txn) => {
    const model = normaliseCarName(txn);
    const outlet = txn.outlet_name || txn.outlet || "Unknown";
    const variant = txn.variant_name || txn.variant || "Unknown";

    const actual = getActual(txn);
    const excess = getExcess(txn);

    modelSales[model] = (modelSales[model] || 0) + 1;
    modelDiscount[model] = (modelDiscount[model] || 0) + actual;

    outletSales[outlet] = (outletSales[outlet] || 0) + 1;
    outletDiscount[outlet] = (outletDiscount[outlet] || 0) + actual;
    outletExcess[outlet] = (outletExcess[outlet] || 0) + excess;

    if (excess > 0) {
      modelExcess[model] = (modelExcess[model] || 0) + excess;
      variantExcess[variant] = (variantExcess[variant] || 0) + excess;
    }

    Object.entries(txn.conditions || {}).forEach(([key, value]) => {
      if (value) {
        const label = key
          .replace(/_/g, " ")
          .replace(/\b\w/g, (char) => char.toUpperCase());

        conditionCount[label] = (conditionCount[label] || 0) + 1;
      }
    });
  });

  return {
    data,
    totalEntries,
    totalDiscount,
    totalActualDiscount,
    totalExcess,
    excessCases,
    okCases,
    compliancePct,
    avgDiscount,
    avgActualDiscount,
    monthMap,
    sortedMonths,
    topModelSales: sortEntries(modelSales),
    topModelDiscount: sortEntries(modelDiscount),
    topModelExcess: sortEntries(modelExcess),
    topVariantExcess: sortEntries(variantExcess),
    outletSales: sortEntries(outletSales),
    outletDiscount: sortEntries(outletDiscount),
    outletExcess,
    outletSalesRaw: outletSales,
    outletDiscountRaw: outletDiscount,
    conditions: sortEntries(conditionCount),
    topExcessTransactions: data
      .filter((txn) => getExcess(txn) > 0)
      .sort((a, b) => getExcess(b) - getExcess(a))
      .slice(0, 8),
    getAllowed,
    getActual,
    getExcess,
  };
};

const CarImage = ({ car }) => {
  if (car?.image) {
    return (
      <img
        src={car.image}
        alt={car.carName}
        className="h-28 w-full scale-125 object-contain transition duration-300 group-hover:scale-150"
        onError={(e) => {
          e.currentTarget.style.display = "none";
        }}
      />
    );
  }

  return (
    <div className="flex h-28 w-full items-center justify-center rounded-2xl bg-gradient-to-br from-slate-100 to-white text-5xl dark:from-slate-900 dark:to-slate-950">
      🚘
    </div>
  );
};

const CarComparisonModal = ({
  open,
  onClose,
  cars,
  showrooms = [],
  transactions = [],
}) => {
  const [selectedCompareShowroomKey, setSelectedCompareShowroomKey] =
    useState("");
  const [expandedCarName, setExpandedCarName] = useState("");
  const [trendOpen, setTrendOpen] = useState(false);
  const [trendMonths, setTrendMonths] = useState(3);

  if (!open) return null;

  const getTxnShowroomKey = (txn) => {
    const outletId =
      txn.outlet_id ||
      txn.outletId ||
      txn.showroom_id ||
      txn.showroomId ||
      null;

    if (outletId) return `outlet-${outletId}`;

    const outletName =
      txn.outlet_name ||
      txn.showroom_name ||
      txn.outlet ||
      txn.showroom ||
      "Unknown Showroom";

    return `name-${normalizeNameKey(outletName)}`;
  };

  const selectedCompareShowroom = selectedCompareShowroomKey
    ? showrooms.find(
      (showroom) =>
        String(showroom.key) === String(selectedCompareShowroomKey),
    )
    : null;

  const selectedShowroomNameKey = normalizeNameKey(
    selectedCompareShowroom?.showroomName || "",
  );

  const comparisonTransactions = selectedCompareShowroomKey
    ? transactions.filter((txn) => {
      const txnShowroomKey = getTxnShowroomKey(txn);

      if (String(txnShowroomKey) === String(selectedCompareShowroomKey)) {
        return true;
      }

      const txnShowroomName =
        txn.outlet_name ||
        txn.showroom_name ||
        txn.outlet ||
        txn.showroom ||
        "";

      return (
        selectedShowroomNameKey &&
        normalizeNameKey(txnShowroomName) === selectedShowroomNameKey
      );
    })
    : transactions;

  const modalCars = selectedCompareShowroomKey
    ? buildCarWiseAnalytics(comparisonTransactions)
    : cars;

  const activeCars = modalCars.filter(
    (car) => cleanNumber(car.totalTransactions) > 0,
  );

  const comparisonCars = activeCars.length ? activeCars : modalCars;

  const getCarColor = (carName) => {
    const index = comparisonCars.findIndex(
      (car) => String(car.carName) === String(carName),
    );

    return PIE_COLORS[(index === -1 ? 0 : index) % PIE_COLORS.length];
  };

  const getTxnDate = (txn) => {
    const rawDate =
      txn.booking_date ||
      txn.delivery_date ||
      txn.invoice_date ||
      txn.created_at ||
      txn.createdAt ||
      "";

    if (!rawDate) return null;

    const date = new Date(rawDate);

    return Number.isNaN(date.getTime()) ? null : date;
  };

  const getMonthKeyFromDate = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");

    return `${year}-${month}`;
  };

  const addMonths = (date, months) => {
    const next = new Date(date);
    next.setMonth(next.getMonth() + months);

    return next;
  };

  const getMonthStart = (date) => {
    return new Date(date.getFullYear(), date.getMonth(), 1);
  };

  const getLatestTransactionDate = () => {
    const datedTransactions = comparisonTransactions
      .map((txn) => getTxnDate(txn))
      .filter(Boolean)
      .sort((a, b) => b.getTime() - a.getTime());

    return datedTransactions[0] || new Date();
  };

  const getPeriodTransactions = (startDate, endDate) => {
    return comparisonTransactions.filter((txn) => {
      const date = getTxnDate(txn);

      return date && date >= startDate && date < endDate;
    });
  };

  const getTxnExcess = (txn) => {
    const isDelivery = txn.stage === "delivery";

    return isDelivery
      ? cleanNumber(txn.total_excess_discount)
      : cleanNumber(txn.excess_booking);
  };

  const getTxnAllowed = (txn) => {
    const isDelivery = txn.stage === "delivery";

    return isDelivery
      ? cleanNumber(txn.total_allowed_discount)
      : getAllowedDiscountBooking(txn);
  };

  const getTxnActual = (txn) => {
    const isDelivery = txn.stage === "delivery";

    return isDelivery
      ? cleanNumber(txn.total_actual_discount)
      : cleanNumber(txn.total_discount_booking);
  };

  const getTrendStats = (txns) => {
    return {
      bookings: txns.filter((txn) => txn.stage !== "delivery").length,
      deliveries: txns.filter((txn) => txn.stage === "delivery").length,
      totalUnits: txns.length,
      allowedDiscount: txns.reduce((sum, txn) => sum + getTxnAllowed(txn), 0),
      actualDiscount: txns.reduce((sum, txn) => sum + getTxnActual(txn), 0),
      excessDiscount: txns.reduce((sum, txn) => sum + getTxnExcess(txn), 0),
    };
  };

  const getTrendPayload = () => {
    const latestDate = getLatestTransactionDate();
    const currentEnd = addMonths(getMonthStart(latestDate), 1);
    const currentStart = addMonths(currentEnd, -trendMonths);
    const previousEnd = currentStart;
    const previousStart = addMonths(previousEnd, -trendMonths);

    const oldTransactions = getPeriodTransactions(previousStart, previousEnd);
    const newTransactions = getPeriodTransactions(currentStart, currentEnd);

    const oldStats = getTrendStats(oldTransactions);
    const newStats = getTrendStats(newTransactions);

    const monthlyMap = {};

    newTransactions.forEach((txn) => {
      const date = getTxnDate(txn);
      if (!date) return;

      const monthKey = getMonthKeyFromDate(date);
      const carName = normaliseCarName(txn);
      const excess = getTxnExcess(txn);

      if (!monthlyMap[monthKey]) {
        monthlyMap[monthKey] = {
          monthKey,
          totalExcess: 0,
          cars: {},
        };
      }

      monthlyMap[monthKey].totalExcess += excess;
      monthlyMap[monthKey].cars[carName] =
        (monthlyMap[monthKey].cars[carName] || 0) + excess;
    });

    const monthRows = [];

    for (let i = trendMonths - 1; i >= 0; i -= 1) {
      const date = addMonths(currentEnd, -1 - i);
      const monthKey = getMonthKeyFromDate(date);

      monthRows.push(
        monthlyMap[monthKey] || {
          monthKey,
          totalExcess: 0,
          cars: {},
        },
      );
    }

    return {
      oldTransactions,
      newTransactions,
      oldStats,
      newStats,
      monthRows,
      currentStart,
      currentEnd,
      previousStart,
      previousEnd,
    };
  };

  const formatDate = (date) => {
    return date.toLocaleDateString("en-IN", {
      month: "short",
      year: "numeric",
    });
  };

  const totalBookings = comparisonCars.reduce(
    (sum, car) => sum + cleanNumber(car.bookings),
    0,
  );

  const totalDeliveries = comparisonCars.reduce(
    (sum, car) => sum + cleanNumber(car.deliveries),
    0,
  );

  const totalExcess = comparisonCars.reduce(
    (sum, car) => sum + cleanNumber(car.excessDiscount),
    0,
  );

  const maxDiscount = Math.max(
    ...comparisonCars.map((car) => cleanNumber(car.excessDiscount)),
    1,
  );

  const buildVariantBreakdownForCar = (targetCarName) => {
    const variantMap = {};

    comparisonTransactions
      .filter((txn) => normaliseCarName(txn) === targetCarName)
      .forEach((txn) => {
        const variantName =
          txn.variant_name ||
          txn.full_variant_name ||
          txn.variant ||
          "Unknown Variant";

        if (!variantMap[variantName]) {
          variantMap[variantName] = {
            variantName,
            bookings: 0,
            deliveries: 0,
            totalUnits: 0,
            allowedDiscount: 0,
            actualDiscount: 0,
            excessDiscount: 0,
          };
        }

        const isDelivery = txn.stage === "delivery";

        const allowed = isDelivery
          ? cleanNumber(txn.total_allowed_discount)
          : getAllowedDiscountBooking(txn);

        const actual = isDelivery
          ? cleanNumber(txn.total_actual_discount)
          : cleanNumber(txn.total_discount_booking);

        const excess = isDelivery
          ? cleanNumber(txn.total_excess_discount)
          : cleanNumber(txn.excess_booking);

        variantMap[variantName].bookings += isDelivery ? 0 : 1;
        variantMap[variantName].deliveries += isDelivery ? 1 : 0;
        variantMap[variantName].totalUnits += 1;
        variantMap[variantName].allowedDiscount += allowed;
        variantMap[variantName].actualDiscount += actual;
        variantMap[variantName].excessDiscount += excess;
      });

    return Object.values(variantMap)
      .map((row) => ({
        ...row,
        excessRate: row.actualDiscount
          ? Number(
            (
              (cleanNumber(row.excessDiscount) /
                cleanNumber(row.actualDiscount)) *
              100
            ).toFixed(1),
          )
          : 0,
      }))
      .sort((a, b) => b.totalUnits - a.totalUnits);
  };

  const buildPieSegments = (items) => {
    const filteredItems = items.filter((item) => cleanNumber(item.value) > 0);

    const total = filteredItems.reduce(
      (sum, item) => sum + cleanNumber(item.value),
      0,
    );

    let cumulative = 0;

    const segments = filteredItems.map((item, index) => {
      const value = cleanNumber(item.value);
      const percentage = total ? value / total : 0;
      const dash = `${percentage * 100} ${100 - percentage * 100}`;
      const offset = -cumulative * 100;

      cumulative += percentage;

      return {
        ...item,
        color: item.color || PIE_COLORS[index % PIE_COLORS.length],
        dash,
        offset,
        percentage,
      };
    });

    return {
      total,
      segments,
    };
  };

  const bookingPie = buildPieSegments(
    comparisonCars.map((car) => ({
      label: car.carName,
      value: cleanNumber(car.bookings),
      color: getCarColor(car.carName),
    })),
  );

  const deliveryPie = buildPieSegments(
    comparisonCars.map((car) => ({
      label: car.carName,
      value: cleanNumber(car.deliveries),
      color: getCarColor(car.carName),
    })),
  );

  const PieShareCard = ({ title, subtitle, pie }) => {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
        <div className="mb-5">
          <h3 className="text-sm font-black text-slate-900 dark:text-white">
            {title}
          </h3>

          <p className="mt-1 text-xs font-semibold text-slate-400">
            {subtitle}
          </p>
        </div>

        <div className="grid items-center gap-5 md:grid-cols-[180px_1fr] xl:grid-cols-1 2xl:grid-cols-[180px_1fr]">
          <div className="relative mx-auto h-[180px] w-[180px]">
            <svg viewBox="0 0 36 36" className="h-full w-full -rotate-90">
              <circle
                cx="18"
                cy="18"
                r="15.9155"
                fill="transparent"
                stroke="currentColor"
                strokeWidth="3.8"
                className="text-slate-100 dark:text-slate-800"
              />

              {pie.segments.map((segment) => (
                <circle
                  key={segment.label}
                  cx="18"
                  cy="18"
                  r="15.9155"
                  fill="transparent"
                  stroke={segment.color}
                  strokeWidth="3.8"
                  strokeDasharray={segment.dash}
                  strokeDashoffset={segment.offset}
                  strokeLinecap="round"
                  className="cursor-pointer transition-opacity hover:opacity-80"
                >
                  <title>
                    {`${segment.label} — ${cleanNumber(
                      segment.value,
                    ).toLocaleString(
                      "en-IN",
                    )} (${(segment.percentage * 100).toFixed(1)}%)`}
                  </title>
                </circle>
              ))}
            </svg>

            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
              <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                Total
              </p>

              <p className="mt-1 text-xl font-black text-slate-950 dark:text-white">
                {pie.total.toLocaleString("en-IN")}
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {pie.segments.length ? (
              pie.segments.map((item) => (
                <div
                  key={item.label}
                  title={`${item.label} — ${cleanNumber(
                    item.value,
                  ).toLocaleString(
                    "en-IN",
                  )} (${(item.percentage * 100).toFixed(1)}%)`}
                  className="flex cursor-help items-center justify-between gap-3 rounded-xl px-2 py-1 transition hover:bg-slate-50 dark:hover:bg-slate-900"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <span
                      className="h-3 w-3 shrink-0 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />

                    <p className="truncate text-xs font-bold text-slate-600 dark:text-slate-300">
                      {item.label}
                    </p>
                  </div>

                  <p className="whitespace-nowrap text-xs font-black text-slate-900 dark:text-white">
                    {cleanNumber(item.value).toLocaleString("en-IN")}{" "}
                    <span className="font-semibold text-slate-400">
                      ({(item.percentage * 100).toFixed(1)}%)
                    </span>
                  </p>
                </div>
              ))
            ) : (
              <div className="rounded-2xl bg-slate-50 p-6 text-center text-sm font-semibold text-slate-400 dark:bg-slate-900">
                No data available
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const TrendMetricCard = ({ title, oldValue, newValue, money = false }) => {
    const oldNumber = cleanNumber(oldValue);
    const newNumber = cleanNumber(newValue);
    const diff = newNumber - oldNumber;
    const isIncrease = diff > 0;
    const isDecrease = diff < 0;
    const arrow = isIncrease ? "↑" : isDecrease ? "↓" : "→";
    const toneClass = isIncrease
      ? "text-emerald-400"
      : isDecrease
        ? "text-red-400"
        : "text-slate-400";

    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
        <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">
          {title}
        </p>

        <div className="mt-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">
              Old Value
            </p>
            <p className="mt-1 text-2xl font-black text-slate-800 dark:text-slate-200">
              {money
                ? formatMoney(oldNumber)
                : oldNumber.toLocaleString("en-IN")}
            </p>
          </div>

          <div className={`text-3xl font-black ${toneClass}`}>{arrow}</div>

          <div className="text-right">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">
              New Value
            </p>
            <p className={`mt-1 text-2xl font-black ${toneClass}`}>
              {money
                ? formatMoney(newNumber)
                : newNumber.toLocaleString("en-IN")}
            </p>
          </div>
        </div>

        <p className={`mt-3 text-xs font-black ${toneClass}`}>
          {diff === 0
            ? "No change"
            : `${isIncrease ? "+" : ""}${money ? formatMoney(diff) : diff.toLocaleString("en-IN")}`}
        </p>
      </div>
    );
  };

  const TrendModal = () => {
    if (!trendOpen) return null;

    const trend = getTrendPayload();
    const maxMonthlyExcess = Math.max(
      ...trend.monthRows.map((row) => cleanNumber(row.totalExcess)),
      1,
    );

    return (
      <div className="fixed inset-0 z-[110] flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-md">
        <div className="max-h-[92vh] w-full max-w-6xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-950">
          <div className="flex flex-col gap-4 border-b border-slate-200 bg-gradient-to-r from-amber-50 via-white to-indigo-50 p-5 dark:border-slate-800 dark:from-slate-900 dark:via-slate-950 dark:to-slate-900 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.25em] text-slate-500 dark:text-slate-400">
                Trends
              </p>

              <h2 className="mt-1 text-2xl font-black text-slate-950 dark:text-white">
                Car Trend Analysis
              </h2>

              <p className="mt-1 text-sm font-semibold text-slate-500 dark:text-slate-400">
                Previous {trendMonths} months vs latest {trendMonths} months.
              </p>

              <p className="mt-2 text-xs font-bold text-slate-400">
                Old: {formatDate(trend.previousStart)} to{" "}
                {formatDate(addMonths(trend.previousEnd, -1))} · New:{" "}
                {formatDate(trend.currentStart)} to{" "}
                {formatDate(addMonths(trend.currentEnd, -1))}
              </p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="min-w-[220px]">
                <p className="mb-1 text-[10px] font-black uppercase tracking-widest text-slate-400">
                  Time Range
                </p>

                <select
                  value={trendMonths}
                  onChange={(e) => setTrendMonths(Number(e.target.value))}
                  className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-black text-slate-800 outline-none transition focus:border-amber-400 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                >
                  <option value={3}>Last 3 Months</option>
                  <option value={6}>Last 6 Months</option>
                  <option value={9}>Last 9 Months</option>
                  <option value={12}>Last 12 Months</option>
                </select>
              </div>

              <button
                type="button"
                onClick={() => setTrendOpen(false)}
                className="rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-black text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                Close
              </button>
            </div>
          </div>

          <div className="max-h-[calc(92vh-128px)] overflow-y-auto p-5">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <TrendMetricCard
                title="Total Bookings"
                oldValue={trend.oldStats.bookings}
                newValue={trend.newStats.bookings}
              />

              <TrendMetricCard
                title="Total Deliveries"
                oldValue={trend.oldStats.deliveries}
                newValue={trend.newStats.deliveries}
              />

              <TrendMetricCard
                title="Total Units"
                oldValue={trend.oldStats.totalUnits}
                newValue={trend.newStats.totalUnits}
              />

              <TrendMetricCard
                title="Allowed Discount"
                oldValue={trend.oldStats.allowedDiscount}
                newValue={trend.newStats.allowedDiscount}
                money
              />

              <TrendMetricCard
                title="Actual Discount"
                oldValue={trend.oldStats.actualDiscount}
                newValue={trend.newStats.actualDiscount}
                money
              />

              <TrendMetricCard
                title="Excess Discount"
                oldValue={trend.oldStats.excessDiscount}
                newValue={trend.newStats.excessDiscount}
                money
              />
            </div>

            <div className="mt-5 rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <div className="mb-5">
                <h3 className="text-sm font-black text-slate-900 dark:text-white">
                  Month-wise Excess Discount Histogram
                </h3>

                <p className="mt-1 text-xs font-semibold text-slate-400">
                  Latest selected period split into monthly excess discount
                  bars.
                </p>
              </div>

              <div className="space-y-5">
                {trend.monthRows.map((row) => {
                  const pct =
                    (cleanNumber(row.totalExcess) / maxMonthlyExcess) * 100;
                  const carEntries = Object.entries(row.cars || {}).sort(
                    (a, b) => cleanNumber(b[1]) - cleanNumber(a[1]),
                  );

                  return (
                    <div
                      key={row.monthKey}
                      className="rounded-2xl px-2 py-2 transition hover:bg-slate-50 dark:hover:bg-slate-900"
                    >
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <p className="text-sm font-black text-slate-800 dark:text-slate-100">
                          {monthLabel(row.monthKey)}
                        </p>

                        <p className="whitespace-nowrap text-sm font-black text-red-600 dark:text-red-300">
                          {formatMoney(row.totalExcess)}
                        </p>
                      </div>

                      <div className="h-4 overflow-hidden rounded-full bg-slate-100 shadow-inner dark:bg-slate-800">
                        <div
                          className="h-full rounded-full bg-red-500 transition-all duration-500"
                          style={{ width: `${pct}%` }}
                        />
                      </div>

                      {carEntries.length ? (
                        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                          {carEntries.map(([carName, value]) => (
                            <div
                              key={`${row.monthKey}-${carName}`}
                              className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-900"
                            >
                              <div className="flex min-w-0 items-center gap-2">
                                <span
                                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                                  style={{
                                    backgroundColor: getCarColor(carName),
                                  }}
                                />
                                <p className="truncate text-xs font-bold text-slate-600 dark:text-slate-300">
                                  {carName}
                                </p>
                              </div>

                              <p
                                className="whitespace-nowrap text-xs font-black"
                                style={{ color: getCarColor(carName) }}
                              >
                                {formatMoney(value)}
                              </p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-2 text-xs font-semibold text-slate-400">
                          No excess discount in this month.
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const tableRows = comparisonCars
    .map((car) => {
      const units = cleanNumber(car.bookings) + cleanNumber(car.deliveries);

      const excessRate = car.actualDiscount
        ? Number(
          (
            (cleanNumber(car.excessDiscount) /
              cleanNumber(car.actualDiscount)) *
            100
          ).toFixed(1),
        )
        : 0;

      return {
        ...car,
        units,
        excessRate,
        variantRows: buildVariantBreakdownForCar(car.carName),
      };
    })
    .sort((a, b) => b.units - a.units);

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/75 p-4 backdrop-blur-md">
      <TrendModal />

      <div className="max-h-[92vh] w-full max-w-7xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-950">
        <div className="flex flex-col gap-4 border-b border-slate-200 bg-gradient-to-r from-amber-50 via-white to-indigo-50 p-5 dark:border-slate-800 dark:from-slate-900 dark:via-slate-950 dark:to-slate-900 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <p className="text-[11px] font-black uppercase tracking-[0.25em] text-slate-500 dark:text-slate-400">
              Car Comparison
            </p>

            <h2 className="mt-1 text-2xl font-black text-slate-950 dark:text-white">
              Model-wise Performance Dashboard
            </h2>

            <p className="mt-1 text-sm font-semibold text-slate-500 dark:text-slate-400">
              Compare bookings, deliveries, discounts, excess discount and model
              share.
            </p>

            {selectedCompareShowroom ? (
              <p className="mt-2 inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-black text-amber-800 dark:bg-amber-400/10 dark:text-amber-300">
                Showing: {selectedCompareShowroom.showroomName}
              </p>
            ) : null}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              type="button"
              onClick={() => setTrendOpen(true)}
              className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-2 text-xs font-black uppercase tracking-wide text-white shadow-lg transition hover:-translate-y-0.5 hover:border-amber-400 hover:text-amber-300 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            >
              See Trends
            </button>

            <div className="min-w-[260px]">
              <p className="mb-1 text-[10px] font-black uppercase tracking-widest text-slate-400">
                Filter Showroom
              </p>

              <select
                value={selectedCompareShowroomKey}
                onChange={(e) => {
                  setSelectedCompareShowroomKey(e.target.value);
                  setExpandedCarName("");
                }}
                className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-black text-slate-800 outline-none transition focus:border-amber-400 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              >
                <option value="">All Showrooms</option>

                {showrooms.map((showroom) => (
                  <option key={showroom.key} value={showroom.key}>
                    {showroom.showroomName}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-black text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Close
            </button>
          </div>
        </div>

        <div className="max-h-[calc(92vh-110px)] overflow-y-auto p-5">
          <div className="mb-5 grid gap-4 md:grid-cols-3">
            <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">
                Total Bookings
              </p>

              <p className="mt-3 text-3xl font-black text-indigo-600 dark:text-indigo-300">
                {totalBookings.toLocaleString("en-IN")}
              </p>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">
                Total Deliveries
              </p>

              <p className="mt-3 text-3xl font-black text-emerald-600 dark:text-emerald-300">
                {totalDeliveries.toLocaleString("en-IN")}
              </p>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">
                Total Excess Discount
              </p>

              <p className="mt-3 text-3xl font-black text-red-600 dark:text-red-300">
                {formatMoney(totalExcess)}
              </p>
            </div>
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <PieShareCard
              title="Pie Chart: Booking Model Share"
              subtitle="Share based on total bookings only"
              pie={bookingPie}
            />

            <PieShareCard
              title="Pie Chart: Delivery Model Share"
              subtitle="Share based on total deliveries only"
              pie={deliveryPie}
            />
          </div>

          <div className="mt-5 rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
            <div className="mb-5">
              <h3 className="text-sm font-black text-slate-900 dark:text-white">
                Excess Discount Histogram
              </h3>

              <p className="mt-1 text-xs font-semibold text-slate-400">
                Model-wise excess discount exposure
              </p>
            </div>

            <div className="space-y-4">
              {comparisonCars.map((car) => {
                const pct =
                  (cleanNumber(car.excessDiscount) / maxDiscount) * 100;

                const carColor = getCarColor(car.carName);

                return (
                  <div
                    key={car.carName}
                    title={`${car.carName} — ${formatMoney(car.excessDiscount)}`}
                    className="cursor-help rounded-xl px-2 py-1 transition hover:bg-slate-50 dark:hover:bg-slate-900"
                  >
                    <div className="mb-1.5 flex items-center justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-2">
                        <span
                          className="h-3 w-3 shrink-0 rounded-full"
                          style={{ backgroundColor: carColor }}
                        />

                        <p className="truncate text-sm font-bold text-slate-700 dark:text-slate-200">
                          {car.carName}
                        </p>
                      </div>

                      <p
                        className="whitespace-nowrap text-sm font-black"
                        style={{ color: carColor }}
                      >
                        {formatMoney(car.excessDiscount)}
                      </p>
                    </div>

                    <div className="h-3 overflow-hidden rounded-full bg-slate-100 shadow-inner dark:bg-slate-800">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: carColor,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-5 overflow-hidden rounded-3xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
            <div className="border-b border-slate-100 p-5 dark:border-slate-800">
              <h3 className="text-sm font-black text-slate-900 dark:text-white">
                Model-wise Comparison Table
              </h3>

              <p className="mt-1 text-xs font-semibold text-slate-400">
                Complete model-level audit summary
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[980px] text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
                    {[
                      "Car",
                      "Bookings",
                      "Deliveries",
                      "Total Units",
                      "Allowed Discount",
                      "Actual Discount",
                      "Excess Discount",
                      "Excess Rate",
                    ].map((heading) => (
                      <th
                        key={heading}
                        className="px-4 py-3 text-left text-[10px] font-black uppercase tracking-widest text-slate-400"
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {tableRows.length ? (
                    tableRows.flatMap((car) => {
                      const carColor = getCarColor(car.carName);
                      const isExpanded = expandedCarName === car.carName;

                      const mainRow = (
                        <tr
                          key={car.carName}
                          onClick={() =>
                            setExpandedCarName((current) =>
                              current === car.carName ? "" : car.carName,
                            )
                          }
                          className="cursor-pointer border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900"
                          title="Click to view variant-wise breakdown"
                        >
                          <td className="px-4 py-3 font-black text-slate-900 dark:text-white">
                            <div className="flex items-center gap-2">
                              <span
                                className="h-3 w-3 shrink-0 rounded-full"
                                style={{ backgroundColor: carColor }}
                              />

                              <span>{car.carName}</span>

                              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-black text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                                {isExpanded ? "Hide variants" : "View variants"}
                              </span>
                            </div>
                          </td>

                          <td className="px-4 py-3 font-bold text-indigo-600 dark:text-indigo-300">
                            {car.bookings}
                          </td>

                          <td className="px-4 py-3 font-bold text-emerald-600 dark:text-emerald-300">
                            {car.deliveries}
                          </td>

                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                            {car.units}
                          </td>

                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                            {formatMoney(car.allowedDiscount)}
                          </td>

                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                            {formatMoney(car.actualDiscount)}
                          </td>

                          <td
                            className="px-4 py-3 font-black"
                            style={{ color: carColor }}
                          >
                            {formatMoney(car.excessDiscount)}
                          </td>

                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                            {car.excessRate}%
                          </td>
                        </tr>
                      );

                      if (!isExpanded) return [mainRow];

                      const variantRow = (
                        <tr key={`${car.carName}-variants`}>
                          <td
                            colSpan={8}
                            className="border-b border-slate-100 bg-slate-50/70 p-0 dark:border-slate-800 dark:bg-slate-900/40"
                          >
                            <div className="mx-4 my-4 ml-8 overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
                              <div className="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
                                <p className="text-xs font-black uppercase tracking-widest text-slate-400">
                                  Variant-wise breakdown — {car.carName}
                                </p>
                              </div>

                              <div className="overflow-x-auto">
                                <table className="w-full min-w-[900px] text-sm">
                                  <thead>
                                    <tr className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
                                      {[
                                        "Variant",
                                        "Bookings",
                                        "Deliveries",
                                        "Total Units",
                                        "Allowed Discount",
                                        "Actual Discount",
                                        "Excess Discount",
                                        "Excess Rate",
                                      ].map((heading) => (
                                        <th
                                          key={heading}
                                          className="px-4 py-3 text-left text-[10px] font-black uppercase tracking-widest text-slate-400"
                                        >
                                          {heading}
                                        </th>
                                      ))}
                                    </tr>
                                  </thead>

                                  <tbody>
                                    {car.variantRows.length ? (
                                      car.variantRows.map((variant) => (
                                        <tr
                                          key={`${car.carName}-${variant.variantName}`}
                                          className="border-b border-slate-100 last:border-b-0 dark:border-slate-800"
                                        >
                                          <td className="px-4 py-3 font-bold text-slate-800 dark:text-slate-100">
                                            <span className="mr-2 text-slate-400">
                                              ↳
                                            </span>
                                            {variant.variantName}
                                          </td>

                                          <td className="px-4 py-3 font-bold text-indigo-600 dark:text-indigo-300">
                                            {variant.bookings}
                                          </td>

                                          <td className="px-4 py-3 font-bold text-emerald-600 dark:text-emerald-300">
                                            {variant.deliveries}
                                          </td>

                                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                                            {variant.totalUnits}
                                          </td>

                                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                                            {formatMoney(
                                              variant.allowedDiscount,
                                            )}
                                          </td>

                                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                                            {formatMoney(
                                              variant.actualDiscount,
                                            )}
                                          </td>

                                          <td
                                            className="px-4 py-3 font-black"
                                            style={{ color: carColor }}
                                          >
                                            {formatMoney(
                                              variant.excessDiscount,
                                            )}
                                          </td>

                                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                                            {variant.excessRate}%
                                          </td>
                                        </tr>
                                      ))
                                    ) : (
                                      <tr>
                                        <td
                                          colSpan={8}
                                          className="px-4 py-6 text-center text-sm font-semibold text-slate-400"
                                        >
                                          No variant-wise data available for
                                          this car.
                                        </td>
                                      </tr>
                                    )}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          </td>
                        </tr>
                      );

                      return [mainRow, variantRow];
                    })
                  ) : (
                    <tr>
                      <td
                        colSpan={8}
                        className="px-4 py-10 text-center text-sm font-semibold text-slate-400"
                      >
                        No car comparison data available.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const CarCarousel = ({
  cars,
  selectedCarName,
  onSelect,
  onCompare,
  sortBy,
  onSortChange,
}) => {
  if (!cars.length) return null;

  return (
    <section className="mb-5">
      <div className="mb-3 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="mt-1 text-xl font-black text-slate-950 dark:text-white">
            Car-Wise Analysis
          </h2>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="min-w-[240px]">
            <select
              value={sortBy}
              onChange={(e) => onSortChange(e.target.value)}
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-2 text-xs font-black uppercase tracking-wide text-white outline-none transition focus:border-amber-400 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            >
              <option value="default">Default Order</option>
              <option value="alphabetical">Alphabetical</option>
              <option value="bookings_high">Bookings: High to Low</option>
              <option value="bookings_low">Bookings: Low to High</option>
              <option value="deliveries_high">Deliveries: High to Low</option>
              <option value="deliveries_low">Deliveries: Low to High</option>
              <option value="excess_high">Excess Discount: High to Low</option>
              <option value="excess_low">Excess Discount: Low to High</option>
            </select>
          </div>

          <button
            type="button"
            onClick={onCompare}
            className="rounded-2xl border border-amber-300 bg-amber-400 px-4 py-2 text-xs font-black uppercase tracking-wide text-slate-950 shadow-lg transition hover:-translate-y-0.5 hover:bg-amber-300 dark:border-amber-400/30 dark:bg-amber-400 dark:text-slate-950"
          >
            Compare All Cars Together
          </button>
        </div>
      </div>

      <div className="flex gap-5 overflow-x-auto pb-4">
        {cars.map((car) => {
          const active = selectedCarName === car.carName;

          return (
            <button
              key={car.carName}
              type="button"
              onClick={() => onSelect(car.carName)}
              className={`group min-w-[190px] rounded-3xl border px-4 py-3 text-center transition-all duration-300 hover:-translate-y-1 hover:shadow-xl ${active
                  ? "border-amber-400 bg-amber-50 shadow-lg ring-2 ring-amber-200 dark:border-amber-400 dark:bg-amber-400/10 dark:ring-amber-400/20"
                  : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-800 dark:bg-slate-950 dark:hover:border-slate-700"
                }`}
            >
              <div className="mb-1 flex h-28 items-center justify-center overflow-hidden rounded-2xl bg-slate-50 p-1 dark:bg-slate-900">
                <CarImage car={car} />
              </div>

              <p className="line-clamp-1 min-h-[24px] text-base font-black leading-tight text-slate-900 dark:text-white">
                {car.carName}
              </p>

              <div className="mt-2 flex justify-center gap-2">
                <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-black text-indigo-700 dark:bg-indigo-400/10 dark:text-indigo-300">
                  B-: {car.bookings}
                </span>

                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300">
                  D-: {car.deliveries}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
};
const ShowroomComparisonModal = ({
  open,
  onClose,
  showrooms,
  transactions = [],
}) => {
  const [trendOpen, setTrendOpen] = useState(false);
  const [trendMonths, setTrendMonths] = useState(3);
  const [expandedShowroomKey, setExpandedShowroomKey] = useState("");

  if (!open) return null;

  const activeShowrooms = showrooms.filter(
    (showroom) => cleanNumber(showroom.totalTransactions) > 0,
  );

  const comparisonShowrooms = activeShowrooms.length
    ? activeShowrooms
    : showrooms;

  const getShowroomColor = (showroomKey) => {
    const index = comparisonShowrooms.findIndex(
      (showroom) => String(showroom.key || showroom.id) === String(showroomKey),
    );

    return PIE_COLORS[(index === -1 ? 0 : index) % PIE_COLORS.length];
  };

  const getTxnShowroomKey = (txn) => {
    const outletId =
      txn.outlet_id ||
      txn.outletId ||
      txn.showroom_id ||
      txn.showroomId ||
      null;

    if (outletId) return `outlet-${outletId}`;

    const outletName =
      txn.outlet_name ||
      txn.showroom_name ||
      txn.outlet ||
      txn.showroom ||
      "Unknown Showroom";

    return `name-${normalizeNameKey(outletName)}`;
  };

  const getTxnShowroomName = (txn) => {
    return (
      txn.outlet_name ||
      txn.showroom_name ||
      txn.outlet ||
      txn.showroom ||
      "Unknown Showroom"
    );
  };

  const getTxnTeamLeaderName = (txn) => {
    return (
      txn.team_leader_name ||
      txn.teamLeaderName ||
      txn.team_leader ||
      txn.teamLeader ||
      txn.tl_name ||
      txn.tlName ||
      txn.sales_team_leader ||
      txn.salesTeamLeader ||
      txn.reporting_manager ||
      txn.reportingManager ||
      txn.manager_name ||
      txn.managerName ||
      txn.executive_team_leader ||
      txn.executiveTeamLeader ||
      txn.executive_name ||
      txn.executiveName ||
      txn.sales_executive ||
      txn.salesExecutive ||
      txn.employee_name ||
      txn.employeeName ||
      "Unknown Team Leader"
    );
  };

  const getTxnAllowedDiscount = (txn) => {
    const isDelivery = txn.stage === "delivery";

    return isDelivery
      ? cleanNumber(txn.total_allowed_discount)
      : getAllowedDiscountBooking(txn);
  };

  const getTxnActualDiscount = (txn) => {
    const isDelivery = txn.stage === "delivery";

    return isDelivery
      ? cleanNumber(txn.total_actual_discount)
      : cleanNumber(txn.total_discount_booking);
  };

  const getTxnExcessDiscount = (txn) => {
    const isDelivery = txn.stage === "delivery";

    return isDelivery
      ? cleanNumber(txn.total_excess_discount)
      : cleanNumber(txn.excess_booking);
  };

  const getTxnMonth = (txn) => {
    const candidates = [
      txn.booking_date,
      txn.bookingDate,
      txn.delivery_date,
      txn.deliveryDate,
      txn.invoice_date,
      txn.invoiceDate,
      txn.date,
      txn.transaction_date,
      txn.transactionDate,
      txn.created_at,
      txn.createdAt,
      txn.updated_at,
      txn.updatedAt,
    ];

    for (const value of candidates) {
      if (!value) continue;

      const text = String(value).trim();

      const isoMatch = text.match(/^(\d{4})-(\d{2})/);
      if (isoMatch) {
        return `${isoMatch[1]}-${isoMatch[2]}`;
      }

      const indianMatch = text.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/);
      if (indianMatch) {
        const month = String(indianMatch[2]).padStart(2, "0");
        return `${indianMatch[3]}-${month}`;
      }

      const parsedDate = new Date(text);
      if (!Number.isNaN(parsedDate.getTime())) {
        const year = parsedDate.getFullYear();
        const month = String(parsedDate.getMonth() + 1).padStart(2, "0");
        return `${year}-${month}`;
      }
    }

    return "";
  };

  const totalBookings = comparisonShowrooms.reduce(
    (sum, showroom) => sum + cleanNumber(showroom.bookings),
    0,
  );

  const totalDeliveries = comparisonShowrooms.reduce(
    (sum, showroom) => sum + cleanNumber(showroom.deliveries),
    0,
  );

  const totalExcess = comparisonShowrooms.reduce(
    (sum, showroom) => sum + cleanNumber(showroom.excessDiscount),
    0,
  );

  const maxDiscount = Math.max(
    ...comparisonShowrooms.map((showroom) =>
      cleanNumber(showroom.excessDiscount),
    ),
    1,
  );

  const buildPieSegments = (items) => {
    const filteredItems = items.filter((item) => cleanNumber(item.value) > 0);

    const total = filteredItems.reduce(
      (sum, item) => sum + cleanNumber(item.value),
      0,
    );

    let cumulative = 0;

    const segments = filteredItems.map((item, index) => {
      const value = cleanNumber(item.value);
      const percentage = total ? value / total : 0;
      const dash = `${percentage * 100} ${100 - percentage * 100}`;
      const offset = -cumulative * 100;

      cumulative += percentage;

      return {
        ...item,
        color: item.color || PIE_COLORS[index % PIE_COLORS.length],
        dash,
        offset,
        percentage,
      };
    });

    return {
      total,
      segments,
    };
  };

  const bookingPie = buildPieSegments(
    comparisonShowrooms.map((showroom) => ({
      label: showroom.showroomName,
      value: cleanNumber(showroom.bookings),
      color: getShowroomColor(showroom.key || showroom.id),
    })),
  );

  const deliveryPie = buildPieSegments(
    comparisonShowrooms.map((showroom) => ({
      label: showroom.showroomName,
      value: cleanNumber(showroom.deliveries),
      color: getShowroomColor(showroom.key || showroom.id),
    })),
  );

  const PieShareCard = ({ title, subtitle, pie }) => {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
        <div className="mb-5">
          <h3 className="text-sm font-black text-slate-900 dark:text-white">
            {title}
          </h3>

          <p className="mt-1 text-xs font-semibold text-slate-400">
            {subtitle}
          </p>
        </div>

        <div className="grid items-center gap-5 md:grid-cols-[180px_1fr] xl:grid-cols-1 2xl:grid-cols-[180px_1fr]">
          <div className="relative mx-auto h-[180px] w-[180px]">
            <svg viewBox="0 0 36 36" className="h-full w-full -rotate-90">
              <circle
                cx="18"
                cy="18"
                r="15.9155"
                fill="transparent"
                stroke="currentColor"
                strokeWidth="3.8"
                className="text-slate-100 dark:text-slate-800"
              />

              {pie.segments.map((segment) => (
                <circle
                  key={segment.label}
                  cx="18"
                  cy="18"
                  r="15.9155"
                  fill="transparent"
                  stroke={segment.color}
                  strokeWidth="3.8"
                  strokeDasharray={segment.dash}
                  strokeDashoffset={segment.offset}
                  strokeLinecap="round"
                  className="cursor-pointer transition-opacity hover:opacity-80"
                >
                  <title>
                    {`${segment.label} — ${cleanNumber(
                      segment.value,
                    ).toLocaleString("en-IN")} (${(
                      segment.percentage * 100
                    ).toFixed(1)}%)`}
                  </title>
                </circle>
              ))}
            </svg>

            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
              <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                Total
              </p>

              <p className="mt-1 text-xl font-black text-slate-950 dark:text-white">
                {pie.total.toLocaleString("en-IN")}
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {pie.segments.length ? (
              pie.segments.map((item) => (
                <div
                  key={item.label}
                  title={`${item.label} — ${cleanNumber(
                    item.value,
                  ).toLocaleString("en-IN")} (${(
                    item.percentage * 100
                  ).toFixed(1)}%)`}
                  className="flex cursor-help items-center justify-between gap-3 rounded-xl px-2 py-1 transition hover:bg-slate-50 dark:hover:bg-slate-900"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <span
                      className="h-3 w-3 shrink-0 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />

                    <p className="truncate text-xs font-bold text-slate-600 dark:text-slate-300">
                      {item.label}
                    </p>
                  </div>

                  <p className="whitespace-nowrap text-xs font-black text-slate-900 dark:text-white">
                    {cleanNumber(item.value).toLocaleString("en-IN")}{" "}
                    <span className="font-semibold text-slate-400">
                      ({(item.percentage * 100).toFixed(1)}%)
                    </span>
                  </p>
                </div>
              ))
            ) : (
              <div className="rounded-2xl bg-slate-50 p-6 text-center text-sm font-semibold text-slate-400 dark:bg-slate-900">
                No data available
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const buildTrendData = () => {
    const usableTransactions = (transactions || []).filter((txn) =>
      getTxnMonth(txn),
    );

    const monthSet = new Set();

    usableTransactions.forEach((txn) => {
      const month = getTxnMonth(txn);
      if (month) monthSet.add(month);
    });

    const allMonths = Array.from(monthSet).sort();

    if (!allMonths.length) {
      return {
        oldLabel: "Old Period",
        newLabel: "New Period",
        oldStats: {
          bookings: 0,
          deliveries: 0,
          units: 0,
          allowedDiscount: 0,
          actualDiscount: 0,
          excessDiscount: 0,
        },
        newStats: {
          bookings: 0,
          deliveries: 0,
          units: 0,
          allowedDiscount: 0,
          actualDiscount: 0,
          excessDiscount: 0,
        },
        monthRows: [],
      };
    }

    const selectedMonths = allMonths.slice(-trendMonths);
    const previousMonths = allMonths.slice(
      Math.max(0, allMonths.length - trendMonths * 2),
      Math.max(0, allMonths.length - trendMonths),
    );

    const makeStats = (months) => {
      const monthLookup = new Set(months);

      const periodTxns = usableTransactions.filter((txn) =>
        monthLookup.has(getTxnMonth(txn)),
      );

      return periodTxns.reduce(
        (acc, txn) => {
          const isDelivery = txn.stage === "delivery";

          acc.bookings += isDelivery ? 0 : 1;
          acc.deliveries += isDelivery ? 1 : 0;
          acc.units += 1;
          acc.allowedDiscount += getTxnAllowedDiscount(txn);
          acc.actualDiscount += getTxnActualDiscount(txn);
          acc.excessDiscount += getTxnExcessDiscount(txn);

          return acc;
        },
        {
          bookings: 0,
          deliveries: 0,
          units: 0,
          allowedDiscount: 0,
          actualDiscount: 0,
          excessDiscount: 0,
        },
      );
    };

    const monthRows = selectedMonths.map((month) => {
      const monthTxns = usableTransactions.filter(
        (txn) => getTxnMonth(txn) === month,
      );

      const showroomMap = {};

      monthTxns.forEach((txn) => {
        const showroomKey = getTxnShowroomKey(txn);
        const showroomName = getTxnShowroomName(txn);

        if (!showroomMap[showroomKey]) {
          showroomMap[showroomKey] = {
            showroomKey,
            showroomName,
            excessDiscount: 0,
          };
        }

        showroomMap[showroomKey].excessDiscount += getTxnExcessDiscount(txn);
      });

      const totalExcessForMonth = Object.values(showroomMap).reduce(
        (sum, row) => sum + cleanNumber(row.excessDiscount),
        0,
      );

      return {
        month,
        totalExcess: totalExcessForMonth,
        showroomRows: Object.values(showroomMap)
          .filter((row) => cleanNumber(row.excessDiscount) > 0)
          .sort((a, b) => b.excessDiscount - a.excessDiscount),
      };
    });

    return {
      oldLabel:
        previousMonths.length > 0
          ? `${monthLabel(previousMonths[0])} - ${monthLabel(
            previousMonths[previousMonths.length - 1],
          )}`
          : "Previous Period",

      newLabel:
        selectedMonths.length > 0
          ? `${monthLabel(selectedMonths[0])} - ${monthLabel(
            selectedMonths[selectedMonths.length - 1],
          )}`
          : "Current Period",

      oldStats: makeStats(previousMonths),
      newStats: makeStats(selectedMonths),
      monthRows,
    };
  };

  const TrendMetric = ({ label, oldValue, newValue, money = false }) => {
    const diff = cleanNumber(newValue) - cleanNumber(oldValue);
    const increased = diff >= 0;

    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
          {label}
        </p>

        <div className="mt-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-bold text-slate-400">Old Value</p>
            <p className="mt-1 text-xl font-black text-slate-900 dark:text-white">
              {money
                ? formatMoney(oldValue)
                : cleanNumber(oldValue).toLocaleString("en-IN")}
            </p>
          </div>

          <div
            className={`rounded-full px-3 py-1 text-sm font-black ${increased
                ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300"
                : "bg-red-50 text-red-700 dark:bg-red-400/10 dark:text-red-300"
              }`}
          >
            {increased ? "↑" : "↓"}{" "}
            {money
              ? formatMoney(Math.abs(diff))
              : Math.abs(diff).toLocaleString("en-IN")}
          </div>

          <div className="text-right">
            <p className="text-xs font-bold text-slate-400">New Value</p>
            <p className="mt-1 text-xl font-black text-slate-900 dark:text-white">
              {money
                ? formatMoney(newValue)
                : cleanNumber(newValue).toLocaleString("en-IN")}
            </p>
          </div>
        </div>
      </div>
    );
  };

  const ShowroomTrendModal = () => {
    if (!trendOpen) return null;

    const trendData = buildTrendData();

    const maxMonthlyExcess = Math.max(
      ...trendData.monthRows.map((row) => cleanNumber(row.totalExcess)),
      1,
    );

    return (
      <div className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-950/75 p-4 backdrop-blur-md">
        <div className="max-h-[92vh] w-full max-w-7xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-950">
          <div className="flex flex-col gap-4 border-b border-slate-200 bg-gradient-to-r from-amber-50 via-white to-indigo-50 p-5 dark:border-slate-800 dark:from-slate-900 dark:via-slate-950 dark:to-slate-900 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.25em] text-slate-500 dark:text-slate-400">
                Showroom Trends
              </p>

              <h2 className="mt-1 text-2xl font-black text-slate-950 dark:text-white">
                Showroom-wise Trend Dashboard
              </h2>

              <p className="mt-1 text-sm font-semibold text-slate-500 dark:text-slate-400">
                Compare previous period with selected recent period.
              </p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <select
                value={trendMonths}
                onChange={(e) => setTrendMonths(Number(e.target.value))}
                className="rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-black text-slate-800 outline-none transition focus:border-amber-400 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              >
                <option value={3}>Last 3 Months</option>
                <option value={6}>Last 6 Months</option>
                <option value={9}>Last 9 Months</option>
                <option value={12}>Last 12 Months</option>
              </select>

              <button
                type="button"
                onClick={() => setTrendOpen(false)}
                className="rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-black text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                Close
              </button>
            </div>
          </div>

          <div className="max-h-[calc(92vh-110px)] overflow-y-auto p-5">
            <div className="mb-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <TrendMetric
                label={`Total Bookings · ${trendData.oldLabel} → ${trendData.newLabel}`}
                oldValue={trendData.oldStats.bookings}
                newValue={trendData.newStats.bookings}
              />

              <TrendMetric
                label={`Total Deliveries · ${trendData.oldLabel} → ${trendData.newLabel}`}
                oldValue={trendData.oldStats.deliveries}
                newValue={trendData.newStats.deliveries}
              />

              <TrendMetric
                label={`Total Units · ${trendData.oldLabel} → ${trendData.newLabel}`}
                oldValue={trendData.oldStats.units}
                newValue={trendData.newStats.units}
              />

              <TrendMetric
                label={`Allowed Discount · ${trendData.oldLabel} → ${trendData.newLabel}`}
                oldValue={trendData.oldStats.allowedDiscount}
                newValue={trendData.newStats.allowedDiscount}
                money
              />

              <TrendMetric
                label={`Actual Discount · ${trendData.oldLabel} → ${trendData.newLabel}`}
                oldValue={trendData.oldStats.actualDiscount}
                newValue={trendData.newStats.actualDiscount}
                money
              />

              <TrendMetric
                label={`Excess Discount · ${trendData.oldLabel} → ${trendData.newLabel}`}
                oldValue={trendData.oldStats.excessDiscount}
                newValue={trendData.newStats.excessDiscount}
                money
              />
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <h3 className="text-sm font-black text-slate-900 dark:text-white">
                Month-wise Excess Discount Histogram
              </h3>

              <p className="mt-1 text-xs font-semibold text-slate-400">
                Each month shows showroom-wise excess discount breakup.
              </p>

              <div className="mt-5 space-y-5">
                {trendData.monthRows.length ? (
                  trendData.monthRows.map((row) => {
                    const pct =
                      (cleanNumber(row.totalExcess) / maxMonthlyExcess) * 100;

                    return (
                      <div key={row.month}>
                        <div className="mb-2 flex items-center justify-between gap-3">
                          <p className="text-sm font-black text-slate-800 dark:text-slate-100">
                            {monthLabel(row.month)}
                          </p>

                          <p className="text-sm font-black text-red-600 dark:text-red-300">
                            {formatMoney(row.totalExcess)}
                          </p>
                        </div>

                        <div className="h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                          <div
                            className="h-full rounded-full bg-red-500 transition-all duration-500"
                            style={{ width: `${pct}%` }}
                          />
                        </div>

                        <div className="mt-2 flex flex-wrap gap-2">
                          {row.showroomRows.map((showroomRow) => (
                            <span
                              key={`${row.month}-${showroomRow.showroomKey}`}
                              title={`${showroomRow.showroomName} — ${formatMoney(
                                showroomRow.excessDiscount,
                              )}`}
                              className="inline-flex items-center gap-2 rounded-full bg-slate-50 px-3 py-1 text-xs font-bold text-slate-600 dark:bg-slate-900 dark:text-slate-300"
                            >
                              <span
                                className="h-2.5 w-2.5 rounded-full"
                                style={{
                                  backgroundColor: getShowroomColor(
                                    showroomRow.showroomKey,
                                  ),
                                }}
                              />

                              {showroomRow.showroomName}:{" "}
                              {formatMoney(showroomRow.excessDiscount)}
                            </span>
                          ))}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="rounded-2xl bg-slate-50 p-8 text-center text-sm font-semibold text-slate-400 dark:bg-slate-900">
                    No month-wise trend data available.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const comparisonTransactionsForShowroom = (targetShowroom) => {
    const targetKey = String(targetShowroom.key || targetShowroom.id || "");
    const targetNameKey = normalizeNameKey(targetShowroom.showroomName || "");

    return (transactions || []).filter((txn) => {
      const txnShowroomKey = String(getTxnShowroomKey(txn));
      const txnShowroomNameKey = normalizeNameKey(getTxnShowroomName(txn));

      return (
        txnShowroomKey === targetKey ||
        (targetNameKey && txnShowroomNameKey === targetNameKey)
      );
    });
  };

  const buildTeamLeaderBreakdownForShowroom = (targetShowroom) => {
    const teamLeaderMap = {};

    comparisonTransactionsForShowroom(targetShowroom).forEach((txn) => {
      const teamLeaderName = getTxnTeamLeaderName(txn);

      if (!teamLeaderMap[teamLeaderName]) {
        teamLeaderMap[teamLeaderName] = {
          teamLeaderName,
          bookings: 0,
          deliveries: 0,
          totalUnits: 0,
          allowedDiscount: 0,
          actualDiscount: 0,
          excessDiscount: 0,
        };
      }

      const isDelivery = txn.stage === "delivery";

      teamLeaderMap[teamLeaderName].bookings += isDelivery ? 0 : 1;
      teamLeaderMap[teamLeaderName].deliveries += isDelivery ? 1 : 0;
      teamLeaderMap[teamLeaderName].totalUnits += 1;
      teamLeaderMap[teamLeaderName].allowedDiscount += getTxnAllowedDiscount(txn);
      teamLeaderMap[teamLeaderName].actualDiscount += getTxnActualDiscount(txn);
      teamLeaderMap[teamLeaderName].excessDiscount += getTxnExcessDiscount(txn);
    });

    return Object.values(teamLeaderMap)
      .map((row) => ({
        ...row,
        excessRate: row.actualDiscount
          ? Number(
            (
              (cleanNumber(row.excessDiscount) /
                cleanNumber(row.actualDiscount)) *
              100
            ).toFixed(1),
          )
          : 0,
      }))
      .sort((a, b) => b.totalUnits - a.totalUnits);
  };

  const tableRows = comparisonShowrooms
    .map((showroom) => {
      const units =
        cleanNumber(showroom.bookings) + cleanNumber(showroom.deliveries);

      const excessRate = showroom.actualDiscount
        ? Number(
          (
            (cleanNumber(showroom.excessDiscount) /
              cleanNumber(showroom.actualDiscount)) *
            100
          ).toFixed(1),
        )
        : 0;

      return {
        ...showroom,
        units,
        excessRate,
        teamLeaderRows: buildTeamLeaderBreakdownForShowroom(showroom),
      };
    })
    .sort((a, b) => b.units - a.units);

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/75 p-4 backdrop-blur-md">
      <ShowroomTrendModal />

      <div className="max-h-[92vh] w-full max-w-7xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-950">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 bg-gradient-to-r from-amber-50 via-white to-indigo-50 p-5 dark:border-slate-800 dark:from-slate-900 dark:via-slate-950 dark:to-slate-900">
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.25em] text-slate-500 dark:text-slate-400">
              Showroom Comparison
            </p>

            <h2 className="mt-1 text-2xl font-black text-slate-950 dark:text-white">
              Showroom-wise Performance Dashboard
            </h2>

            <p className="mt-1 text-sm font-semibold text-slate-500 dark:text-slate-400">
              Compare bookings, deliveries, discounts, excess discount and
              showroom share.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setTrendOpen(true)}
              className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-2 text-xs font-black uppercase tracking-wide text-white shadow-lg transition hover:-translate-y-0.5 hover:border-amber-400 hover:text-amber-300 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            >
              See Trends
            </button>

            <button
              type="button"
              onClick={onClose}
              className="rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-black text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Close
            </button>
          </div>
        </div>

        <div className="max-h-[calc(92vh-110px)] overflow-y-auto p-5">
          <div className="mb-5 grid gap-4 md:grid-cols-3">
            <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">
                Total Bookings
              </p>

              <p className="mt-3 text-3xl font-black text-indigo-600 dark:text-indigo-300">
                {totalBookings.toLocaleString("en-IN")}
              </p>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">
                Total Deliveries
              </p>

              <p className="mt-3 text-3xl font-black text-emerald-600 dark:text-emerald-300">
                {totalDeliveries.toLocaleString("en-IN")}
              </p>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">
                Total Excess Discount
              </p>

              <p className="mt-3 text-3xl font-black text-red-600 dark:text-red-300">
                {formatMoney(totalExcess)}
              </p>
            </div>
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <PieShareCard
              title="Pie Chart: Booking Showroom Share"
              subtitle="Share based on total bookings only"
              pie={bookingPie}
            />

            <PieShareCard
              title="Pie Chart: Delivery Showroom Share"
              subtitle="Share based on total deliveries only"
              pie={deliveryPie}
            />
          </div>

          <div className="mt-5 rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
            <h3 className="text-sm font-black text-slate-900 dark:text-white">
              Excess Discount Histogram
            </h3>

            <p className="mt-1 text-xs font-semibold text-slate-400">
              Showroom-wise excess discount exposure
            </p>

            <div className="mt-5 space-y-4">
              {comparisonShowrooms.map((showroom) => {
                const pct =
                  (cleanNumber(showroom.excessDiscount) / maxDiscount) * 100;

                const showroomColor = getShowroomColor(
                  showroom.key || showroom.id,
                );

                return (
                  <div
                    key={showroom.key || showroom.id}
                    title={`${showroom.showroomName} — ${formatMoney(
                      showroom.excessDiscount,
                    )}`}
                    className="cursor-help rounded-xl px-2 py-1 transition hover:bg-slate-50 dark:hover:bg-slate-900"
                  >
                    <div className="mb-1.5 flex items-center justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-2">
                        <span
                          className="h-3 w-3 shrink-0 rounded-full"
                          style={{ backgroundColor: showroomColor }}
                        />

                        <p className="truncate text-sm font-bold text-slate-700 dark:text-slate-200">
                          {showroom.showroomName}
                        </p>
                      </div>

                      <p
                        className="whitespace-nowrap text-sm font-black"
                        style={{ color: showroomColor }}
                      >
                        {formatMoney(showroom.excessDiscount)}
                      </p>
                    </div>

                    <div className="h-3 overflow-hidden rounded-full bg-slate-100 shadow-inner dark:bg-slate-800">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: showroomColor,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-5 overflow-hidden rounded-3xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
            <div className="border-b border-slate-100 p-5 dark:border-slate-800">
              <h3 className="text-sm font-black text-slate-900 dark:text-white">
                Showroom-wise Comparison Table
              </h3>

              <p className="mt-1 text-xs font-semibold text-slate-400">
                Complete showroom-level audit summary
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[980px] text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
                    {[
                      "Showroom",
                      "Bookings",
                      "Deliveries",
                      "Total Units",
                      "Allowed Discount",
                      "Actual Discount",
                      "Excess Discount",
                      "Excess Rate",
                    ].map((heading) => (
                      <th
                        key={heading}
                        className="px-4 py-3 text-left text-[10px] font-black uppercase tracking-widest text-slate-400"
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {tableRows.length ? (
                    tableRows.flatMap((showroom) => {
                      const showroomColor = getShowroomColor(
                        showroom.key || showroom.id,
                      );
                      const showroomKey = String(showroom.key || showroom.id);
                      const isExpanded =
                        String(expandedShowroomKey) === showroomKey;

                      const mainRow = (
                        <tr
                          key={showroomKey}
                          onClick={() =>
                            setExpandedShowroomKey((current) =>
                              String(current) === showroomKey
                                ? ""
                                : showroomKey,
                            )
                          }
                          className="cursor-pointer border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900"
                          title="Click to view team-leader-wise breakdown"
                        >
                          <td className="px-4 py-3 font-black text-slate-900 dark:text-white">
                            <div className="flex items-center gap-2">
                              <span
                                className="h-3 w-3 shrink-0 rounded-full"
                                style={{ backgroundColor: showroomColor }}
                              />

                              <span>{showroom.showroomName}</span>

                              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-black text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                                {isExpanded
                                  ? "Hide team leaders"
                                  : "View team leaders"}
                              </span>
                            </div>
                          </td>

                          <td className="px-4 py-3 font-bold text-indigo-600 dark:text-indigo-300">
                            {showroom.bookings}
                          </td>

                          <td className="px-4 py-3 font-bold text-emerald-600 dark:text-emerald-300">
                            {showroom.deliveries}
                          </td>

                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                            {showroom.units}
                          </td>

                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                            {formatMoney(showroom.allowedDiscount)}
                          </td>

                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                            {formatMoney(showroom.actualDiscount)}
                          </td>

                          <td
                            className="px-4 py-3 font-black"
                            style={{ color: showroomColor }}
                          >
                            {formatMoney(showroom.excessDiscount)}
                          </td>

                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                            {showroom.excessRate}%
                          </td>
                        </tr>
                      );

                      if (!isExpanded) return [mainRow];

                      const teamLeaderRow = (
                        <tr key={`${showroomKey}-team-leaders`}>
                          <td
                            colSpan={8}
                            className="border-b border-slate-100 bg-slate-50/70 p-0 dark:border-slate-800 dark:bg-slate-900/40"
                          >
                            <div className="my-4 ml-8 mr-4 overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
                              <div className="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
                                <p className="text-xs font-black uppercase tracking-widest text-slate-400">
                                  Team-leader-wise breakdown —{" "}
                                  {showroom.showroomName}
                                </p>
                              </div>

                              <div className="overflow-x-auto">
                                <table className="w-full min-w-[900px] text-sm">
                                  <thead>
                                    <tr className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
                                      {[
                                        "Team Leader",
                                        "Bookings",
                                        "Deliveries",
                                        "Total Units",
                                        "Allowed Discount",
                                        "Actual Discount",
                                        "Excess Discount",
                                        "Excess Rate",
                                      ].map((heading) => (
                                        <th
                                          key={heading}
                                          className="px-4 py-3 text-left text-[10px] font-black uppercase tracking-widest text-slate-400"
                                        >
                                          {heading}
                                        </th>
                                      ))}
                                    </tr>
                                  </thead>

                                  <tbody>
                                    {showroom.teamLeaderRows.length ? (
                                      showroom.teamLeaderRows.map((leader) => (
                                        <tr
                                          key={`${showroomKey}-${leader.teamLeaderName}`}
                                          className="border-b border-slate-100 last:border-b-0 dark:border-slate-800"
                                        >
                                          <td className="px-4 py-3 font-bold text-slate-800 dark:text-slate-100">
                                            <span className="mr-2 text-slate-400">
                                              ↳
                                            </span>
                                            {leader.teamLeaderName}
                                          </td>

                                          <td className="px-4 py-3 font-bold text-indigo-600 dark:text-indigo-300">
                                            {leader.bookings}
                                          </td>

                                          <td className="px-4 py-3 font-bold text-emerald-600 dark:text-emerald-300">
                                            {leader.deliveries}
                                          </td>

                                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                                            {leader.totalUnits}
                                          </td>

                                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                                            {formatMoney(
                                              leader.allowedDiscount,
                                            )}
                                          </td>

                                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                                            {formatMoney(
                                              leader.actualDiscount,
                                            )}
                                          </td>

                                          <td
                                            className="px-4 py-3 font-black"
                                            style={{ color: showroomColor }}
                                          >
                                            {formatMoney(
                                              leader.excessDiscount,
                                            )}
                                          </td>

                                          <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                                            {leader.excessRate}%
                                          </td>
                                        </tr>
                                      ))
                                    ) : (
                                      <tr>
                                        <td
                                          colSpan={8}
                                          className="px-4 py-6 text-center text-sm font-semibold text-slate-400"
                                        >
                                          No team-leader-wise data available for
                                          this showroom.
                                        </td>
                                      </tr>
                                    )}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          </td>
                        </tr>
                      );

                      return [mainRow, teamLeaderRow];
                    })
                  ) : (
                    <tr>
                      <td
                        colSpan={8}
                        className="px-4 py-10 text-center text-sm font-semibold text-slate-400"
                      >
                        No showroom comparison data available.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const ShowroomCarousel = ({
  showrooms,
  selectedShowroomKey,
  onSelect,
  onCompare,
  sortBy,
  onSortChange,
}) => {
  if (!showrooms.length) return null;

  return (
    <section className="mb-5">
      <div className="mb-3 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="mt-1 text-xl font-black text-slate-950 dark:text-white">
            Showroom-Wise Analysis
          </h2>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="min-w-[240px]">
            <select
              value={sortBy}
              onChange={(e) => onSortChange(e.target.value)}
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-2 text-xs font-black uppercase tracking-wide text-white outline-none transition focus:border-amber-400 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            >
              <option value="default">Default Order</option>
              <option value="alphabetical">Alphabetical</option>
              <option value="bookings_high">Bookings: High to Low</option>
              <option value="bookings_low">Bookings: Low to High</option>
              <option value="deliveries_high">Deliveries: High to Low</option>
              <option value="deliveries_low">Deliveries: Low to High</option>
              <option value="excess_high">Excess Discount: High to Low</option>
              <option value="excess_low">Excess Discount: Low to High</option>
            </select>
          </div>

          <button
            type="button"
            onClick={onCompare}
            className="rounded-2xl border border-amber-300 bg-amber-400 px-4 py-2 text-xs font-black uppercase tracking-wide text-slate-950 shadow-lg transition hover:-translate-y-0.5 hover:bg-amber-300 dark:border-amber-400/30 dark:bg-amber-400 dark:text-slate-950"
          >
            Compare All Showrooms Together
          </button>
        </div>
      </div>

      <div className="flex gap-5 overflow-x-auto pb-4">
        {showrooms.map((showroom) => {
          const active = String(selectedShowroomKey) === String(showroom.key);

          return (
            <button
              key={showroom.key}
              type="button"
              onClick={() => onSelect(showroom.key)}
              className={`group min-w-[220px] rounded-3xl border px-4 py-3 text-center transition-all duration-300 hover:-translate-y-1 hover:shadow-xl ${active
                  ? "border-amber-400 bg-amber-50 shadow-lg ring-2 ring-amber-200 dark:border-amber-400 dark:bg-amber-400/10 dark:ring-amber-400/20"
                  : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-800 dark:bg-slate-950 dark:hover:border-slate-700"
                }`}
            >
              <div className="mb-2 flex h-20 items-center justify-center overflow-hidden rounded-2xl bg-slate-50 p-1 dark:bg-slate-900">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-100 to-indigo-100 text-3xl dark:from-amber-400/10 dark:to-indigo-400/10">
                  🏬
                </div>
              </div>

              <p className="line-clamp-2 min-h-[36px] text-sm font-black leading-tight text-slate-900 dark:text-white">
                {showroom.showroomName}
              </p>

              <div className="mt-2 flex flex-wrap justify-center gap-2">
                <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-black text-indigo-700 dark:bg-indigo-400/10 dark:text-indigo-300">
                  B-: {showroom.bookings}
                </span>

                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300">
                  D-: {showroom.deliveries}
                </span>

                <span className="rounded-full bg-red-50 px-3 py-1 text-xs font-black text-red-700 dark:bg-red-400/10 dark:text-red-300">
                  Excess-: {formatMoney(showroom.excessDiscount)}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
};

const RtoCarousel = ({ analytics, selectedRtoKey, onSelect }) => {
  const rows = analytics?.summaryRows || [];

  if (!rows.length) return null;

  const cardImage = {
    lucknow: "/rto/lucknow.png",
    other: "",
    not_available: "",
  };

  const cardIcon = {
    lucknow: "🏙️",
    other: "🛣️",
    not_available: "❔",
  };

  const cardTitle = {
    lucknow: "Lucknow Bookings",
    other: "Outside Lucknow",
    not_available: "RTO Not Available",
  };

  const cardSubTitle = {
    lucknow: "UP32 / Lucknow",
    other: "Valid RTO outside Lucknow",
    not_available: "Missing / Invalid RTO",
  };

  return (
    <section className="mb-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="mt-1 text-xl font-black text-slate-950 dark:text-white">
            RTO-Wise Analysis
          </h2>
        </div>

        <p className="hidden text-xs font-semibold text-slate-400 md:block">
          Click an RTO category to open details
        </p>
      </div>

      <div className="flex gap-5 overflow-x-auto pb-4">
        {rows.map((row) => {
          const active = String(selectedRtoKey) === String(row.key);

          return (
            <button
              key={row.key}
              type="button"
              onClick={() => onSelect(row.key)}
              className={`group min-w-[220px] rounded-3xl border px-4 py-3 text-center transition-all duration-300 hover:-translate-y-1 hover:shadow-xl ${active
                  ? "border-amber-400 bg-amber-50 shadow-lg ring-2 ring-amber-200 dark:border-amber-400 dark:bg-amber-400/10 dark:ring-amber-400/20"
                  : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-800 dark:bg-slate-950 dark:hover:border-slate-700"
                }`}
            >
              <div className="mb-2 flex h-20 items-center justify-center overflow-hidden rounded-2xl bg-slate-50 p-1 dark:bg-slate-900">
                {cardImage[row.key] ? (
                  <img
                    src={cardImage[row.key]}
                    alt={cardTitle[row.key] || row.label}
                    className="h-16 w-full object-contain transition duration-300 group-hover:scale-110"
                    onError={(e) => {
                      e.currentTarget.style.display = "none";
                    }}
                  />
                ) : (
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-100 to-indigo-100 text-3xl dark:from-amber-400/10 dark:to-indigo-400/10">
                    {cardIcon[row.key] || "🧾"}
                  </div>
                )}
              </div>

              <p className="line-clamp-2 min-h-[36px] text-sm font-black leading-tight text-slate-900 dark:text-white">
                {cardTitle[row.key] || row.label}
              </p>

              <p className="mt-1 text-xs font-bold text-slate-400">
                {cardSubTitle[row.key] || row.rtoDisplay}
              </p>

              <div className="mt-2 flex flex-wrap justify-center gap-2">
                <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-black text-indigo-700 dark:bg-indigo-400/10 dark:text-indigo-300">
                  B-: {cleanNumber(row.bookings).toLocaleString("en-IN")}
                </span>

                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300">
                  {cleanNumber(row.share)}%
                </span>

                <span className="rounded-full bg-red-50 px-3 py-1 text-xs font-black text-red-700 dark:bg-red-400/10 dark:text-red-300">
                  RTO-: {cleanNumber(row.rtoCount)}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
};

const RtoDetailsModal = ({ open, onClose, title, rows, totalBookings }) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/75 p-4 backdrop-blur-md">
      <div className="max-h-[92vh] w-full max-w-6xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-950">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 bg-gradient-to-r from-amber-50 via-white to-indigo-50 p-5 dark:border-slate-800 dark:from-slate-900 dark:via-slate-950 dark:to-slate-900">
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.25em] text-slate-500 dark:text-slate-400">
              RTO Details
            </p>

            <h2 className="mt-1 text-2xl font-black text-slate-950 dark:text-white">
              {title}
            </h2>

            <p className="mt-1 text-sm font-semibold text-slate-500 dark:text-slate-400">
              RTO-wise booking distribution based on registered RTO numbers.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-black text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Close
          </button>
        </div>

        <div className="max-h-[calc(92vh-110px)] overflow-y-auto p-5">
          <div className="mb-5 grid gap-4 md:grid-cols-3">
            <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">
                Total Bookings
              </p>
              <p className="mt-3 text-3xl font-black text-indigo-600 dark:text-indigo-300">
                {cleanNumber(totalBookings).toLocaleString("en-IN")}
              </p>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">
                RTO Codes
              </p>
              <p className="mt-3 text-3xl font-black text-emerald-600 dark:text-emerald-300">
                {rows.length.toLocaleString("en-IN")}
              </p>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">
                Selected Bookings
              </p>
              <p className="mt-3 text-3xl font-black text-amber-600 dark:text-amber-300">
                {rows
                  .reduce((sum, row) => sum + cleanNumber(row.bookings), 0)
                  .toLocaleString("en-IN")}
              </p>
            </div>
          </div>

          <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
            <div className="border-b border-slate-100 p-5 dark:border-slate-800">
              <h3 className="text-sm font-black text-slate-900 dark:text-white">
                All Registered RTO Numbers
              </h3>
              <p className="mt-1 text-xs font-semibold text-slate-400">
                Click-through summary expanded at RTO code level.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[920px] text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
                    {[
                      "RTO Number",
                      "City",
                      "Bookings",
                      "Share",
                      "Allowed Discount",
                      "Actual Discount",
                      "Excess Discount",
                    ].map((heading) => (
                      <th
                        key={heading}
                        className="px-4 py-3 text-left text-[10px] font-black uppercase tracking-widest text-slate-400"
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {rows.length ? (
                    rows.map((row) => (
                      <tr
                        key={row.rtoCode}
                        className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900"
                      >
                        <td className="px-4 py-3 font-black text-slate-900 dark:text-white">
                          {row.rtoCode === "NOT_AVAILABLE"
                            ? "NOT AVAILABLE"
                            : row.rtoCode}
                        </td>

                        <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                          {row.city}
                        </td>

                        <td className="px-4 py-3 font-bold text-indigo-600 dark:text-indigo-300">
                          {row.bookings}
                        </td>

                        <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                          {row.share}%
                        </td>

                        <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                          {formatMoney(row.totalAllowedDiscount)}
                        </td>

                        <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                          {formatMoney(row.totalActualDiscount)}
                        </td>

                        <td className="px-4 py-3 font-black text-red-600 dark:text-red-300">
                          {formatMoney(row.totalExcessDiscount)}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td
                        colSpan={7}
                        className="px-4 py-10 text-center text-sm font-semibold text-slate-400"
                      >
                        No RTO booking data available.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const RtoBookingsTable = ({ analytics, onOpen }) => {
  if (!analytics.totalBookings) {
    return (
      <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="mt-1 text-xl font-black text-slate-950 dark:text-white">
              RTO Bookings
            </h2>
          </div>
        </div>

        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center text-sm font-semibold text-slate-400 dark:border-slate-800 dark:bg-slate-900">
          No RTO booking data available.
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="mt-1 text-xl font-black text-slate-950 dark:text-white">
            RTO-Wise Analysis
          </h2>
        </div>

        <span className="rounded-full bg-slate-100 px-4 py-2 text-xs font-black text-slate-600 dark:bg-slate-900 dark:text-slate-300">
          Total {analytics.totalBookings.toLocaleString("en-IN")}
        </span>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800">
        <table className="w-full min-w-[860px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
              {[
                "Particulars",
                "RTO",
                "Bookings",
                "Share",
                "RTO Count",
                "Action",
              ].map((heading) => (
                <th
                  key={heading}
                  className="px-4 py-3 text-left text-[10px] font-black uppercase tracking-widest text-slate-400"
                >
                  {heading}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {analytics.summaryRows.map((row) => (
              <tr
                key={row.key}
                className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900"
              >
                <td className="px-4 py-3 font-black text-slate-900 dark:text-white">
                  {row.label}
                </td>

                <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                  {row.rtoDisplay}
                </td>

                <td className="px-4 py-3 font-bold text-indigo-600 dark:text-indigo-300">
                  {row.bookings.toLocaleString("en-IN")}
                </td>

                <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                  {row.share}%
                </td>

                <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                  {row.rtoCount.toLocaleString("en-IN")}
                </td>

                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => onOpen(row.key)}
                    className="rounded-xl border border-amber-300 bg-amber-400 px-3 py-2 text-xs font-black uppercase tracking-wide text-slate-950 shadow-sm transition hover:-translate-y-0.5 hover:bg-amber-300 dark:border-amber-400/30 dark:bg-amber-400 dark:text-slate-950"
                  >
                    View RTOs
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

const getComplaintValue = (row, keys, fallback = "—") => {
  for (const key of keys) {
    const value = row?.[key];

    if (value !== undefined && value !== null && String(value).trim() !== "") {
      return value;
    }
  }

  return fallback;
};

const getNestedComplaintValue = (row, paths, fallback = "—") => {
  for (const path of paths) {
    const value = path.split(".").reduce((obj, key) => obj?.[key], row);

    if (value !== undefined && value !== null && String(value).trim() !== "") {
      return value;
    }
  }

  return fallback;
};

const joinComplaintParty = (dealer, showroom) => {
  const cleanDealer = dealer && dealer !== "—" ? String(dealer).trim() : "";
  const cleanShowroom =
    showroom && showroom !== "—" ? String(showroom).trim() : "";

  if (cleanDealer && cleanShowroom) return `${cleanDealer} – ${cleanShowroom}`;
  if (cleanDealer) return cleanDealer;
  if (cleanShowroom) return cleanShowroom;

  return "—";
};

const buildComplaintsAnalytics = (complaints = []) => {
  const rows = Array.isArray(complaints) ? complaints : [];

  return {
    totalComplaints: rows.length,
    rows: rows.map((complaint, index) => {
      const complainantDealer = getNestedComplaintValue(complaint, [
        "complainant_dealer_name",
        "complainantDealerName",
        "complainant_dealership",
        "complainantDealership",
        "dealer_showroom_details.complainant_dealership",
        "dealerShowroomDetails.complainant_dealership",
        "dealerShowroomDetails.complainantDealership",
      ]);

      const complainantShowroom = getNestedComplaintValue(complaint, [
        "complainant_showroom_name",
        "complainantShowroomName",
        "complainant_showroom",
        "complainantShowroom",
        "dealer_showroom_details.complainant_showroom",
        "dealerShowroomDetails.complainant_showroom",
        "dealerShowroomDetails.complainantShowroom",
      ]);

      const complaineeDealer = getNestedComplaintValue(complaint, [
        "complainee_dealer_name",
        "complaineeDealerName",
        "complainee_dealership",
        "complaineeDealership",
        "dealer_showroom_details.complainee_dealership",
        "dealerShowroomDetails.complainee_dealership",
        "dealerShowroomDetails.complaineeDealership",
      ]);

      const complaineeShowroom = getNestedComplaintValue(complaint, [
        "complainee_showroom_name",
        "complaineeShowroomName",
        "complainee_showroom",
        "complaineeShowroom",
        "dealer_showroom_details.complainee_showroom",
        "dealerShowroomDetails.complainee_showroom",
        "dealerShowroomDetails.complaineeShowroom",
      ]);

      const customerName = getNestedComplaintValue(complaint, [
        "customer_name",
        "customerName",
        "customer_details.customer_name",
        "customerDetails.customer_name",
        "customerDetails.customerName",
      ]);

      const complainant =
        joinComplaintParty(complainantDealer, complainantShowroom) !== "—"
          ? joinComplaintParty(complainantDealer, complainantShowroom)
          : customerName;

      const complainee = joinComplaintParty(
        complaineeDealer,
        complaineeShowroom,
      );

      return {
        id:
          complaint.id ||
          complaint.complaint_id ||
          complaint.complaintId ||
          complaint.complaint_code ||
          complaint.complaintCode ||
          index + 1,

        complainant,
        complainee,

        subject: getNestedComplaintValue(complaint, [
          "subject",
          "title",
          "complaint_subject",
          "complaintSubject",
          "complaint_type",
          "complaintType",
          "category",
          "issue",
          "remarks_page.remarks_by_complainant",
          "remarksPage.remarks_by_complainant",
          "remarksPage.remarksByComplainant",
          "remarks_complainant",
          "remarksComplainant",
        ]),

        status: getNestedComplaintValue(complaint, [
          "status",
          "complaint_status",
          "complaintStatus",
        ]),

        date: getNestedComplaintValue(complaint, [
          "date",
          "complaint_date",
          "complaintDate",
          "date_of_complaint",
          "dateOfComplaint",
          "created_at",
          "createdAt",
          "remarks_page.complaint_raised_date",
          "remarksPage.complaint_raised_date",
          "remarksPage.complaintRaisedDate",
        ]),
      };
    }),
  };
};
const ComplaintsInformationTable = ({ analytics }) => {
  const rows = analytics?.rows || [];
  const total = analytics?.totalComplaints || 0;

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="mt-1 text-xl font-black text-slate-950 dark:text-white">
            Complaints Information
          </h2>

          <p className="mt-1 text-xs font-semibold text-slate-400">
            Complainant and complainee details in tabular form.
          </p>
        </div>

        <span className="rounded-full bg-slate-100 px-4 py-2 text-xs font-black text-slate-600 dark:bg-slate-900 dark:text-slate-300">
          Total {total.toLocaleString("en-IN")}
        </span>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800">
        <table className="w-full min-w-[860px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
              {[
                "S No.",
                "Complainant",
                "Complainee",
                "Subject / Type",
                "Status",
                "Date",
              ].map((heading) => (
                <th
                  key={heading}
                  className="px-4 py-3 text-left text-[10px] font-black uppercase tracking-widest text-slate-400"
                >
                  {heading}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.length ? (
              rows.map((row, index) => (
                <tr
                  key={row.id || index}
                  className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900"
                >
                  <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                    {index + 1}
                  </td>

                  <td className="px-4 py-3 font-black text-slate-900 dark:text-white">
                    {row.complainant}
                  </td>

                  <td className="px-4 py-3 font-black text-slate-900 dark:text-white">
                    {row.complainee}
                  </td>

                  <td className="px-4 py-3 font-semibold text-slate-700 dark:text-slate-200">
                    {row.subject}
                  </td>

                  <td className="px-4 py-3">
                    <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-black text-indigo-700 dark:bg-indigo-400/10 dark:text-indigo-300">
                      {row.status}
                    </span>
                  </td>

                  <td className="px-4 py-3 font-semibold text-slate-700 dark:text-slate-200">
                    {String(row.date).slice(0, 10)}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={6}
                  className="px-4 py-10 text-center text-sm font-semibold text-slate-400"
                >
                  No complaints data available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};

const getPendencyValue = (row, keys, fallback = "—") => {
  for (const key of keys) {
    const value = row?.[key];

    if (value !== undefined && value !== null && String(value).trim() !== "") {
      return value;
    }
  }

  return fallback;
};

const isPendencyPending = (pendency) => {
  const status = String(
    pendency.status ||
    pendency.file_status ||
    pendency.fileStatus ||
    pendency.stage ||
    pendency.current_status ||
    pendency.currentStatus ||
    pendency.task_status ||
    pendency.taskStatus ||
    "",
  )
    .trim()
    .toLowerCase();

  if (!status) return true;

  const completedStatuses = [
    "completed",
    "complete",
    "closed",
    "done",
    "resolved",
    "submitted",
    "filed",
    "finished",
    "approved",
  ];

  return !completedStatuses.includes(status);
};

const buildPendencyAnalytics = (pendencies = []) => {
  const rows = Array.isArray(pendencies) ? pendencies : [];

  const mappedRows = rows.map((pendency, index) => {
    const pending = isPendencyPending(pendency);

    return {
      id:
        pendency.id ||
        pendency.file_id ||
        pendency.fileId ||
        pendency.pendency_id ||
        pendency.pendencyId ||
        pendency.task_id ||
        pendency.taskId ||
        index + 1,

      fileName: getPendencyValue(pendency, [
        "file_name",
        "fileName",
        "file",
        "name",
        "title",
        "task_name",
        "taskName",
        "work_name",
        "workName",
      ]),

      clientName: getPendencyValue(pendency, [
        "client_name",
        "clientName",
        "client",
        "customer_name",
        "customerName",
        "dealer_name",
        "dealerName",
        "dealership_name",
        "dealershipName",
      ]),

      assignedTo: getPendencyValue(pendency, [
        "assigned_to",
        "assignedTo",
        "responsible_person",
        "responsiblePerson",
        "respondent",
        "user_name",
        "userName",
        "employee_name",
        "employeeName",
        "executive_name",
        "executiveName",
      ]),

      status: getPendencyValue(
        pendency,
        [
          "status",
          "file_status",
          "fileStatus",
          "stage",
          "current_status",
          "currentStatus",
          "task_status",
          "taskStatus",
        ],
        pending ? "Pending" : "Completed",
      ),

      dueDate: getPendencyValue(pendency, [
        "due_date",
        "dueDate",
        "target_date",
        "targetDate",
        "deadline",
        "expected_completion_date",
        "expectedCompletionDate",
      ]),

      pending,
    };
  });

  const pendingRows = mappedRows.filter((row) => row.pending);

  return {
    totalFiles: mappedRows.length,
    totalPending: pendingRows.length,
    totalCompleted: mappedRows.length - pendingRows.length,
    rows: mappedRows,
    pendingRows,
  };
};

const PendencyInformationTable = ({ analytics }) => {
  const rows = analytics?.rows || [];

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="mt-1 text-xl font-black text-slate-950 dark:text-white">
            Pendency Information
          </h2>

          <p className="mt-1 text-xs font-semibold text-slate-400">
            Total files and pending files summary.
          </p>
        </div>

        <div className="flex flex-wrap justify-end gap-2">
          <span className="rounded-full bg-indigo-50 px-4 py-2 text-xs font-black text-indigo-700 dark:bg-indigo-400/10 dark:text-indigo-300">
            Total Files{" "}
            {cleanNumber(analytics?.totalFiles).toLocaleString("en-IN")}
          </span>

          <span className="rounded-full bg-red-50 px-4 py-2 text-xs font-black text-red-700 dark:bg-red-400/10 dark:text-red-300">
            Pending{" "}
            {cleanNumber(analytics?.totalPending).toLocaleString("en-IN")}
          </span>

          <span className="rounded-full bg-emerald-50 px-4 py-2 text-xs font-black text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300">
            Completed{" "}
            {cleanNumber(analytics?.totalCompleted).toLocaleString("en-IN")}
          </span>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800">
        <table className="w-full min-w-[900px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
              {[
                "S No.",
                "File / Task",
                "Client",
                "Assigned To",
                "Status",
                "Due Date",
              ].map((heading) => (
                <th
                  key={heading}
                  className="px-4 py-3 text-left text-[10px] font-black uppercase tracking-widest text-slate-400"
                >
                  {heading}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.length ? (
              rows.map((row, index) => (
                <tr
                  key={row.id || index}
                  className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900"
                >
                  <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-200">
                    {index + 1}
                  </td>

                  <td className="px-4 py-3 font-black text-slate-900 dark:text-white">
                    {row.fileName}
                  </td>

                  <td className="px-4 py-3 font-semibold text-slate-700 dark:text-slate-200">
                    {row.clientName}
                  </td>

                  <td className="px-4 py-3 font-semibold text-slate-700 dark:text-slate-200">
                    {row.assignedTo}
                  </td>

                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-black ${row.pending
                          ? "bg-red-50 text-red-700 dark:bg-red-400/10 dark:text-red-300"
                          : "bg-emerald-50 text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300"
                        }`}
                    >
                      {row.status}
                    </span>
                  </td>

                  <td className="px-4 py-3 font-semibold text-slate-700 dark:text-slate-200">
                    {String(row.dueDate || "—").slice(0, 10)}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={6}
                  className="px-4 py-10 text-center text-sm font-semibold text-slate-400"
                >
                  No pendency data available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};

const CarMetricCard = ({ title, value, tone = "slate" }) => {
  const toneMap = {
    indigo:
      "bg-indigo-50 text-indigo-700 dark:bg-indigo-400/10 dark:text-indigo-300",
    green:
      "bg-emerald-50 text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300",
    red: "bg-red-50 text-red-700 dark:bg-red-400/10 dark:text-red-300",
    amber:
      "bg-amber-50 text-amber-700 dark:bg-amber-400/10 dark:text-amber-300",
    slate: "bg-slate-50 text-slate-700 dark:bg-slate-900 dark:text-slate-300",
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
        {title}
      </p>

      <p
        className={`mt-2 inline-flex rounded-xl px-3 py-1 text-xl font-black ${toneMap[tone] || toneMap.slate
          }`}
      >
        {value}
      </p>
    </div>
  );
};

const MiniBar = ({
  label,
  value,
  max,
  color = "bg-indigo-500",
  money = false,
}) => {
  const pct = max ? (cleanNumber(value) / max) * 100 : 0;

  return (
    <div>
      <div className="mb-1 flex justify-between gap-3">
        <p className="truncate text-xs font-bold text-slate-600 dark:text-slate-300">
          {label}
        </p>

        <p className="whitespace-nowrap text-xs font-black text-slate-900 dark:text-white">
          {money
            ? formatMoney(value)
            : cleanNumber(value).toLocaleString("en-IN")}
        </p>
      </div>

      <div className="h-3 rounded-full bg-slate-100 dark:bg-slate-800">
        <div
          className={`h-3 rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

const MixBarChart = ({
  title,
  items,
  color = "bg-indigo-500",
  empty = "No data",
}) => {
  const max = Math.max(...items.map((item) => cleanNumber(item.count)), 0);
  const total = items.reduce((sum, item) => sum + cleanNumber(item.count), 0);

  if (!items.length || !max) {
    return (
      <div className="rounded-3xl border border-slate-200 p-5 dark:border-slate-800">
        <h3 className="mb-4 text-sm font-black text-slate-900 dark:text-white">
          {title}
        </h3>

        <div className="flex h-40 items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 text-sm font-semibold text-slate-400 dark:border-slate-800 dark:bg-slate-900">
          {empty}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-3xl border border-slate-200 p-5 dark:border-slate-800">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="text-sm font-black text-slate-900 dark:text-white">
          {title}
        </h3>

        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-black text-slate-600 dark:bg-slate-900 dark:text-slate-300">
          Total {total}
        </span>
      </div>

      <div className="space-y-4">
        {items.map((item) => {
          const pct = max ? (cleanNumber(item.count) / max) * 100 : 0;
          const share = total
            ? ((cleanNumber(item.count) / total) * 100).toFixed(1)
            : "0.0";

          return (
            <div key={item.label}>
              <div className="mb-1.5 flex items-center justify-between gap-3">
                <p className="truncate text-sm font-bold text-slate-700 dark:text-slate-200">
                  {item.label}
                </p>

                <p className="whitespace-nowrap text-sm font-black text-slate-950 dark:text-white">
                  {item.count}{" "}
                  <span className="text-xs font-semibold text-slate-400">
                    ({share}%)
                  </span>
                </p>
              </div>

              <div className="h-3 overflow-hidden rounded-full bg-slate-100 shadow-inner dark:bg-slate-800">
                <div
                  className={`h-full rounded-full ${color} transition-all duration-500`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const SelectedCarPanel = ({ car }) => {
  if (!car) return null;

  const graphItems = [
    { label: "Bookings", value: car.bookings, color: "bg-indigo-500" },
    { label: "Deliveries", value: car.deliveries, color: "bg-emerald-500" },
    {
      label: "Allowed Discount",
      value: car.allowedDiscount,
      color: "bg-amber-500",
      money: true,
    },
    {
      label: "Actual Discount",
      value: car.actualDiscount,
      color: "bg-cyan-500",
      money: true,
    },
    {
      label: "Excess Discount",
      value: car.excessDiscount,
      color: "bg-red-500",
      money: true,
    },
  ];

  const maxValue = Math.max(
    ...graphItems.map((item) => cleanNumber(item.value)),
    1,
  );

  const variantRows = sortEntries(car.variants, 6).map(([variant, count]) => ({
    label: variant,
    count,
  }));

  const outletRows = sortEntries(car.outlets, 6).map(([outlet, count]) => ({
    label: outlet,
    count,
  }));

  return (
    <section className="mb-9 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="border-b border-slate-100 bg-gradient-to-r from-amber-50 via-white to-indigo-50 p-5 dark:border-slate-800 dark:from-slate-900 dark:via-slate-950 dark:to-slate-900">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            <div className="h-24 w-32 rounded-3xl bg-white p-3 shadow-sm dark:bg-slate-900">
              <CarImage car={car} />
            </div>

            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">
                Selected Car
              </p>

              <h2 className="mt-1 text-2xl font-black text-slate-950 dark:text-white">
                {car.carName}
              </h2>

              <p className="mt-1 text-sm font-semibold text-slate-500 dark:text-slate-400">
                Car-wise bookings, deliveries, discounts and excess analysis
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:w-[520px]">
            <CarMetricCard
              title="Bookings"
              value={car.bookings}
              tone="indigo"
            />

            <CarMetricCard
              title="Deliveries"
              value={car.deliveries}
              tone="green"
            />

            <CarMetricCard
              title="Excess"
              value={formatMoney(car.excessDiscount)}
              tone={car.excessDiscount > 0 ? "red" : "green"}
            />
          </div>
        </div>
      </div>

      <div className="grid gap-5 p-5 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="grid gap-5">
          <div className="rounded-3xl border border-slate-200 p-5 dark:border-slate-800">
            <h3 className="mb-4 text-sm font-black text-slate-900 dark:text-white">
              Car Performance Graph
            </h3>

            <div className="space-y-4">
              {graphItems.map((item) => (
                <MiniBar
                  key={item.label}
                  label={item.label}
                  value={item.value}
                  max={maxValue}
                  color={item.color}
                  money={item.money}
                />
              ))}
            </div>
          </div>

          <MixBarChart
            title="Outlet Mix"
            items={outletRows}
            color="bg-emerald-500"
            empty="No outlet data"
          />
        </div>

        <div className="grid gap-5">
          <MixBarChart
            title="Variant Mix"
            items={variantRows}
            color="bg-violet-500"
            empty="No variant data"
          />
        </div>
      </div>
    </section>
  );
};

const SelectedShowroomPanel = ({ showroom }) => {
  if (!showroom) return null;

  const graphItems = [
    { label: "Bookings", value: showroom.bookings, color: "bg-indigo-500" },
    {
      label: "Deliveries",
      value: showroom.deliveries,
      color: "bg-emerald-500",
    },
    {
      label: "Allowed Discount",
      value: showroom.allowedDiscount,
      color: "bg-amber-500",
      money: true,
    },
    {
      label: "Actual Discount",
      value: showroom.actualDiscount,
      color: "bg-cyan-500",
      money: true,
    },
    {
      label: "Excess Discount",
      value: showroom.excessDiscount,
      color: "bg-red-500",
      money: true,
    },
  ];

  const maxValue = Math.max(
    ...graphItems.map((item) => cleanNumber(item.value)),
    1,
  );

  const carRows = sortEntries(showroom.cars, 6).map(([car, count]) => ({
    label: car,
    count,
  }));

  const variantRows = sortEntries(showroom.variants, 6).map(
    ([variant, count]) => ({
      label: variant,
      count,
    }),
  );

  return (
    <section className="mb-9 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="border-b border-slate-100 bg-gradient-to-r from-indigo-50 via-white to-amber-50 p-5 dark:border-slate-800 dark:from-slate-900 dark:via-slate-950 dark:to-slate-900">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-24 w-24 items-center justify-center rounded-3xl bg-white text-5xl shadow-sm dark:bg-slate-900">
              🏬
            </div>

            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">
                Selected Showroom
              </p>

              <h2 className="mt-1 text-2xl font-black text-slate-950 dark:text-white">
                {showroom.showroomName}
              </h2>

              <p className="mt-1 text-sm font-semibold text-slate-500 dark:text-slate-400">
                Showroom-wise bookings, deliveries, discounts and excess
                analysis
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:w-[520px]">
            <CarMetricCard
              title="Bookings"
              value={showroom.bookings}
              tone="indigo"
            />

            <CarMetricCard
              title="Deliveries"
              value={showroom.deliveries}
              tone="green"
            />

            <CarMetricCard
              title="Excess"
              value={formatMoney(showroom.excessDiscount)}
              tone={showroom.excessDiscount > 0 ? "red" : "green"}
            />
          </div>
        </div>
      </div>

      <div className="grid gap-5 p-5 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="grid gap-5">
          <div className="rounded-3xl border border-slate-200 p-5 dark:border-slate-800">
            <h3 className="mb-4 text-sm font-black text-slate-900 dark:text-white">
              Showroom Performance Graph
            </h3>

            <div className="space-y-4">
              {graphItems.map((item) => (
                <MiniBar
                  key={item.label}
                  label={item.label}
                  value={item.value}
                  max={maxValue}
                  color={item.color}
                  money={item.money}
                />
              ))}
            </div>
          </div>

          <MixBarChart
            title="Variant Mix"
            items={variantRows}
            color="bg-violet-500"
            empty="No variant data"
          />
        </div>

        <div className="grid gap-5">
          <MixBarChart
            title="Car Mix"
            items={carRows}
            color="bg-indigo-500"
            empty="No car data"
          />
        </div>
      </div>
    </section>
  );
};

const KpiCard = ({ icon, title, value, subtitle, tone = "slate" }) => {
  const toneMap = {
    indigo: "from-indigo-500/15 border-indigo-200 dark:border-indigo-400/20",
    green: "from-emerald-500/15 border-emerald-200 dark:border-emerald-400/20",
    red: "from-red-500/15 border-red-200 dark:border-red-400/20",
    amber: "from-amber-500/15 border-amber-200 dark:border-amber-400/20",
    slate: "from-slate-500/10 border-slate-200 dark:border-slate-800",
  };

  return (
    <div
      className={`relative overflow-hidden rounded-3xl border bg-gradient-to-br ${toneMap[tone] || toneMap.slate
        } to-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-xl dark:to-slate-950`}
    >
      <div className="absolute -right-8 -top-8 h-28 w-28 rounded-full bg-white/40 blur-2xl dark:bg-white/5" />

      <div className="relative flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-black uppercase tracking-[0.20em] text-slate-400">
            {title}
          </p>
          <p className="mt-3 text-2xl font-black text-slate-950 dark:text-white">
            {value}
          </p>
          {subtitle ? (
            <p className="mt-2 text-sm font-semibold text-slate-500 dark:text-slate-400">
              {subtitle}
            </p>
          ) : null}
        </div>

        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white text-2xl shadow-sm dark:bg-slate-900">
          {icon}
        </div>
      </div>
    </div>
  );
};

const DonutChart = ({ title, subtitle, data, centerLabel, centerValue }) => {
  const total = data.reduce((sum, item) => sum + cleanNumber(item.value), 0);

  let cumulative = 0;

  const segments = data
    .filter((item) => cleanNumber(item.value) > 0)
    .map((item, index) => {
      const value = cleanNumber(item.value);
      const percentage = total ? value / total : 0;
      const dash = `${percentage * 100} ${100 - percentage * 100}`;
      const offset = -cumulative * 100;
      cumulative += percentage;

      return {
        ...item,
        color: item.color || PIE_COLORS[index % PIE_COLORS.length],
        dash,
        offset,
      };
    });

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-black text-slate-900 dark:text-white">
            {title}
          </h3>
          {subtitle ? (
            <p className="mt-1 text-xs font-semibold text-slate-400">
              {subtitle}
            </p>
          ) : null}
        </div>
      </div>

      <div className="grid items-center gap-5 md:grid-cols-[180px_1fr]">
        <div className="relative mx-auto h-[180px] w-[180px]">
          <svg viewBox="0 0 36 36" className="h-full w-full -rotate-90">
            <circle
              cx="18"
              cy="18"
              r="15.9155"
              fill="transparent"
              stroke="currentColor"
              strokeWidth="3.8"
              className="text-slate-100 dark:text-slate-800"
            />

            {segments.map((segment) => (
              <circle
                key={segment.label}
                cx="18"
                cy="18"
                r="15.9155"
                fill="transparent"
                stroke={segment.color}
                strokeWidth="3.8"
                strokeDasharray={segment.dash}
                strokeDashoffset={segment.offset}
                strokeLinecap="round"
              />
            ))}
          </svg>

          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
              {centerLabel}
            </p>
            <p className="mt-1 text-xl font-black text-slate-950 dark:text-white">
              {centerValue}
            </p>
          </div>
        </div>

        <div className="space-y-3">
          {segments.length ? (
            segments.map((item) => {
              const pct = total
                ? ((cleanNumber(item.value) / total) * 100).toFixed(1)
                : "0.0";

              return (
                <div
                  key={item.label}
                  className="flex items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <p className="text-xs font-bold text-slate-600 dark:text-slate-300">
                      {item.label}
                    </p>
                  </div>

                  <p className="text-xs font-black text-slate-900 dark:text-white">
                    {item.format === "money"
                      ? formatMoney(item.value)
                      : cleanNumber(item.value).toLocaleString("en-IN")}{" "}
                    <span className="font-semibold text-slate-400">
                      ({pct}%)
                    </span>
                  </p>
                </div>
              );
            })
          ) : (
            <div className="rounded-2xl bg-slate-50 p-6 text-center text-sm font-semibold text-slate-400 dark:bg-slate-900">
              No chart data available
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const BarChart = ({
  items,
  color = "bg-indigo-500",
  valueType = "number",
  empty = "No data",
}) => {
  const max = Math.max(...items.map(([, value]) => cleanNumber(value)), 0);

  if (!items.length || !max) {
    return (
      <div className="flex h-40 items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 text-sm font-semibold text-slate-400 dark:border-slate-800 dark:bg-slate-900">
        {empty}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {items.map(([label, value]) => {
        const pct = max ? (cleanNumber(value) / max) * 100 : 0;

        return (
          <div key={label}>
            <div className="mb-1.5 flex items-center justify-between gap-3">
              <p className="truncate text-xs font-bold text-slate-600 dark:text-slate-300">
                {label}
              </p>
              <p className="whitespace-nowrap text-xs font-black text-slate-900 dark:text-white">
                {valueType === "money"
                  ? formatMoney(value)
                  : cleanNumber(value).toLocaleString("en-IN")}
              </p>
            </div>

            <div className="h-3 overflow-hidden rounded-full bg-slate-100 shadow-inner dark:bg-slate-800">
              <div
                className={`h-full rounded-full ${color} transition-all duration-500`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};

const ChartCard = ({ title, subtitle, children }) => {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-5 flex items-baseline justify-between gap-3 border-b border-slate-100 pb-3 dark:border-slate-800">
        <div>
          <h3 className="text-sm font-black text-slate-900 dark:text-white">
            {title}
          </h3>
          {subtitle ? (
            <p className="mt-1 text-xs font-semibold text-slate-400">
              {subtitle}
            </p>
          ) : null}
        </div>
      </div>

      {children}
    </div>
  );
};

const PrettyTable = ({ title, subtitle, columns, rows, empty = "No data" }) => {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-5 border-b border-slate-100 pb-3 dark:border-slate-800">
        <h3 className="text-sm font-black text-slate-900 dark:text-white">
          {title}
        </h3>
        {subtitle ? (
          <p className="mt-1 text-xs font-semibold text-slate-400">
            {subtitle}
          </p>
        ) : null}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`py-3 text-[10px] font-black uppercase tracking-widest text-slate-400 ${col.align === "right" ? "text-right" : "text-left"
                    }`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.length ? (
              rows.map((row, index) => (
                <tr
                  key={row.id || row.key || index}
                  className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900"
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={`py-3 text-sm ${col.align === "right" ? "text-right" : "text-left"
                        } ${col.className ||
                        "font-semibold text-slate-700 dark:text-slate-200"
                        }`}
                    >
                      {col.render ? col.render(row, index) : row[col.key]}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={columns.length}
                  className="py-10 text-center text-sm font-semibold text-slate-400"
                >
                  {empty}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const SectionHeader = ({ title, actionLabel, actionPath }) => {
  return (
    <div className="mb-4 mt-9 flex w-full items-center gap-3">
      <p className="whitespace-nowrap text-[11px] font-black uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
        {title}
      </p>

      <div className="h-px flex-1 bg-gradient-to-r from-slate-200 to-transparent dark:from-slate-800" />

      {actionLabel && actionPath ? (
        <a
          href={actionPath}
          className="rounded-full border border-orange-200 bg-orange-50 px-3 py-1.5 text-[10px] font-black uppercase tracking-wide text-orange-700 transition hover:bg-orange-100 dark:border-orange-400/20 dark:bg-orange-400/10 dark:text-orange-300"
        >
          {actionLabel}
        </a>
      ) : null}
    </div>
  );
};

const AnalyticsPanel = ({ title, stage, analytics, userRole }) => {
  const canViewMis = userRole !== "client";

  const complianceData = [
    { label: "OK Cases", value: analytics.okCases, color: "#10b981" },
    { label: "Excess Cases", value: analytics.excessCases, color: "#ef4444" },
  ];

  const discountData = [
    {
      label: "Allowed Discount",
      value: analytics.totalDiscount,
      color: "#6366f1",
      format: "money",
    },
    {
      label: "Actual Discount",
      value: analytics.totalActualDiscount,
      color: "#10b981",
      format: "money",
    },
    {
      label: "Excess Discount",
      value: analytics.totalExcess,
      color: "#ef4444",
      format: "money",
    },
  ];

  const outletRows = Object.keys(analytics.outletSalesRaw || {})
    .map((outlet) => {
      const sales = cleanNumber(analytics.outletSalesRaw[outlet]);
      const discount = cleanNumber(analytics.outletDiscountRaw[outlet]);
      const excess = cleanNumber(analytics.outletExcess[outlet]);
      const rate = discount
        ? Number(((excess / discount) * 100).toFixed(1))
        : 0;

      return {
        outlet,
        sales,
        discount,
        excess,
        rate,
      };
    })
    .sort((a, b) => b.sales - a.sales)
    .slice(0, 8);

  const monthRows = analytics.sortedMonths.slice(0, 10).map((month) => {
    const txns = analytics.monthMap[month] || [];

    const discount = txns.reduce(
      (sum, txn) => sum + cleanNumber(txn.total_allowed_discount),
      0,
    );

    const excess = txns.reduce(
      (sum, txn) => sum + cleanNumber(txn.total_excess_discount),
      0,
    );

    return {
      key: month,
      month,
      txns: txns.length,
      discount,
      excess,
    };
  });

  return (
    <section>


      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          icon="🚗"
          title={stage === "booking" ? "Total Bookings" : "Total Deliveries"}
          value={analytics.totalEntries}
          subtitle={`${analytics.okCases} OK · ${analytics.excessCases} Excess`}
          tone="indigo"
        />

        <KpiCard
          icon="💸"
          title="Actual Discount"
          value={formatMoney(analytics.totalActualDiscount)}
          subtitle={`Avg ${formatMoney(analytics.avgActualDiscount)} / transaction`}
          tone="green"
        />

        <KpiCard
          icon="✅"
          title="Allowable Discount"
          value={formatMoney(analytics.totalDiscount)}
          subtitle={`Avg ${formatMoney(analytics.avgDiscount)} / transaction`}
          tone="amber"
        />

        <KpiCard
          icon="⚠️"
          title="Excess Discount"
          value={formatMoney(analytics.totalExcess)}
          subtitle={`${analytics.compliancePct}% compliance`}
          tone={analytics.totalExcess > 0 ? "red" : "green"}
        />
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <DonutChart
          title={`${title} Compliance`}
          subtitle="OK vs Excess transactions"
          data={complianceData}
          centerLabel="Compliance"
          centerValue={`${analytics.compliancePct}%`}
        />

        <DonutChart
          title={`${title} Discount Mix`}
          subtitle="Allowed, actual and excess discount"
          data={discountData}
          centerLabel="Total"
          centerValue={formatMoney(
            analytics.totalDiscount +
            analytics.totalActualDiscount +
            analytics.totalExcess,
          )}
        />
      </div>

      {stage === "delivery" ? <></> : null}
    </section>
  );
};

const sortAnalysisCards = (items, sortBy, nameKey) => {
  const list = [...(items || [])];

  switch (sortBy) {
    case "alphabetical":
      return list.sort((a, b) =>
        String(a[nameKey] || "").localeCompare(String(b[nameKey] || "")),
      );

    case "bookings_high":
      return list.sort(
        (a, b) => cleanNumber(b.bookings) - cleanNumber(a.bookings),
      );

    case "bookings_low":
      return list.sort(
        (a, b) => cleanNumber(a.bookings) - cleanNumber(b.bookings),
      );

    case "deliveries_high":
      return list.sort(
        (a, b) => cleanNumber(b.deliveries) - cleanNumber(a.deliveries),
      );

    case "deliveries_low":
      return list.sort(
        (a, b) => cleanNumber(a.deliveries) - cleanNumber(b.deliveries),
      );

    case "excess_high":
      return list.sort(
        (a, b) => cleanNumber(b.excessDiscount) - cleanNumber(a.excessDiscount),
      );

    case "excess_low":
      return list.sort(
        (a, b) => cleanNumber(a.excessDiscount) - cleanNumber(b.excessDiscount),
      );

    default:
      return list;
  }
};

export default function DashboardPage() {
  const { user } = useAuth();

  const [dealerships, setDealerships] = useState([]);
  const [outlets, setOutlets] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [complaints, setComplaints] = useState([]);
  const [pendencies, setPendencies] = useState([]);

  const [filters, setFilters] = useState({
    dealership_id: "",
    outlet_id: "",
    month: "",
  });

  const [selectedCarName, setSelectedCarName] = useState(null);
  const [selectedShowroomKey, setSelectedShowroomKey] = useState(null);
  const [carSortBy, setCarSortBy] = useState("default");
  const [showroomSortBy, setShowroomSortBy] = useState("default");
  const [carComparisonOpen, setCarComparisonOpen] = useState(false);
  const [showroomComparisonOpen, setShowroomComparisonOpen] = useState(false);
  const [rtoModalMode, setRtoModalMode] = useState(null);
  const [selectedRtoKey, setSelectedRtoKey] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const userRole = getUserRole(user);
  const allowedOutletIds = getAllowedOutletIds(user);

  const visibleOutlets = useMemo(() => {
    if (userRole === "admin") return outlets;

    return outlets.filter((outlet) =>
      allowedOutletIds.includes(Number(outlet.id)),
    );
  }, [outlets, userRole, allowedOutletIds]);

  const visibleDealerships = useMemo(() => {
    if (userRole === "admin") return dealerships;

    const allowedDealershipIds = new Set(
      visibleOutlets.map((outlet) => Number(outlet.dealership_id)),
    );

    return dealerships.filter((dealer) =>
      allowedDealershipIds.has(Number(dealer.id)),
    );
  }, [dealerships, visibleOutlets, userRole]);

  const filteredOutletOptions = useMemo(() => {
    if (!filters.dealership_id) return visibleOutlets;

    return visibleOutlets.filter(
      (outlet) =>
        String(outlet.dealership_id) === String(filters.dealership_id),
    );
  }, [visibleOutlets, filters.dealership_id]);

  const monthOptions = useMemo(() => {
    const monthSet = new Set();

    transactions.forEach((txn) => {
      const bookingDate = txn.booking_date || "";
      if (bookingDate.length >= 7) monthSet.add(bookingDate.slice(0, 7));
    });

    return Array.from(monthSet).sort().reverse();
  }, [transactions]);

  const displayedTransactions = useMemo(() => {
    if (!filters.month) return transactions;

    return transactions.filter((txn) =>
      String(txn.booking_date || "").startsWith(filters.month),
    );
  }, [transactions, filters.month]);

  const carWiseAnalytics = useMemo(
    () => buildCarWiseAnalytics(displayedTransactions),
    [displayedTransactions],
  );

  const showroomWiseAnalytics = useMemo(
    () =>
      buildShowroomWiseAnalytics(displayedTransactions, filteredOutletOptions),
    [displayedTransactions, filteredOutletOptions],
  );
  const sortedCarWiseAnalytics = useMemo(
    () => sortAnalysisCards(carWiseAnalytics, carSortBy, "carName"),
    [carWiseAnalytics, carSortBy],
  );

  const sortedShowroomWiseAnalytics = useMemo(
    () =>
      sortAnalysisCards(showroomWiseAnalytics, showroomSortBy, "showroomName"),
    [showroomWiseAnalytics, showroomSortBy],
  );

  const rtoBookingAnalytics = useMemo(
    () => buildRtoBookingAnalytics(displayedTransactions),
    [displayedTransactions],
  );

  const complaintsAnalytics = useMemo(
    () => buildComplaintsAnalytics(complaints),
    [complaints],
  );

  const pendencyAnalytics = useMemo(
    () => buildPendencyAnalytics(pendencies),
    [pendencies],
  );

  const activeRtoSummary = useMemo(() => {
    if (!rtoModalMode) return null;

    return (
      rtoBookingAnalytics.summaryRows.find((row) => row.key === rtoModalMode) ||
      null
    );
  }, [rtoBookingAnalytics, rtoModalMode]);

  const rtoModalRows = activeRtoSummary?.rows || [];

  const rtoModalTitle = activeRtoSummary
    ? `${activeRtoSummary.label} - ${activeRtoSummary.rtoDisplay}`
    : "RTO Details";

  useEffect(() => {
    if (
      selectedCarName &&
      carWiseAnalytics.length &&
      !carWiseAnalytics.some((car) => car.carName === selectedCarName)
    ) {
      setSelectedCarName(null);
    }
  }, [carWiseAnalytics, selectedCarName]);

  const selectedCar = useMemo(() => {
    if (!selectedCarName) return null;

    return (
      carWiseAnalytics.find((car) => car.carName === selectedCarName) || null
    );
  }, [carWiseAnalytics, selectedCarName]);

  useEffect(() => {
    if (
      selectedShowroomKey &&
      showroomWiseAnalytics.length &&
      !showroomWiseAnalytics.some(
        (showroom) => String(showroom.key) === String(selectedShowroomKey),
      )
    ) {
      setSelectedShowroomKey(null);
    }
  }, [showroomWiseAnalytics, selectedShowroomKey]);

  const selectedShowroom = useMemo(() => {
    if (!selectedShowroomKey) return null;

    return (
      showroomWiseAnalytics.find(
        (showroom) => String(showroom.key) === String(selectedShowroomKey),
      ) || null
    );
  }, [showroomWiseAnalytics, selectedShowroomKey]);

  const bookingAnalytics = useMemo(
    () => computeAnalytics(displayedTransactions, "booking"),
    [displayedTransactions],
  );

  const deliveryAnalytics = useMemo(
    () => computeAnalytics(displayedTransactions, "delivery"),
    [displayedTransactions],
  );


  const visualReportData = useMemo(() => {
    const selectedDealer = filters.dealership_id
      ? visibleDealerships.find(
        (dealer) => String(dealer.id) === String(filters.dealership_id),
      )
      : null;

    const selectedOutlet = filters.outlet_id
      ? filteredOutletOptions.find(
        (outlet) => String(outlet.id) === String(filters.outlet_id),
      )
      : null;

    const scopeParts = [];

    if (selectedDealer?.name) scopeParts.push(selectedDealer.name);
    if (selectedOutlet?.name) scopeParts.push(selectedOutlet.name);
    if (filters.month) scopeParts.push(monthLabel(filters.month));

    const activeCars = carWiseAnalytics.filter(
      (car) => cleanNumber(car.totalTransactions) > 0,
    );

    const carsForReport = activeCars.length ? activeCars : carWiseAnalytics;

    const activeShowrooms = showroomWiseAnalytics.filter(
      (showroom) => cleanNumber(showroom.totalTransactions) > 0,
    );

    const showroomsForReport = activeShowrooms.length
      ? activeShowrooms
      : showroomWiseAnalytics;

    const monthlyMap = getMonthMap(displayedTransactions);

    const getTxnExcess = (txn) => {
      const isDelivery = txn.stage === "delivery";

      return isDelivery
        ? cleanNumber(txn.total_excess_discount)
        : cleanNumber(txn.excess_booking);
    };

    const trendRows = Object.entries(monthlyMap)
      .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
      .map(([month, txns]) => ({
        month: monthLabel(month),
        excessDiscount: txns.reduce((sum, txn) => sum + getTxnExcess(txn), 0),
      }));

    const previousTrendRow = trendRows.length > 1 ? trendRows[trendRows.length - 2] : null;
    const currentTrendRow = trendRows.length ? trendRows[trendRows.length - 1] : null;

    const exceptionRows = [
      ...bookingAnalytics.topExcessTransactions,
      ...deliveryAnalytics.topExcessTransactions,
    ]
      .map((txn) => {
        const isDelivery = txn.stage === "delivery";

        return {
          customer:
            txn.customer_name ||
            txn.customer ||
            txn.name ||
            txn.customerName ||
            "-",
          showroom:
            txn.outlet_name ||
            txn.showroom_name ||
            txn.outlet ||
            txn.showroom ||
            "-",
          model: normaliseCarName(txn),
          executive:
            txn.sales_executive_name ||
            txn.executive_name ||
            txn.executive ||
            txn.salesExecutiveName ||
            "-",
          excessDiscount: isDelivery
            ? cleanNumber(txn.total_excess_discount)
            : cleanNumber(txn.excess_booking),
        };
      })
      .sort((a, b) => cleanNumber(b.excessDiscount) - cleanNumber(a.excessDiscount))
      .slice(0, 25);

    return {
      scope: scopeParts.length ? scopeParts.join(" · ") : "All Accessible Data",

      summary: {
        totalBookings: bookingAnalytics.totalEntries,
        totalDeliveries: deliveryAnalytics.totalEntries,
        okBookings: bookingAnalytics.okCases,
        excessBookings: bookingAnalytics.excessCases,
        actualDiscount:
          bookingAnalytics.totalActualDiscount + deliveryAnalytics.totalActualDiscount,
        allowedDiscount:
          bookingAnalytics.totalDiscount + deliveryAnalytics.totalDiscount,
        excessDiscount:
          bookingAnalytics.totalExcess + deliveryAnalytics.totalExcess,
        compliancePercent: bookingAnalytics.compliancePct,
      },

      models: carsForReport.map((car) => ({
        name: car.carName,
        bookings: car.bookings,
        deliveries: car.deliveries,
        excessDiscount: car.excessDiscount,
      })),

      showrooms: showroomsForReport.map((showroom) => ({
        name: showroom.showroomName,
        bookings: showroom.bookings,
        deliveries: showroom.deliveries,
        excessDiscount: showroom.excessDiscount,
      })),

      cars: carsForReport.map((car) => ({
        name: car.carName,
        image: car.image,
        bookings: car.bookings,
        deliveries: car.deliveries,
        allowedDiscount: car.allowedDiscount,
        actualDiscount: car.actualDiscount,
        excessDiscount: car.excessDiscount,
        variants: Object.entries(car.variants || {})
          .sort((a, b) => cleanNumber(b[1]) - cleanNumber(a[1]))
          .map(([name, count]) => ({ name, count })),
        outlets: Object.entries(car.outlets || {})
          .sort((a, b) => cleanNumber(b[1]) - cleanNumber(a[1]))
          .map(([name, count]) => ({ name, count })),
      })),

      rto: rtoBookingAnalytics.summaryRows.map((row) => ({
        name: row.label,
        rto: row.rtoDisplay,
        bookings: row.bookings,
        share: row.share,
      })),

      trends: trendRows,

      trendSummary: {
        oldBookings: previousTrendRow ? 0 : 0,
        newBookings: bookingAnalytics.totalEntries,
        oldExcess: previousTrendRow?.excessDiscount || 0,
        newExcess:
          currentTrendRow?.excessDiscount ||
          bookingAnalytics.totalExcess + deliveryAnalytics.totalExcess,
      },

      complaints: {
        total: complaintsAnalytics.totalComplaints || 0,
        rows: complaintsAnalytics.rows || [],
      },

      pendencies: {
        total: pendencyAnalytics.totalFiles || 0,
        pending: pendencyAnalytics.totalPending || 0,
        completed: pendencyAnalytics.totalCompleted || 0,
        rows: pendencyAnalytics.rows || [],
      },

      exceptions: exceptionRows,
    };
  }, [
    bookingAnalytics,
    carWiseAnalytics,
    complaintsAnalytics,
    deliveryAnalytics,
    displayedTransactions,
    filteredOutletOptions,
    filters.dealership_id,
    filters.month,
    filters.outlet_id,
    pendencyAnalytics,
    rtoBookingAnalytics,
    showroomWiseAnalytics,
    visibleDealerships,
  ]);

  async function fetchMastersAndData(initial = false) {
    setLoading(true);
    setError("");

    try {
      const fetchPendencies = async () => {
        const endpoints = ["/pendencies", "/files", "/tasks"];

        for (const endpoint of endpoints) {
          try {
            const result = await api.get(endpoint);
            return result;
          } catch {
            // Try next endpoint.
          }
        }

        return [];
      };

      const [dealerResult, outletResult, complaintsResult, pendencyResult] =
        await Promise.all([
          api.get("/complaints/dealerships"),
          api.get("/outlets"),
          api.get("/complaints").catch(() => []),
          fetchPendencies(),
        ]);

      let dealerList = Array.isArray(dealerResult) ? dealerResult : [];
      let outletList = Array.isArray(outletResult) ? outletResult : [];
      let complaintList = Array.isArray(complaintsResult)
        ? complaintsResult
        : complaintsResult?.items ||
        complaintsResult?.data ||
        complaintsResult?.results ||
        [];
      let pendencyList = Array.isArray(pendencyResult)
        ? pendencyResult
        : pendencyResult?.items ||
        pendencyResult?.data ||
        pendencyResult?.results ||
        [];

      if (userRole !== "admin") {
        outletList = outletList.filter((outlet) =>
          allowedOutletIds.includes(Number(outlet.id)),
        );

        const allowedDealerIds = new Set(
          outletList.map((outlet) => Number(outlet.dealership_id)),
        );

        dealerList = dealerList.filter((dealer) =>
          allowedDealerIds.has(Number(dealer.id)),
        );

        complaintList = complaintList.filter((complaint) => {
          const outletId =
            complaint.outlet_id ||
            complaint.outletId ||
            complaint.showroom_id ||
            complaint.showroomId;

          return !outletId || allowedOutletIds.includes(Number(outletId));
        });

        pendencyList = pendencyList.filter((pendency) => {
          const outletId =
            pendency.outlet_id ||
            pendency.outletId ||
            pendency.showroom_id ||
            pendency.showroomId;

          return !outletId || allowedOutletIds.includes(Number(outletId));
        });
      }

      setDealerships(dealerList);
      setOutlets(outletList);
      setComplaints(complaintList);
      setPendencies(pendencyList);

      const defaultDealership =
        userRole !== "admin" && dealerList.length === 1
          ? String(dealerList[0].id)
          : "";

      const nextFilters = {
        dealership_id: initial ? defaultDealership : filters.dealership_id,
        outlet_id: filters.outlet_id,
        month: filters.month,
      };

      setFilters(nextFilters);

      await fetchTransactions(nextFilters);
    } catch (e) {
      setError(e.message || "Unable to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }

  async function fetchTransactions(nextFilters = filters) {
    const params = {};

    if (nextFilters.dealership_id) {
      params.dealership_id = nextFilters.dealership_id;
    }

    if (nextFilters.outlet_id) {
      params.outlet_id = nextFilters.outlet_id;
    }

    const result = await api.get("/dashboard-data", params);
    setTransactions(Array.isArray(result) ? result : []);
  }

  async function handleFilterChange(next) {
    const nextFilters = {
      ...filters,
      ...next,
    };

    if ("dealership_id" in next) {
      nextFilters.outlet_id = "";
    }

    setFilters(nextFilters);
    setLoading(true);
    setError("");

    try {
      await fetchTransactions(nextFilters);
    } catch (e) {
      setError(e.message || "Unable to apply filters.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchMastersAndData(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Executive overview of audit transactions, discounts, compliance and outlet performance."
        actions={
          <GenerateReportButton
            reportTitle="Automobile Sales Audit MIS Report"
            reportData={visualReportData}
          />
        }
      />

      <Alert type="error">{error}</Alert>

      <div className="dashboard-hero card mb-4 grid gap-4 p-4 md:grid-cols-3">
        <Field label="Dealership">
          <Select
            value={filters.dealership_id}
            onChange={(e) =>
              handleFilterChange({
                dealership_id: e.target.value,
                outlet_id: "",
              })
            }
          >
            {userRole === "admin" ? (
              <option value="">All Dealerships</option>
            ) : null}

            {visibleDealerships.map((dealer) => (
              <option key={dealer.id} value={dealer.id}>
                {dealer.name}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Showroom">
          <Select
            value={filters.outlet_id}
            onChange={(e) =>
              handleFilterChange({
                outlet_id: e.target.value,
              })
            }
          >
            <option value="">All Showrooms</option>

            {filteredOutletOptions.map((outlet) => (
              <option key={outlet.id} value={outlet.id}>
                {outlet.name}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Month">
          <Select
            value={filters.month}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                month: e.target.value,
              }))
            }
          >
            <option value="">All Months</option>

            {monthOptions.map((month) => (
              <option key={month} value={month}>
                {monthLabel(month)}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      {loading ? (
        <Loader />
      ) : (
        <div className="space-y-5">
          <CarComparisonModal
            open={carComparisonOpen}
            onClose={() => setCarComparisonOpen(false)}
            cars={carWiseAnalytics}
            showrooms={showroomWiseAnalytics}
            transactions={displayedTransactions}
          />

          <CarCarousel
            cars={sortedCarWiseAnalytics}
            selectedCarName={selectedCar?.carName}
            onCompare={() => setCarComparisonOpen(true)}
            sortBy={carSortBy}
            onSortChange={setCarSortBy}
            onSelect={(carName) => {
              setSelectedCarName((current) =>
                current === carName ? null : carName,
              );
            }}
          />

          {selectedCar ? <SelectedCarPanel car={selectedCar} /> : null}

          <ShowroomComparisonModal
            open={showroomComparisonOpen}
            onClose={() => setShowroomComparisonOpen(false)}
            showrooms={showroomWiseAnalytics}
            transactions={displayedTransactions}
          />

          <ShowroomCarousel
            showrooms={sortedShowroomWiseAnalytics}
            selectedShowroomKey={selectedShowroom?.key}
            onCompare={() => setShowroomComparisonOpen(true)}
            sortBy={showroomSortBy}
            onSortChange={setShowroomSortBy}
            onSelect={(showroomKey) => {
              setSelectedShowroomKey((current) =>
                String(current) === String(showroomKey) ? null : showroomKey,
              );
            }}
          />
          {selectedShowroom ? (
            <SelectedShowroomPanel showroom={selectedShowroom} />
          ) : null}

          <RtoCarousel
            analytics={rtoBookingAnalytics}
            selectedRtoKey={selectedRtoKey}
            onSelect={(rtoKey) => {
              setSelectedRtoKey((current) =>
                String(current) === String(rtoKey) ? null : rtoKey,
              );

              setRtoModalMode(rtoKey);
            }}
          />

          <RtoDetailsModal
            open={Boolean(rtoModalMode)}
            onClose={() => setRtoModalMode(null)}
            title={rtoModalTitle}
            rows={rtoModalRows}
            totalBookings={rtoBookingAnalytics.totalBookings}
          />

          <ComplaintsInformationTable analytics={complaintsAnalytics} />

          <PendencyInformationTable analytics={pendencyAnalytics} />

          <AnalyticsPanel
            title="Bookings"
            stage="booking"
            analytics={bookingAnalytics}
            userRole={userRole}
          />

          <AnalyticsPanel
            title="Deliveries"
            stage="delivery"
            analytics={deliveryAnalytics}
            userRole={userRole}
          />
        </div>
      )}
    </>
  );
}
