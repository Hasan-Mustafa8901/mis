import { Download, LogOut, Menu, Moon, Sun, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { NAV_ITEMS } from "../config/navigation";
import { useAuth } from "../context/AuthContext";
import { authStorage } from "../lib/storage";
import { hasPageAccess } from "../utils/auth";

const ACTIVITY_LOG_KEY = "audit_mis_activity_logs";
const MAX_ACTIVITY_LOGS = 1000;

function isActive(path) {
  return window.location.pathname === path;
}

function getStoredActivityLogs() {
  try {
    const raw = localStorage.getItem(ACTIVITY_LOG_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveActivityLogs(logs) {
  try {
    localStorage.setItem(
      ACTIVITY_LOG_KEY,
      JSON.stringify(logs.slice(-MAX_ACTIVITY_LOGS))
    );
  } catch (error) {
    console.warn("Unable to save activity logs:", error);
  }
}

function formatRole(role) {
  return String(role || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatConsoleTimestamp(date = new Date()) {
  const pad = (value, size = 2) => String(value).padStart(size, "0");

  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hour = pad(date.getHours());
  const minute = pad(date.getMinutes());
  const second = pad(date.getSeconds());
  const millisecond = pad(date.getMilliseconds(), 3);

  return `${year}-${month}-${day} ${hour}:${minute}:${second},${millisecond}`;
}

function getPageLabel(path) {
  const item = NAV_ITEMS.find((navItem) => navItem.path === path);
  return item?.label || path || "Unknown Page";
}

function getReadableActivity(action, details = {}) {
  const map = {
    PAGE_VIEW: `Accessing ${details.path || window.location.pathname} page (month: ${
      details.month || "None"
    })`,
    NAVIGATION_CLICK: `Clicked navigation: ${details.label || details.path || ""}`,
    BOTTOM_NAVIGATION_CLICK: `Clicked bottom navigation: ${
      details.label || details.path || ""
    }`,
    THEME_CHANGED: `Theme changed to ${details.to || ""}`,
    MOBILE_MENU_OPENED: "Mobile menu opened",
    LOGOUT_CLICKED: "Logout clicked",
    ACTIVITY_LOGS_DOWNLOADED: "Downloaded activity logs",
    FRONTEND_EXCEPTION: `Exception: ${details.message || "Unknown error"}`,
    FRONTEND_UNHANDLED_REJECTION: `Unhandled promise rejection: ${
      details.message || "Unknown error"
    }`,
  };

  return map[action] || String(action || "").replace(/_/g, " ");
}

function toSimpleLogEntry(log) {
  if (log?.time && log?.name && log?.role && log?.activity) {
    return {
      time: log.time,
      name: log.name,
      role: log.role,
      activity: log.activity,
    };
  }

  return {
    time: log?.time || log?.timestamp || new Date().toISOString(),
    name: log?.name || log?.user?.name || "User",
    role: formatRole(log?.role || log?.user?.role || ""),
    activity:
      log?.activity ||
      getReadableActivity(log?.action, log?.details || {}) ||
      "Activity recorded",
  };
}

function isDuplicateRecentLog(logEntry) {
  const logs = getStoredActivityLogs().map(toSimpleLogEntry);
  const lastLog = logs[logs.length - 1];

  if (!lastLog) return false;

  const sameUser = lastLog.name === logEntry.name && lastLog.role === logEntry.role;
  const sameActivity = lastLog.activity === logEntry.activity;

  if (!sameUser || !sameActivity) return false;

  const lastTime = new Date(lastLog.time).getTime();
  const currentTime = new Date(logEntry.time).getTime();

  if (Number.isNaN(lastTime) || Number.isNaN(currentTime)) return false;

  return Math.abs(currentTime - lastTime) < 1200;
}

function writeActivityLog(action, details = {}, user = {}, auth = {}) {
  const now = new Date();

  const userName = user?.name || auth?.name || "User";
  const role = formatRole(user?.role || auth?.role || "");
  const activity = getReadableActivity(action, details);

  const logEntry = {
    time: now.toISOString(),
    name: userName,
    role,
    activity,
  };

  if (isDuplicateRecentLog(logEntry)) return;

  const isErrorAction =
    String(action || "").includes("EXCEPTION") ||
    String(action || "").includes("REJECTION");

  const level = isErrorAction ? "ERROR" : "INFO";

  const consoleLine = `${formatConsoleTimestamp(now)} [${level}] frontend - ${activity} for user: ${userName}`;

  if (isErrorAction) {
    console.error(consoleLine);

    if (details?.stack || details?.source || details?.line || details?.column) {
      console.error("Exception details:", details);
    }
  } else {
    console.info(consoleLine);
  }

  const existingLogs = getStoredActivityLogs().map(toSimpleLogEntry);
  saveActivityLogs([...existingLogs, logEntry]);

  window.dispatchEvent(
    new CustomEvent("audit-mis-log-created", { detail: logEntry })
  );
}

function downloadActivityLogs() {
  const logs = getStoredActivityLogs().map(toSimpleLogEntry);

  const fileContent = JSON.stringify(logs, null, 2);

  const blob = new Blob([fileContent], {
    type: "application/json;charset=utf-8",
  });

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");

  anchor.href = url;
  anchor.download = `audit-mis-activity-logs-${new Date()
    .toISOString()
    .slice(0, 10)}.json`;

  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);

  URL.revokeObjectURL(url);
}

function applyTheme(nextTheme) {
  const html = document.documentElement;
  const body = document.body;

  html.classList.remove("light", "dark");
  body.classList.remove("light", "dark");

  if (nextTheme === "dark") {
    html.classList.add("dark");
    body.classList.add("dark");
  } else {
    html.classList.add("light");
    body.classList.add("light");
  }

  localStorage.setItem("audit_mis_theme", nextTheme);
}

function getInitialTheme() {
  const saved = localStorage.getItem("audit_mis_theme");

  if (saved === "dark") return "dark";
  if (saved === "light") return "light";

  return "light";
}

const NAV_SECTION_RULES = [
  {
    title: "Client Access",
    paths: new Set(["/", "/daily-reporting", "/complaints/form"]),
  },
  {
    title: "Audit Assistant Access",
    paths: new Set([
      "/booking-mis",
      "/delivery-mis",
      "/complaints/register",
      "/ebd-upload",
      "/price-list",
    ]),
  },
  {
    title: "Admin Access",
    paths: new Set(["/settings"]),
  },
];

function getNavSections(items) {
  const usedPaths = new Set();

  const sections = NAV_SECTION_RULES.map((section) => {
    const sectionItems = items.filter((item) => section.paths.has(item.path));

    sectionItems.forEach((item) => usedPaths.add(item.path));

    return {
      title: section.title,
      items: sectionItems,
    };
  }).filter((section) => section.items.length > 0);

  const otherItems = items.filter((item) => !usedPaths.has(item.path));

  if (otherItems.length) {
    sections.push({
      title: "Other Access",
      items: otherItems,
    });
  }

  return sections;
}

function NavLink({ item, onClick, onLog }) {
  const Icon = item.icon;
  const active = isActive(item.path);

  return (
    <a
      key={item.path}
      href={item.path}
      onClick={() => {
        onLog?.("NAVIGATION_CLICK", {
          label: item.label,
          path: item.path,
          from: window.location.pathname,
        });

        onClick?.();
      }}
      className={`group flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold transition-all duration-200 ${
        active
          ? "bg-amber-50 text-slate-950 ring-1 ring-amber-200 shadow-sm dark:bg-amber-400/10 dark:text-amber-200 dark:ring-amber-400/30"
          : "text-slate-600 hover:bg-slate-50 hover:text-slate-950 dark:text-slate-400 dark:hover:bg-slate-900 dark:hover:text-white"
      }`}
    >
      <span
        className={`flex h-9 w-9 items-center justify-center rounded-xl transition ${
          active
            ? "bg-amber-200 text-slate-950 dark:bg-amber-400/20 dark:text-amber-200"
            : "bg-slate-100 text-slate-500 group-hover:bg-white group-hover:text-slate-900 dark:bg-slate-900 dark:text-slate-400 dark:group-hover:bg-slate-800 dark:group-hover:text-white"
        }`}
      >
        <Icon size={18} />
      </span>

      <span>{item.label}</span>
    </a>
  );
}

function NavSection({ title, items, onClick, onLog }) {
  if (!items.length) return null;

  return (
    <div className="mt-5 first:mt-0">
      <div className="mb-3 flex items-center gap-3 px-2">
        <span className="shrink-0 text-[10px] font-black uppercase tracking-[0.20em] text-slate-400 dark:text-slate-500">
          {title}
        </span>
        <div className="h-px flex-1 bg-slate-300 dark:bg-slate-700/70" />
      </div>

      <div className="space-y-1">
        {items.map((item) => (
          <NavLink
            key={item.path}
            item={item}
            onClick={onClick}
            onLog={onLog}
          />
        ))}
      </div>
    </div>
  );
}

function normalizeAccessText(value) {
  return JSON.stringify(value || {})
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");
}

function getAccessibleDealerLogos(auth, user) {
  const role = String(user?.role || auth?.role || "").toLowerCase();

  const isAdmin =
    role === "admin" ||
    role === "super_admin" ||
    role.includes("admin");

  const userName = String(user?.name || auth?.name || "").toLowerCase();

  const allowedGroups =
    user?.allowed_groups ||
    user?.allowedGroups ||
    auth?.allowed_groups ||
    auth?.allowedGroups ||
    [];

  const allowedDealerships =
    user?.allowed_dealerships ||
    user?.allowedDealerships ||
    auth?.allowed_dealerships ||
    auth?.allowedDealerships ||
    [];

  const allowedDealershipNames =
    user?.allowed_dealership_names ||
    user?.allowedDealershipNames ||
    auth?.allowed_dealership_names ||
    auth?.allowedDealershipNames ||
    [];

  const allowedOutletNames =
    user?.allowed_outlet_names ||
    user?.allowedOutletNames ||
    auth?.allowed_outlet_names ||
    auth?.allowedOutletNames ||
    [];

  const combinedText = normalizeAccessText({
    role,
    userName,
    allowedGroups,
    allowedDealerships,
    allowedDealershipNames,
    allowedOutletNames,
    user,
    auth,
  });

  const hasBR =
    isAdmin ||
    /\bbr\b/i.test(userName) ||
    /\bbr\b/i.test(combinedText) ||
    combinedText.includes("br group") ||
    combinedText.includes("beeaar") ||
    combinedText.includes("beeaar tata") ||
    combinedText.includes("br gc");

  const hasSRM =
    isAdmin ||
    /\bsrm\b/i.test(userName) ||
    /\bsrm\b/i.test(combinedText) ||
    combinedText.includes("srm group") ||
    combinedText.includes("srm motors");

  const logos = [];

  if (hasBR) {
    logos.push({
      key: "br",
      name: "BR Group",
      src: "/brand/br-logo.png",
      fallback: "BR",
    });
  }

  if (hasSRM) {
    logos.push({
      key: "srm",
      name: "SRM Group",
      src: "/brand/srm-logo.png",
      fallback: "SRM",
    });
  }

  return logos;
}

function BrandLogoBox({ logo, wide = false }) {
  return (
    <div
      className={`flex ${
        wide ? "h-16 flex-1" : "h-16 w-16 shrink-0"
      } items-center justify-center overflow-hidden rounded-2xl bg-white p-2 shadow-sm`}
    >
      <img
        src={logo.src}
        alt={logo.name}
        className="h-full w-full object-contain"
        onError={(e) => {
          e.currentTarget.style.display = "none";

          const fallback = e.currentTarget.nextElementSibling;
          if (fallback) fallback.style.display = "flex";
        }}
      />

      <span
        className="hidden h-full w-full items-center justify-center rounded-xl bg-amber-300 text-xs font-black uppercase tracking-widest text-slate-950"
        style={{ display: "none" }}
      >
        {logo.fallback}
      </span>
    </div>
  );
}

function BrandCard({ auth, user }) {
  const dealerLogos = getAccessibleDealerLogos(auth, user);

  const role = String(user?.role || auth?.role || "").toLowerCase();

  const isAdmin =
    role === "admin" ||
    role === "super_admin" ||
    role.includes("admin");

  const logosToShow = dealerLogos.length
    ? dealerLogos
    : isAdmin
      ? [
          {
            key: "br",
            name: "BR Group",
            src: "/brand/br-logo.png",
            fallback: "BR",
          },
          {
            key: "srm",
            name: "SRM Group",
            src: "/brand/srm-logo.png",
            fallback: "SRM",
          },
        ]
      : [];

  return (
    <div className="mb-6 overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-slate-900 to-amber-950 p-5 text-white shadow-xl">
      <div className="mb-5 rounded-2xl border border-white/10 bg-white/5 p-3">
        <div className="flex items-center justify-between gap-3">
          <BrandLogoBox
            logo={{
              key: "firm",
              name: "Asija & Associates",
              src: "/brand/firm-logo.png",
              fallback: "A",
            }}
          />

          <div className="h-14 w-px bg-white/20" />

          {logosToShow.length ? (
            <div
              className={`grid flex-1 gap-2 ${
                logosToShow.length === 1 ? "grid-cols-1" : "grid-cols-2"
              }`}
            >
              {logosToShow.slice(0, 2).map((logo) => (
                <BrandLogoBox key={logo.key} logo={logo} wide />
              ))}
            </div>
          ) : (
            <div className="flex h-16 flex-1 items-center justify-center rounded-2xl bg-white p-2 shadow-sm">
              <span className="text-xs font-black uppercase tracking-widest text-slate-950">
                Dealer
              </span>
            </div>
          )}
        </div>
      </div>

      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-amber-300">
        Audit MIS
      </p>

      <h1 className="mt-2 text-xl font-bold leading-tight">
        Automobile Sales Audit
      </h1>

      <p className="mt-2 text-xs font-semibold tracking-wide text-slate-300">
        ASIJA & ASSOCIATES
      </p>
    </div>
  );
}

export default function AppLayout({ children }) {
  const { user, signOut } = useAuth();

  const [theme, setTheme] = useState(getInitialTheme);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const auth = authStorage.get();

  const previousPathRef = useRef("");

  const visibleNavItems = useMemo(() => {
    return NAV_ITEMS.filter((item) => hasPageAccess(auth, item.path));
  }, [auth]);

  const navSections = useMemo(() => {
    return getNavSections(visibleNavItems);
  }, [visibleNavItems]);

  const role = String(user?.role || auth?.role || "").toLowerCase();

  const isAdmin =
    role === "admin" ||
    role === "super_admin" ||
    role.includes("admin");

  const log = (action, details = {}) => {
    writeActivityLog(action, details, user, auth);
  };

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    function handleWindowError(event) {
      log("FRONTEND_EXCEPTION", {
        message: event.message,
        source: event.filename,
        line: event.lineno,
        column: event.colno,
        stack: event.error?.stack || "",
      });
    }

    function handleUnhandledRejection(event) {
      const reason = event.reason;

      log("FRONTEND_UNHANDLED_REJECTION", {
        message:
          reason?.message || String(reason || "Unhandled promise rejection"),
        stack: reason?.stack || "",
      });
    }

    window.addEventListener("error", handleWindowError);
    window.addEventListener("unhandledrejection", handleUnhandledRejection);

    return () => {
      window.removeEventListener("error", handleWindowError);
      window.removeEventListener(
        "unhandledrejection",
        handleUnhandledRejection
      );
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const currentPath = `${window.location.pathname}${window.location.search}`;

    if (previousPathRef.current !== currentPath) {
      const searchParams = new URLSearchParams(window.location.search);

      log("PAGE_VIEW", {
        path: window.location.pathname,
        search: window.location.search,
        month: searchParams.get("month") || null,
      });

      previousPathRef.current = currentPath;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [children]);

  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = "hidden";
      log("MOBILE_MENU_OPENED");
    } else {
      document.body.style.overflow = "";
    }

    return () => {
      document.body.style.overflow = "";
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mobileMenuOpen]);

  const isDark = theme === "dark";

  const toggleTheme = () => {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";

      log("THEME_CHANGED", {
        from: current,
        to: next,
      });

      applyTheme(next);
      return next;
    });
  };

  const closeMobileMenu = () => {
    setMobileMenuOpen(false);
  };

  const handleDownloadLogs = () => {
    log("ACTIVITY_LOGS_DOWNLOADED", {
      totalLogs: getStoredActivityLogs().length,
    });

    setTimeout(() => {
      downloadActivityLogs();
    }, 100);
  };

  const handleSignOut = () => {
    log("LOGOUT_CLICKED", {
      name: user?.name || auth?.name,
      role: user?.role || auth?.role,
    });

    signOut();
  };

  const bottomNavItems = visibleNavItems.slice(0, 5);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950 transition-colors duration-300 dark:bg-[#020617] dark:text-slate-100">
      {/* Desktop Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-72 border-r border-slate-200 bg-white shadow-sm lg:block dark:border-slate-800 dark:bg-slate-950">
        <div className="flex h-full flex-col p-4">
          <BrandCard auth={auth} user={user} />

          <nav className="sidebar-scroll -mr-2 flex-1 overflow-y-auto pr-2 pb-4">
            {navSections.map((section) => (
              <NavSection
                key={section.title}
                title={section.title}
                items={section.items}
                onLog={log}
              />
            ))}
          </nav>
        </div>
      </aside>

      {/* Mobile Drawer Overlay */}
      {mobileMenuOpen ? (
        <div
          className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-sm lg:hidden"
          onClick={closeMobileMenu}
        />
      ) : null}

      {/* Mobile Drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-[60] w-[84%] max-w-[340px] border-r border-slate-200 bg-white shadow-2xl transition-transform duration-300 lg:hidden dark:border-slate-800 dark:bg-slate-950 ${
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-full flex-col p-4">
          <div className="mb-4 flex items-center justify-between">
            <p className="text-xs font-black uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
              Menu
            </p>

            <button
              type="button"
              onClick={closeMobileMenu}
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
            >
              <X size={18} />
            </button>
          </div>

          <BrandCard auth={auth} user={user} />

          <nav className="sidebar-scroll -mr-2 flex-1 overflow-y-auto pr-2 pb-24">
            {navSections.map((section) => (
              <NavSection
                key={section.title}
                title={section.title}
                items={section.items}
                onClick={closeMobileMenu}
                onLog={log}
              />
            ))}
          </nav>
        </div>
      </aside>

      <main className="min-h-screen bg-slate-50 transition-colors duration-300 lg:pl-72 dark:bg-[#020617]">
        {/* Header */}
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur-xl transition-colors dark:border-slate-800 dark:bg-slate-950/90">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(true)}
                className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 lg:hidden dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
              >
                <Menu size={20} />
              </button>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Logged in as
                </p>

                <p className="text-sm font-bold text-slate-950 dark:text-white">
                  {user?.name || "User"}{" "}
                  <span className="font-medium text-slate-500 dark:text-slate-400">
                    ({String(user?.role || "role").replace(/_/g, " ")})
                  </span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {isAdmin ? (
                <button
                  type="button"
                  onClick={handleDownloadLogs}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                  title="Download local activity logs"
                >
                  <Download size={16} />
                  <span className="hidden sm:inline">Logs</span>
                </button>
              ) : null}

              <button
                type="button"
                onClick={toggleTheme}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                {isDark ? <Sun size={16} /> : <Moon size={16} />}
                <span className="hidden sm:inline">
                  {isDark ? "Light" : "Dark"}
                </span>
              </button>

              <button onClick={handleSignOut} className="btn-secondary">
                <LogOut size={16} />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </header>

        {/* Page Body */}
        <div className="min-h-screen bg-slate-50 px-4 py-4 pb-24 transition-colors duration-300 md:px-6 md:py-5 lg:pb-8 dark:bg-[#020617]">
          {children}
        </div>
      </main>

      {/* Mobile Bottom Navigation */}
      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/95 px-2 py-2 shadow-2xl backdrop-blur-xl lg:hidden dark:border-slate-800 dark:bg-slate-950/95">
        <div className="grid grid-cols-5 gap-1">
          {bottomNavItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);

            return (
              <a
                key={item.path}
                href={item.path}
                onClick={() =>
                  log("BOTTOM_NAVIGATION_CLICK", {
                    label: item.label,
                    path: item.path,
                    from: window.location.pathname,
                  })
                }
                className={`flex flex-col items-center justify-center rounded-2xl px-2 py-2 text-[10px] font-black transition ${
                  active
                    ? "bg-amber-50 text-amber-700 dark:bg-amber-400/10 dark:text-amber-300"
                    : "text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-900"
                }`}
              >
                <Icon size={18} />
                <span className="mt-1 max-w-full truncate">
                  {item.label.length > 11
                    ? `${item.label.slice(0, 10)}…`
                    : item.label}
                </span>
              </a>
            );
          })}
        </div>
      </nav>
    </div>
  );
}