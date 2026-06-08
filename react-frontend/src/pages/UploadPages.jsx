import { UploadCloud } from "lucide-react";
import { useState } from "react";
import Alert from "../components/Alert";
import Button from "../components/Button";
import Field, { Input, Select } from "../components/Field";
import PageHeader from "../components/PageHeader";
import { useMasters } from "../context/MasterDataContext";
import { uploadEbd } from "../services/reportService";
import { uploadPriceList } from "../services/transactionService";
const today = new Date().toISOString().slice(0, 10);
export function EbdUploadPage() {
  const masters = useMasters();
  const [outlet, setOutlet] = useState("");
  const [file, setFile] = useState(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  async function submit(e) {
    e.preventDefault();
    setMsg("");
    setError("");
    const fd = new FormData();
    fd.append("outlet_id", outlet);
    fd.append("file", file);
    try {
      const res = await uploadEbd(fd);
      setMsg(JSON.stringify(res));
    } catch (e) {
      setError(e.message);
    }
  }
  return (
    <>
      <PageHeader
        title="EBD Upload"
        description="Upload EBD Excel files to /mis/upload-ebd."
      />
      <form onSubmit={submit} className="card max-w-2xl space-y-4 p-5">
        <Alert type="error">{error}</Alert>
        <Alert type="success">{msg}</Alert>
        <Field label="Outlet">
          <Select
            value={outlet}
            onChange={(e) => setOutlet(e.target.value)}
            required
          >
            <option value="">Select Outlet</option>
            {masters.outlets.map((x) => (
              <option key={x.id} value={x.id}>
                {x.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Excel File">
          <Input
            type="file"
            accept=".xlsx,.xls"
            onChange={(e) => setFile(e.target.files?.[0])}
            required
          />
        </Field>
        <Button type="submit">
          <UploadCloud size={16} /> Upload EBD
        </Button>
      </form>
    </>
  );
}
export function PriceListPage() {
  const [form, setForm] = useState({
    sheet_name: "0",
    model_year: new Date().getFullYear(),
    valid_from: today,
    valid_to: "",
  });
  const [file, setFile] = useState(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  async function submit(e) {
    e.preventDefault();
    setMsg("");
    setError("");
    const fd = new FormData();
    Object.entries(form).forEach(([k, v]) => {
      if (v !== "") fd.append(k, v);
    });
    fd.append("file", file);
    try {
      const res = await uploadPriceList(fd);
      setMsg(JSON.stringify(res));
    } catch (e) {
      setError(e.message);
    }
  }
  return (
    <>
      <PageHeader
        title="Price List Upload"
        description="Seed backend price-list master without changing backend code."
      />
      <form onSubmit={submit} className="card max-w-2xl space-y-4 p-5">
        <Alert type="error">{error}</Alert>
        <Alert type="success">{msg}</Alert>
        <Field label="Excel File">
          <Input
            type="file"
            accept=".xlsx,.xls"
            onChange={(e) => setFile(e.target.files?.[0])}
            required
          />
        </Field>
        <Field label="Sheet Name / Index">
          <Input
            value={form.sheet_name}
            onChange={(e) =>
              setForm((f) => ({ ...f, sheet_name: e.target.value }))
            }
          />
        </Field>
        <Field label="Model Year">
          <Input
            type="number"
            value={form.model_year}
            onChange={(e) =>
              setForm((f) => ({ ...f, model_year: e.target.value }))
            }
          />
        </Field>
        <Field label="Valid From">
          <Input
            type="date"
            value={form.valid_from}
            onChange={(e) =>
              setForm((f) => ({ ...f, valid_from: e.target.value }))
            }
          />
        </Field>
        <Field label="Valid To">
          <Input
            type="date"
            value={form.valid_to}
            onChange={(e) =>
              setForm((f) => ({ ...f, valid_to: e.target.value }))
            }
          />
        </Field>
        <Button type="submit">
          <UploadCloud size={16} /> Upload Price List
        </Button>
      </form>
    </>
  );
}
