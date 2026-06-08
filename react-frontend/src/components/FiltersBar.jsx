import Button from './Button';
import Field, { Select } from './Field';

export default function FiltersBar({
  filters,
  setFilters,
  dealerships = [],
  outlets = [],
  onApply,
  children,
  rightActions,
}) {
  return (
    <div className="mb-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[1fr_1fr_1fr_auto_auto] xl:items-end">
        <Field label="Dealership">
          <Select
            value={filters.dealership_id || ''}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                dealership_id: e.target.value || undefined,
                outlet_id: undefined,
                offset: 0,
              }))
            }
          >
            <option value="">All Dealerships</option>

            {dealerships.map((dealership) => (
              <option key={dealership.id} value={dealership.id}>
                {dealership.name}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Outlet">
          <Select
            value={filters.outlet_id || ''}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                outlet_id: e.target.value || undefined,
                offset: 0,
              }))
            }
          >
            <option value="">All Outlets</option>

            {outlets
              .filter((outlet) => {
                if (!filters.dealership_id) return true;
                return String(outlet.dealership_id) === String(filters.dealership_id);
              })
              .map((outlet) => (
                <option key={outlet.id} value={outlet.id}>
                  {outlet.name}
                </option>
              ))}
          </Select>
        </Field>

        {children}

        <div className="flex items-end">
          <Button onClick={onApply} className="h-12 w-full min-w-[180px]">
            Apply
          </Button>
        </div>

        {rightActions ? (
          <div className="flex items-end">
            {rightActions}
          </div>
        ) : null}
      </div>
    </div>
  );
}