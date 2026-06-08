import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getMasters } from "../services/masterService";
const MasterDataContext = createContext(null);
export function MasterDataProvider({ children }) {
  const [data, setData] = useState({
    cars: [],
    variants: [],
    outlets: [],
    executives: [],
    accessories: [],
    dealerships: [],
    components: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function refresh() {
    setLoading(true);
    setError("");
    try {
      setData(await getMasters());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    refresh();
  }, []);
  const maps = useMemo(
    () => ({
      outletById: Object.fromEntries(
        (data.outlets || []).map((x) => [x.id, x]),
      ),
      dealershipById: Object.fromEntries(
        (data.dealerships || []).map((x) => [x.id, x]),
      ),
      variantById: Object.fromEntries(
        (data.variants || []).map((x) => [x.id, x]),
      ),
      executiveById: Object.fromEntries(
        (data.executives || []).map((x) => [x.id, x]),
      ),
    }),
    [data],
  );
  return (
    <MasterDataContext.Provider
      value={{ ...data, ...maps, loading, error, refresh }}
    >
      {children}
    </MasterDataContext.Provider>
  );
}
export function useMasters() {
  const ctx = useContext(MasterDataContext);
  if (!ctx)
    throw new Error("useMasters must be used inside MasterDataProvider");
  return ctx;
}
