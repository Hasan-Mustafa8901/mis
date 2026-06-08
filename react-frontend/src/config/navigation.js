import {
  BarChart3,
  ClipboardList,
  FileSpreadsheet,
  Home,
  MessageSquarePlus,
  Settings,
  ShieldCheck,
  Upload,
  Users,
} from 'lucide-react';

export const NAV_ITEMS = [
  { label: 'Dashboard', path: '/', icon: Home },
  { label: 'Daily Reporting', path: '/daily-reporting', icon: BarChart3 },
  { label: 'Complaint Form', path: '/complaints/form', icon: MessageSquarePlus },
  { label: 'Booking', path: '/booking-mis', icon: ClipboardList },
  { label: 'Delivery', path: '/delivery-mis', icon: ShieldCheck },
  { label: 'Complaint Register', path: '/complaints/register', icon: Users },
  { label: 'Uploads', path: '/ebd-upload', icon: Upload },
  { label: 'Price List', path: '/price-list', icon: FileSpreadsheet },
  { label: 'Settings', path: '/settings', icon: Settings },
];

export const STAGES = [
  { label: 'Booking', value: 'booking' },
  { label: 'Delivery', value: 'delivery' },
];
