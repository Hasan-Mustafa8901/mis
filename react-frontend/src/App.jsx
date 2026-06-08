import TransactionFormPage from './pages/TransactionForm';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import MisPage from './pages/MisPage';
import DailyReportingPage from './pages/DailyReportingPage';
import SettingsPage from './pages/SettingsPage';
import { EbdUploadPage, PriceListPage } from './pages/UploadPages';
import AppLayout from './layouts/AppLayout';
import { useAuth } from './context/AuthContext';
import { MasterDataProvider } from './context/MasterDataContext';
import RequireRoles from './components/RequireRoles';
import { authStorage } from './lib/storage';
import { getUserRoles, tokenIsValid } from './utils/auth';
import ComplaintFormPage from './pages/ComplaintFormPage';
import ComplaintRegisterPage from './pages/ComplaintRegisterPage';

function redirectTo(path) {
  if (window.location.pathname !== path) {
    window.history.replaceState({}, '', path);
  }
}

function Router() {
  const path = window.location.pathname;
  const auth = authStorage.get();
  const roles = getUserRoles(auth);
  const userRole = roles[0] || '';

  if (path === '/login') {
    return <DashboardPage />;
  }

  if (path === '/booking-mis') {
    return (
      <RequireRoles path="/booking-mis">
        <MisPage stage="booking" />
      </RequireRoles>
    );
  }

  if (path === '/delivery-mis') {
    return (
      <RequireRoles path="/delivery-mis">
        <MisPage stage="delivery" />
      </RequireRoles>
    );
  }

  if (path === '/daily-reporting') {
    return (
      <RequireRoles path="/daily-reporting">
        <DailyReportingPage />
      </RequireRoles>
    );
  }

  if (path === '/complaints') {
    const target = userRole === 'client' ? '/complaints/form' : '/complaints/register';
    redirectTo(target);

    return userRole === 'client' ? (
      <RequireRoles path="/complaints/form">
        <ComplaintFormPage />
      </RequireRoles>
    ) : (
      <RequireRoles path="/complaints/register">
        <ComplaintRegisterPage />
      </RequireRoles>
    );
  }

  if (path === '/complaints/form') {
    return (
      <RequireRoles path="/complaints/form">
        <ComplaintFormPage />
      </RequireRoles>
    );
  }

  if (path === '/complaints/register') {
    return (
      <RequireRoles path="/complaints/register">
        <ComplaintRegisterPage />
      </RequireRoles>
    );
  }

  if (path === '/ebd-upload') {
    return (
      <RequireRoles path="/ebd-upload">
        <EbdUploadPage />
      </RequireRoles>
    );
  }

  if (path === '/price-list') {
    return (
      <RequireRoles path="/price-list">
        <PriceListPage />
      </RequireRoles>
    );
  }

  if (path === '/settings') {
    return (
      <RequireRoles path="/settings">
        <SettingsPage />
      </RequireRoles>
    );
  }

  if (path === '/form') {
    return (
      <RequireRoles path="/form">
        <TransactionFormPage />
      </RequireRoles>
    );
  }

  return (
    <RequireRoles path="/">
      <DashboardPage />
    </RequireRoles>
  );
}

export default function App() {
  const { isAuthenticated } = useAuth();

  const auth = authStorage.get();
  const token = auth?.access_token || auth?.token;
  const validToken = tokenIsValid(token);

  const shouldShowLogin = !isAuthenticated || !token || !validToken;

  if (shouldShowLogin) {
    if (auth) {
      authStorage.clear();
    }

    if (window.location.pathname !== '/login') {
      window.history.replaceState({}, '', '/login');
    }

    return <LoginPage />;
  }

  if (window.location.pathname === '/login') {
    window.history.replaceState({}, '', '/');
  }

  return (
    <MasterDataProvider>
      <AppLayout>
        <Router />
      </AppLayout>
    </MasterDataProvider>
  );
}
