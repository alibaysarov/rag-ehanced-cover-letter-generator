import { useState, useEffect, useRef, useCallback } from 'react';
import { autoParseApi } from '../api/auto-parse-client';
import type { ParsingJob, AutoParsedJob } from '../types';

const STORAGE_KEY = 'autoParse_jobId';

interface UseAutoParseReturn {
  job: ParsingJob | null;
  vacancies: AutoParsedJob[];
  isStarting: boolean;
  startParse: (query: string) => Promise<void>;
  loadVacanciesForJob: (jobId: number) => Promise<void>;
}

export function useAutoParse(): UseAutoParseReturn {
  const [jobId, setJobId] = useState<number | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? Number(stored) : null;
  });
  const [job, setJob] = useState<ParsingJob | null>(null);
  const [vacancies, setVacancies] = useState<AutoParsedJob[]>([]);
  const [isStarting, setIsStarting] = useState(false);

  // Holds the active EventSource so we can close it on unmount or completion.
  const esRef = useRef<EventSource | null>(null);

  const closeEventSource = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  const fetchVacancies = useCallback(async (id: number) => {
    try {
      const data = await autoParseApi.getVacancies(id);
      setVacancies(data);
    } catch {
      // Vacancies may not be ready yet; silently ignore
    }
  }, []);

  const subscribeToSSE = useCallback(
    (id: number) => {
      closeEventSource();

      const es = autoParseApi.createEventSource(id);
      esRef.current = es;

      es.onmessage = (event: MessageEvent<string>) => {
        try {
          const parsed: ParsingJob = JSON.parse(event.data);
          setJob(parsed);

          if (parsed.status === 'done' || parsed.status === 'failed') {
            closeEventSource();
            if (parsed.status === 'done') {
              void fetchVacancies(id);
            }
          }
        } catch {
          // Malformed SSE frame; ignore
        }
      };

      es.onerror = () => {
        // On error the browser will retry automatically; we only close if
        // the job has already reached a terminal state.
        if (job?.status === 'done' || job?.status === 'failed') {
          closeEventSource();
        }
      };
    },
    [closeEventSource, fetchVacancies, job?.status],
  );

  // On mount: restore jobId from localStorage and fetch its current state.
  useEffect(() => {
    if (jobId === null) return;

    let cancelled = false;

    void (async () => {
      try {
        const status = await autoParseApi.getStatus(jobId);
        if (cancelled) return;
        setJob(status);

        if (status.status === 'done') {
          await fetchVacancies(jobId);
        } else if (status.status === 'pending' || status.status === 'running') {
          subscribeToSSE(jobId);
        }
      } catch {
        // Job may have been deleted on the server; clear persisted state
        localStorage.removeItem(STORAGE_KEY);
        setJobId(null);
      }
    })();

    return () => {
      cancelled = true;
    };
    // We intentionally run this only once on mount (jobId from localStorage).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Close EventSource on unmount.
  useEffect(() => {
    return () => {
      closeEventSource();
    };
  }, [closeEventSource]);

  const startParse = useCallback(
    async (query: string) => {
      setIsStarting(true);
      try {
        const { parsing_job_id } = await autoParseApi.startParse(query);

        localStorage.setItem(STORAGE_KEY, String(parsing_job_id));
        setJobId(parsing_job_id);
        setVacancies([]);
        setJob(null);

        subscribeToSSE(parsing_job_id);
      } finally {
        setIsStarting(false);
      }
    },
    [subscribeToSSE],
  );

  const loadVacanciesForJob = useCallback(
    async (id: number) => {
      closeEventSource();

      localStorage.setItem(STORAGE_KEY, String(id));
      setJobId(id);
      setVacancies([]);

      try {
        const status = await autoParseApi.getStatus(id);
        setJob(status);
        if (status.status === 'done') {
          await fetchVacancies(id);
        } else if (status.status === 'pending' || status.status === 'running') {
          subscribeToSSE(id);
        }
      } catch {
        // Status unavailable; silently ignore
      }
    },
    [closeEventSource, fetchVacancies, subscribeToSSE],
  );

  return { job, vacancies, isStarting, startParse, loadVacanciesForJob };
}
