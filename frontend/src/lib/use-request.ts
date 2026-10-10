import { useEffect, useState } from "react";
import { Api, errorMessage } from "./api";

export function useRequest<T>(api: Api, path: string, revision: string | number = 0) {
  const key = `${path}:${revision}`;
  const [result, setResult] = useState<{ key: string; api: Api; data?: T; error?: string } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    api<T>(path, { signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setResult({ key, api, data }); })
      .catch(error => { if (!controller.signal.aborted) setResult({ key, api, error: errorMessage(error) }); });
    return () => controller.abort();
  }, [api, path, key]);
  const current = result?.key === key && result?.api === api ? result : null;
  return { data: current?.data, error: current?.error, busy: current === null };
}
