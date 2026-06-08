import { useState } from "react";
import Alert from "../components/Alert";
import Button from "../components/Button";
import Field, { Input } from "../components/Field";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const { signIn } = useAuth();

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await signIn(name, password);
      window.location.href = "/";
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-slate-950 p-4">
      <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-2xl dark:bg-slate-950">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-amber-600 dark:text-amber-400">
          Automobile MIS
        </p>

        <h1 className="mt-3 text-3xl font-bold text-slate-950 dark:text-white">
          Sign in
        </h1>

        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          Use the same backend credentials. No backend changes are required.
        </p>

        <form onSubmit={submit} className="mt-7 space-y-4">
          <Alert type="error">{error}</Alert>

          <Field label="Name">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoFocus
            />
          </Field>

          <Field label="Password">
            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="pr-24"
              />

              <button
                type="button"
                onClick={() => setShowPassword((current) => !current)}
                className="absolute right-3 top-1/2 -translate-y-1/2 rounded-xl bg-slate-900 px-3 py-2 text-xs font-black uppercase tracking-wide text-amber-300 transition hover:bg-slate-950"
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </Field>

          <Button disabled={loading} className="w-full">
            {loading ? "Signing in..." : "Login"}
          </Button>
        </form>
      </div>
    </div>
  );
}