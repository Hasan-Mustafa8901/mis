import { RefreshCw, Save, Trash2, UploadCloud, UserPlus } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import Alert from '../components/Alert';
import Button from '../components/Button';
import Field, { Input, Select } from '../components/Field';
import Loader from '../components/Loader';
import PageHeader from '../components/PageHeader';
import {
  PAGE_ACCESS_ITEMS,
  PAGE_ROLE_OPTIONS,
  getStoredPageAccess,
  saveStoredPageAccess,
} from '../config/pageAccess';
import { api } from '../services/apiClient';

const today = new Date().toISOString().slice(0, 10);

const ROLE_OPTIONS = [
  { label: 'Admin', value: 'admin' },
  { label: 'Client', value: 'client' },
  { label: 'Audit Assistant', value: 'audit_assistant' },
];

const getDisplayRole = (role) => {
  return String(role || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

const getIdByName = (items, name) => {
  const item = (items || []).find((x) => x.name === name);
  return item?.id || null;
};

const SectionCard = ({ title, subtitle, icon, children, className = '' }) => {
  return (
    <section className={`card p-6 ${className}`}>
      <div className="mb-5 flex items-start justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-xl dark:bg-slate-900">
            {icon}
          </div>

          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              {title}
            </h2>

            {subtitle ? (
              <p className="mt-1 text-sm font-medium text-slate-500 dark:text-slate-400">
                {subtitle}
              </p>
            ) : null}
          </div>
        </div>
      </div>

      {children}
    </section>
  );
};

export default function SettingsPage() {
  const [masters, setMasters] = useState({
    dealerships: [],
    outlets: [],
    users: [],
  });

  const [pageAccess, setPageAccess] = useState(getStoredPageAccess());

  const [userForm, setUserForm] = useState({
    name: '',
    username: '',
    password: '',
    role: '',
    allowed_outlet_ids: [],
  });

  const [priceUploadForm, setPriceUploadForm] = useState({
    valid_from: today,
    valid_to: '',
    model_year: new Date().getFullYear(),
    file: null,
  });

  const [dealershipForm, setDealershipForm] = useState({
    name: '',
    code: '',
  });

  const [outletForm, setOutletForm] = useState({
    name: '',
    code: '',
    address: '',
    dealership_name: '',
  });

  const [employeeForm, setEmployeeForm] = useState({
    name: '',
    designation: '',
    outlet_name: '',
  });

  const [loading, setLoading] = useState(false);
  const [creatingUser, setCreatingUser] = useState(false);
  const [uploadingPriceList, setUploadingPriceList] = useState(false);
  const [creatingDealership, setCreatingDealership] = useState(false);
  const [creatingOutlet, setCreatingOutlet] = useState(false);
  const [creatingEmployee, setCreatingEmployee] = useState(false);
  const [deletingUserId, setDeletingUserId] = useState(null);

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const outletNames = useMemo(
    () => masters.outlets.map((outlet) => outlet.name),
    [masters.outlets]
  );

  const dealershipNames = useMemo(
    () => masters.dealerships.map((dealer) => dealer.name),
    [masters.dealerships]
  );

  const userRows = useMemo(() => {
    return (masters.users || []).map((user) => {
      const allowedOutlets = user.allowed_outlets || [];

      return {
        id: user.id,
        name: user.name || '',
        username: user.username || '',
        outlet_name: allowedOutlets.length
          ? allowedOutlets.map((outlet) => outlet.name).join(', ')
          : 'All Outlets',
        role: getDisplayRole(user.role),
        raw_role: user.role,
      };
    });
  }, [masters.users]);

  const clearMessages = () => {
    setError('');
    setSuccess('');
  };

  function togglePageRole(path, role) {
    setPageAccess((prev) => {
      const currentRoles = new Set(prev[path] || []);

      if (currentRoles.has(role)) {
        currentRoles.delete(role);
      } else {
        currentRoles.add(role);
      }

      return {
        ...prev,
        [path]: Array.from(currentRoles),
      };
    });
  }

  function savePageAccess() {
    clearMessages();
    saveStoredPageAccess(pageAccess);
    setSuccess('Page access updated successfully. Application will refresh.');

    setTimeout(() => {
      window.location.reload();
    }, 700);
  }

  async function fetchReferenceData() {
    setLoading(true);
    clearMessages();

    try {
      let dealerships = [];
      let outlets = [];

      try {
        const reference = await api.get('/reference-data');
        dealerships = reference?.dealerships || [];
        outlets = reference?.outlets || [];
      } catch {
        const [dealershipResult, outletResult] = await Promise.all([
          api.get('/dealerships'),
          api.get('/outlets'),
        ]);

        dealerships = Array.isArray(dealershipResult) ? dealershipResult : [];
        outlets = Array.isArray(outletResult) ? outletResult : [];
      }

      let users = [];

      try {
        const usersResult = await api.get('/auth/users');
        users = Array.isArray(usersResult) ? usersResult : usersResult?.data || [];
      } catch (e) {
        console.warn('Unable to load users:', e);
      }

      setMasters({
        dealerships,
        outlets,
        users,
      });
    } catch (e) {
      setError(e.message || 'Unable to load settings data.');
    } finally {
      setLoading(false);
    }
  }

  function resetUserForm() {
    setUserForm({
      name: '',
      username: '',
      password: '',
      role: '',
      allowed_outlet_ids: [],
    });
  }

  function toggleAllowedOutlet(outletId) {
    if (userForm.role === 'admin') return;

    setUserForm((prev) => {
      const current = new Set(prev.allowed_outlet_ids || []);

      if (current.has(outletId)) {
        current.delete(outletId);
      } else {
        current.add(outletId);
      }

      return {
        ...prev,
        allowed_outlet_ids: Array.from(current),
      };
    });
  }

  async function handleCreateUser() {
    clearMessages();

    if (!userForm.name.trim() || !userForm.password) {
      setError('Name and Password are required.');
      return;
    }

    if (!userForm.username.trim()) {
      setError('Username is required.');
      return;
    }

    if (!userForm.role) {
      setError('Role is required.');
      return;
    }

    if (userForm.role !== 'admin' && !userForm.allowed_outlet_ids.length) {
      setError('At least one showroom is required for non-admin users.');
      return;
    }

    setCreatingUser(true);

    try {
      await api.post('/auth/register', {
        name: userForm.name.trim(),
        username: userForm.username.trim(),
        password: userForm.password,
        role: userForm.role,
        allowed_outlet_ids:
          userForm.role === 'admin' ? [] : userForm.allowed_outlet_ids,
      });

      setSuccess('User created successfully.');
      resetUserForm();
      await fetchReferenceData();
    } catch (e) {
      setError(e.message || 'Unable to create user.');
    } finally {
      setCreatingUser(false);
    }
  }

  async function handleDeleteUser(user) {
    clearMessages();

    if (!user?.id) {
      setError('User ID not found. Unable to delete user.');
      return;
    }

    const userLabel = user.name || user.username || `User #${user.id}`;

    const confirmed = confirm(
      user.raw_role === 'admin'
        ? `You are deleting an Admin user: ${userLabel}. Continue?`
        : `Delete user "${userLabel}"? This action cannot be undone.`
    );

    if (!confirmed) return;

    setDeletingUserId(user.id);

    try {
      await api.delete(`/auth/users/${user.id}`);

      setSuccess('User deleted successfully.');
      await fetchReferenceData();
    } catch (e) {
      setError(
        e.message ||
          'Unable to delete user. Please confirm that backend DELETE /auth/users/{id} API exists.'
      );
    } finally {
      setDeletingUserId(null);
    }
  }

  async function handleUploadPriceList() {
    clearMessages();

    if (!priceUploadForm.valid_from) {
      setError('Valid From is required.');
      return;
    }

    if (!priceUploadForm.model_year) {
      setError('Model Year is required.');
      return;
    }

    if (!priceUploadForm.file) {
      setError('Please select a .xlsx price-list file.');
      return;
    }

    setUploadingPriceList(true);

    try {
      const formData = new FormData();
      formData.append('file', priceUploadForm.file);
      formData.append('valid_from', priceUploadForm.valid_from);
      formData.append('model_year', String(Number(priceUploadForm.model_year)));
      formData.append('sheet_name', '0');

      if (priceUploadForm.valid_to) {
        formData.append('valid_to', priceUploadForm.valid_to);
      }

      await api.form('/price-list/upload', formData);

      setSuccess('Price list uploaded successfully.');
      setPriceUploadForm((prev) => ({
        ...prev,
        file: null,
      }));

      const fileInput = document.getElementById('price-list-file-input');
      if (fileInput) fileInput.value = '';

      await fetchReferenceData();
    } catch (e) {
      setError(e.message || 'Unable to upload price list.');
    } finally {
      setUploadingPriceList(false);
    }
  }

  async function handleCreateDealership() {
    clearMessages();

    if (!dealershipForm.name.trim()) {
      setError('Dealership Name is required.');
      return;
    }

    setCreatingDealership(true);

    try {
      await api.post('/dealership', {
        name: dealershipForm.name.trim(),
        code: dealershipForm.code.trim(),
      });

      setSuccess('Dealership created successfully.');
      setDealershipForm({ name: '', code: '' });
      await fetchReferenceData();
    } catch (e) {
      setError(e.message || 'Unable to create dealership.');
    } finally {
      setCreatingDealership(false);
    }
  }

  async function handleCreateOutlet() {
    clearMessages();

    if (!outletForm.name.trim()) {
      setError('Outlet Name is required.');
      return;
    }

    if (!outletForm.dealership_name) {
      setError('Dealership is required for showroom creation.');
      return;
    }

    const dealershipId = getIdByName(masters.dealerships, outletForm.dealership_name);

    if (!dealershipId) {
      setError('Selected dealership could not be identified.');
      return;
    }

    setCreatingOutlet(true);

    try {
      await api.post('/outlets', {
        name: outletForm.name.trim(),
        code: outletForm.code.trim(),
        address: outletForm.address.trim(),
        dealership_id: dealershipId,
      });

      setSuccess('Showroom created successfully.');

      setOutletForm({
        name: '',
        code: '',
        address: '',
        dealership_name: '',
      });

      await fetchReferenceData();
    } catch (e) {
      setError(e.message || 'Unable to create showroom.');
    } finally {
      setCreatingOutlet(false);
    }
  }

  async function handleCreateEmployee() {
    clearMessages();

    if (!employeeForm.name.trim()) {
      setError('Employee Name is required.');
      return;
    }

    if (!employeeForm.outlet_name) {
      setError('Outlet is required for showroom employee creation.');
      return;
    }

    const outletId = getIdByName(masters.outlets, employeeForm.outlet_name);

    if (!outletId) {
      setError('Selected outlet could not be identified.');
      return;
    }

    setCreatingEmployee(true);

    try {
      await api.post('/sales-executive', {
        name: employeeForm.name.trim(),
        outlet_id: outletId,
        designation: employeeForm.designation.trim(),
      });

      setSuccess('Employee created successfully.');

      setEmployeeForm({
        name: '',
        designation: '',
        outlet_name: '',
      });

      await fetchReferenceData();
    } catch (e) {
      setError(e.message || 'Unable to create showroom employee.');
    } finally {
      setCreatingEmployee(false);
    }
  }

  useEffect(() => {
    fetchReferenceData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <PageHeader
        title="Settings"
        description="Manage users, page access, showroom access, price lists, dealerships, showrooms, and employees."
        actions={
          <Button variant="secondary" onClick={fetchReferenceData} disabled={loading}>
            <RefreshCw size={16} />
            Refresh
          </Button>
        }
      />

      <div className="mx-auto max-w-[1100px] space-y-8">
        <Alert type="error">{error}</Alert>
        <Alert type="success">{success}</Alert>

        {loading ? (
          <Loader />
        ) : (
          <>
            <SectionCard
              icon="🔐"
              title="Page Access Control"
              subtitle="Admin can control which role can access each page."
            >
              <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
                <table className="w-full min-w-[760px] border-collapse text-sm">
                  <thead>
                    <tr className="bg-slate-50 dark:bg-slate-900">
                      <th className="border-b border-slate-200 px-4 py-3 text-left text-xs font-black uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-300">
                        Page
                      </th>

                      {PAGE_ROLE_OPTIONS.map((role) => (
                        <th
                          key={role.value}
                          className="border-b border-slate-200 px-4 py-3 text-center text-xs font-black uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-300"
                        >
                          {role.label}
                        </th>
                      ))}
                    </tr>
                  </thead>

                  <tbody>
                    {PAGE_ACCESS_ITEMS.map((page) => (
                      <tr
                        key={page.path}
                        className="border-b border-slate-100 bg-white dark:border-slate-800 dark:bg-slate-950"
                      >
                        <td className="px-4 py-3">
                          <p className="font-bold text-slate-900 dark:text-white">
                            {page.label}
                          </p>

                          <p className="text-xs font-semibold text-slate-400">
                            {page.path}
                          </p>
                        </td>

                        {PAGE_ROLE_OPTIONS.map((role) => {
                          const checked = (pageAccess[page.path] || []).includes(
                            role.value
                          );

                          const adminLocked =
                            page.path === '/settings' && role.value === 'admin';

                          return (
                            <td key={role.value} className="px-4 py-3 text-center">
                              <input
                                type="checkbox"
                                checked={checked}
                                disabled={adminLocked}
                                onChange={() => togglePageRole(page.path, role.value)}
                                className="h-5 w-5 cursor-pointer rounded border-slate-300 disabled:cursor-not-allowed disabled:opacity-60"
                              />
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-5 flex justify-end">
                <Button onClick={savePageAccess}>
                  <Save size={16} />
                  Save Page Access
                </Button>
              </div>
            </SectionCard>

            <SectionCard
              icon="👤"
              title="Register New Users"
              subtitle="Create system users and assign showroom-level access."
            >
              <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
                <div className="space-y-4">
                  <Field label="Full Name">
                    <Input
                      value={userForm.name}
                      onChange={(e) =>
                        setUserForm((prev) => ({
                          ...prev,
                          name: e.target.value,
                        }))
                      }
                    />
                  </Field>

                  <Field label="User Name">
                    <Input
                      value={userForm.username}
                      onChange={(e) =>
                        setUserForm((prev) => ({
                          ...prev,
                          username: e.target.value,
                        }))
                      }
                    />
                  </Field>

                  <Field label="Password">
                    <Input
                      type="password"
                      value={userForm.password}
                      onChange={(e) =>
                        setUserForm((prev) => ({
                          ...prev,
                          password: e.target.value,
                        }))
                      }
                    />
                  </Field>

                  <Field label="Role">
                    <Select
                      value={userForm.role}
                      onChange={(e) => {
                        const role = e.target.value;

                        setUserForm((prev) => ({
                          ...prev,
                          role,
                          allowed_outlet_ids:
                            role === 'admin' ? [] : prev.allowed_outlet_ids,
                        }));
                      }}
                    >
                      <option value="">Select Role</option>

                      {ROLE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </Field>

                  <div>
                    <p className="mb-2 text-sm font-bold text-slate-700 dark:text-slate-200">
                      Allowed Showrooms
                    </p>

                    <div
                      className={`max-h-[260px] overflow-auto rounded-2xl border p-3 ${
                        userForm.role === 'admin'
                          ? 'bg-slate-50 opacity-70 dark:bg-slate-900'
                          : 'bg-white dark:bg-slate-950'
                      }`}
                    >
                      {masters.outlets.length ? (
                        masters.outlets.map((outlet) => (
                          <label
                            key={outlet.id}
                            className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-900"
                          >
                            <input
                              type="checkbox"
                              disabled={userForm.role === 'admin'}
                              checked={userForm.allowed_outlet_ids.includes(outlet.id)}
                              onChange={() => toggleAllowedOutlet(outlet.id)}
                            />

                            <span>{outlet.name}</span>
                          </label>
                        ))
                      ) : (
                        <p className="px-3 py-6 text-center text-sm font-semibold text-slate-400">
                          No showrooms available.
                        </p>
                      )}
                    </div>

                    {userForm.role === 'admin' ? (
                      <p className="mt-2 text-xs font-semibold text-slate-400">
                        Admin users automatically get full access to all outlets.
                      </p>
                    ) : null}
                  </div>

                  <div className="flex gap-3 pt-2">
                    <Button onClick={handleCreateUser} disabled={creatingUser}>
                      <UserPlus size={16} />
                      {creatingUser ? 'Creating...' : 'Create User'}
                    </Button>

                    <Button variant="secondary" onClick={resetUserForm}>
                      Reset
                    </Button>
                  </div>
                </div>

                <div className="rounded-2xl border bg-slate-50 p-5 text-sm font-medium text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                  <h3 className="mb-3 font-bold text-slate-900 dark:text-white">
                    Guidelines
                  </h3>

                  <ul className="space-y-2">
                    <li>• Use a unique username</li>
                    <li>• Assign correct role carefully</li>
                    <li>• Showroom assignment controls visibility</li>
                    <li>• Multiple showrooms supported</li>
                    <li>• Password should be secure</li>
                  </ul>

                  <div className="my-4 h-px bg-slate-200 dark:bg-slate-800" />

                  <h3 className="mb-3 font-bold text-slate-900 dark:text-white">
                    Roles
                  </h3>

                  <ul className="space-y-2">
                    <li>Admin → Full access</li>
                    <li>Client → Dealership access</li>
                    <li>Audit Assistant → Assigned showroom access</li>
                  </ul>
                </div>
              </div>
            </SectionCard>

            <SectionCard
              icon="📋"
              title="Users"
              subtitle="Review registered users and their authorised outlet visibility."
            >
              <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800">
                <table className="w-full table-fixed border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
                      <th className="w-[22%] px-4 py-4 text-left text-xs font-black uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                        Name
                      </th>

                      <th className="w-[18%] px-4 py-4 text-left text-xs font-black uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                        Username
                      </th>

                      <th className="w-[30%] px-4 py-4 text-left text-xs font-black uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                        Allowed Showrooms
                      </th>

                      <th className="w-[15%] px-4 py-4 text-left text-xs font-black uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                        Role
                      </th>

                      <th className="w-[15%] px-4 py-4 text-right text-xs font-black uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                        Action
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {userRows.length ? (
                      userRows.map((row) => (
                        <tr
                          key={row.id || row.username}
                          className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900/70"
                        >
                          <td className="px-4 py-4 align-top font-bold text-slate-800 dark:text-slate-100">
                            <div className="break-words leading-snug">
                              {row.name || '-'}
                            </div>
                          </td>

                          <td className="px-4 py-4 align-top font-semibold text-slate-700 dark:text-slate-200">
                            <div className="break-words leading-snug">
                              {row.username || '-'}
                            </div>
                          </td>

                          <td className="px-4 py-4 align-top font-semibold text-slate-700 dark:text-slate-200">
                            <div className="max-w-full whitespace-normal break-words leading-snug">
                              {row.outlet_name || 'All Outlets'}
                            </div>
                          </td>

                          <td className="px-4 py-4 align-top font-bold text-slate-700 dark:text-slate-200">
                            <span className="inline-flex rounded-full border border-slate-300 px-3 py-1 text-xs font-black uppercase tracking-wide text-slate-600 dark:border-slate-700 dark:text-slate-300">
                              {row.role || '-'}
                            </span>
                          </td>

                          <td className="px-4 py-4 text-right align-top">
                            <button
                              type="button"
                              onClick={() => handleDeleteUser(row)}
                              disabled={deletingUserId === row.id}
                              className="inline-flex items-center justify-center gap-2 rounded-xl border border-red-300 bg-red-50 px-3 py-2 text-xs font-black uppercase tracking-wide text-red-600 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-400/30 dark:bg-red-400/10 dark:text-red-300 dark:hover:bg-red-400/20"
                              title="Delete user"
                            >
                              <Trash2 size={14} />
                              {deletingUserId === row.id ? 'Deleting...' : 'Delete'}
                            </button>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td
                          colSpan={5}
                          className="px-4 py-10 text-center text-sm font-semibold text-slate-500 dark:text-slate-400"
                        >
                          No users found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </SectionCard>

            <SectionCard
              icon="📤"
              title="Upload Price List"
              subtitle="Upload Excel file with pricing details."
            >
              <div className="grid gap-4 md:grid-cols-3">
                <Field label="Valid From">
                  <Input
                    type="date"
                    value={priceUploadForm.valid_from}
                    onChange={(e) =>
                      setPriceUploadForm((prev) => ({
                        ...prev,
                        valid_from: e.target.value,
                      }))
                    }
                  />
                </Field>

                <Field label="Valid To">
                  <Input
                    type="date"
                    value={priceUploadForm.valid_to}
                    onChange={(e) =>
                      setPriceUploadForm((prev) => ({
                        ...prev,
                        valid_to: e.target.value,
                      }))
                    }
                  />
                </Field>

                <Field label="Model Year">
                  <Input
                    type="number"
                    value={priceUploadForm.model_year}
                    onChange={(e) =>
                      setPriceUploadForm((prev) => ({
                        ...prev,
                        model_year: e.target.value,
                      }))
                    }
                  />
                </Field>
              </div>

              <div className="mt-6 rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 p-8 text-center dark:border-slate-800 dark:bg-slate-900">
                <UploadCloud className="mx-auto text-slate-400" size={42} />

                <p className="mt-3 text-sm font-bold text-slate-700 dark:text-slate-200">
                  Drag & drop your Excel file here
                </p>

                <p className="mt-1 text-xs font-semibold text-slate-400">
                  or click to browse. Only .xlsx files are supported.
                </p>

                <input
                  id="price-list-file-input"
                  type="file"
                  accept=".xlsx"
                  className="mx-auto mt-5 block max-w-sm cursor-pointer rounded-xl border bg-white p-2 text-sm font-semibold dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200"
                  onChange={(e) =>
                    setPriceUploadForm((prev) => ({
                      ...prev,
                      file: e.target.files?.[0] || null,
                    }))
                  }
                />

                {priceUploadForm.file ? (
                  <p className="mt-3 text-xs font-bold text-slate-500">
                    Selected file: {priceUploadForm.file.name}
                  </p>
                ) : null}

                <Button
                  className="mt-5"
                  onClick={handleUploadPriceList}
                  disabled={uploadingPriceList}
                >
                  <UploadCloud size={16} />
                  {uploadingPriceList ? 'Uploading...' : 'Upload Price List'}
                </Button>
              </div>
            </SectionCard>

            <div className="grid gap-6 lg:grid-cols-2">
              <SectionCard
                icon="🏢"
                title="Create Dealership"
                subtitle="Add a new dealership master."
              >
                <div className="space-y-4">
                  <Field label="Dealership Name">
                    <Input
                      value={dealershipForm.name}
                      onChange={(e) =>
                        setDealershipForm((prev) => ({
                          ...prev,
                          name: e.target.value,
                        }))
                      }
                    />
                  </Field>

                  <Field label="Dealership Code">
                    <Input
                      value={dealershipForm.code}
                      onChange={(e) =>
                        setDealershipForm((prev) => ({
                          ...prev,
                          code: e.target.value,
                        }))
                      }
                    />
                  </Field>

                  <Button
                    onClick={handleCreateDealership}
                    disabled={creatingDealership}
                  >
                    <Save size={16} />
                    {creatingDealership ? 'Creating...' : 'Create Dealership'}
                  </Button>
                </div>
              </SectionCard>

              <SectionCard
                icon="🏬"
                title="Create Showroom"
                subtitle="Create an outlet and map it with dealership."
              >
                <div className="space-y-4">
                  <Field label="Outlet Name">
                    <Input
                      value={outletForm.name}
                      onChange={(e) =>
                        setOutletForm((prev) => ({
                          ...prev,
                          name: e.target.value,
                        }))
                      }
                    />
                  </Field>

                  <Field label="Outlet Code">
                    <Input
                      value={outletForm.code}
                      onChange={(e) =>
                        setOutletForm((prev) => ({
                          ...prev,
                          code: e.target.value,
                        }))
                      }
                    />
                  </Field>

                  <Field label="Address">
                    <Input
                      value={outletForm.address}
                      onChange={(e) =>
                        setOutletForm((prev) => ({
                          ...prev,
                          address: e.target.value,
                        }))
                      }
                    />
                  </Field>

                  <Field label="Dealership">
                    <Select
                      value={outletForm.dealership_name}
                      onChange={(e) =>
                        setOutletForm((prev) => ({
                          ...prev,
                          dealership_name: e.target.value,
                        }))
                      }
                    >
                      <option value="">Select Dealership</option>

                      {dealershipNames.map((name) => (
                        <option key={name} value={name}>
                          {name}
                        </option>
                      ))}
                    </Select>
                  </Field>

                  <Button onClick={handleCreateOutlet} disabled={creatingOutlet}>
                    <Save size={16} />
                    {creatingOutlet ? 'Creating...' : 'Create Showroom'}
                  </Button>
                </div>
              </SectionCard>
            </div>

            <SectionCard
              icon="👨‍💼"
              title="Create Showroom Employee"
              subtitle="Add employee / sales executive mapped to showroom."
            >
              <div className="grid gap-4 md:grid-cols-3">
                <Field label="Employee Name">
                  <Input
                    value={employeeForm.name}
                    onChange={(e) =>
                      setEmployeeForm((prev) => ({
                        ...prev,
                        name: e.target.value,
                      }))
                    }
                  />
                </Field>

                <Field label="Designation">
                  <Input
                    value={employeeForm.designation}
                    onChange={(e) =>
                      setEmployeeForm((prev) => ({
                        ...prev,
                        designation: e.target.value,
                      }))
                    }
                  />
                </Field>

                <Field label="Outlet">
                  <Select
                    value={employeeForm.outlet_name}
                    onChange={(e) =>
                      setEmployeeForm((prev) => ({
                        ...prev,
                        outlet_name: e.target.value,
                      }))
                    }
                  >
                    <option value="">Select Outlet</option>

                    {outletNames.map((name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>

              <Button
                className="mt-5"
                onClick={handleCreateEmployee}
                disabled={creatingEmployee}
              >
                <Save size={16} />
                {creatingEmployee ? 'Creating...' : 'Create Employee'}
              </Button>
            </SectionCard>
          </>
        )}
      </div>
    </>
  );
}