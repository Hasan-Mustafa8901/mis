export const PAGE_ACCESS_STORAGE_KEY = 'audit_mis_page_access';

export const PAGE_ACCESS_ITEMS = [
  {
    label: 'Dashboard',
    path: '/',
    roles: ['admin', 'client', 'audit_assistant'],
  },
  {
    label: 'Booking MIS',
    path: '/booking-mis',
    roles: ['admin', 'audit_assistant'],
  },
  {
    label: 'Delivery MIS',
    path: '/delivery-mis',
    roles: ['admin', 'audit_assistant'],
  },
  {
    label: 'Daily Reporting',
    path: '/daily-reporting',
    roles: ['admin', 'client', 'audit_assistant'],
  },
  {
    label: 'Complaints Redirect',
    path: '/complaints',
    roles: ['admin', 'client', 'audit_assistant'],
  },
  {
    label: 'Raise Complaint',
    path: '/complaints/form',
    roles: ['admin', 'client', 'audit_assistant'],
  },
  {
    label: 'Complaint Register',
    path: '/complaints/register',
    roles: ['admin', 'audit_assistant'],
  },
  {
    label: 'EBD Upload',
    path: '/ebd-upload',
    roles: ['admin', 'audit_assistant'],
  },
  {
    label: 'Price List',
    path: '/price-list',
    roles: ['admin'],
  },
  {
    label: 'Settings',
    path: '/settings',
    roles: ['admin'],
  },
  {
    label: 'New Entry Form',
    path: '/form',
    roles: ['admin', 'audit_assistant'],
  },
];

export const PAGE_ROLE_OPTIONS = [
  { label: 'Admin', value: 'admin' },
  { label: 'Client', value: 'client' },
  { label: 'Audit Assistant', value: 'audit_assistant' },
];

export function getDefaultPageAccess() {
  return PAGE_ACCESS_ITEMS.reduce((acc, item) => {
    acc[item.path] = item.roles;
    return acc;
  }, {});
}

export function getStoredPageAccess() {
  try {
    const stored = JSON.parse(
      localStorage.getItem(PAGE_ACCESS_STORAGE_KEY) || 'null'
    );

    if (!stored || typeof stored !== 'object') {
      return getDefaultPageAccess();
    }

    return {
      ...getDefaultPageAccess(),
      ...stored,
    };
  } catch {
    return getDefaultPageAccess();
  }
}

export function saveStoredPageAccess(access) {
  localStorage.setItem(PAGE_ACCESS_STORAGE_KEY, JSON.stringify(access));
}
