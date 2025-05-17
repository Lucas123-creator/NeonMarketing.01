import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

export function useApi<T>(url: string, refreshInterval?: number) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(url);
      setData(response.data);
    } catch (err: any) {
      setError(err.message || 'Error fetching data');
    } finally {
      setLoading(false);
    }
  }, [url]);

  useEffect(() => {
    fetchData();
    if (refreshInterval) {
      const interval = setInterval(fetchData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchData, refreshInterval]);

  return { data, loading, error, refetch: fetchData };
} 