import { useState, useEffect, useRef, useCallback } from 'react';
import { autoParseApi } from '../api/auto-parse-client';
import type { ParsingJob, AutoParsedJob } from '../types';

const STORAGE_KEY = 'autoParse_jobId';

export interface GenerationState {
  status: 'idle' | 'running' | 'done' | 'failed';
  generated: number;
  total: number;
}

interface UseAutoParseReturn {
  job: ParsingJob | null;
  vacancies: AutoParsedJob[];
  isStarting: boolean;
  startParse: (query: string) => Promise<void>;
  loadVacanciesForJob: (jobId: number) => Promise<void>;
  // generation
  genState: GenerationState;
  isStartingGen: boolean;
  startGeneration: () => Promise<void>;
}

export function useAutoParse(): UseAutoParseReturn {
  const [jobId, setJobId] = useState<number | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? Number(stored) : null;
  });
  const [job, setJob] = useState<ParsingJob | null>(null);
  const [vacancies, setVacancies] = useState<AutoParsedJob[]>([]);
  const [isStarting, setIsStarting] = useState(false);
  const [isStartingGen, setIsStartingGen] = useState(false);
  const [genState, setGenState] = useState<GenerationState>({
    status: 'idle',
    generated: 0,
    total: 0,
  });

  const esRef = useRef<EventSource | null>(null);
  const genEsRef = useRef<EventSource | null>(null);

  const closeEventSource = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  const closeGenEventSource = useCallback(() => {
    if (genEsRef.current) {
      genEsRef.current.close();
      genEsRef.current = null;
    }
  }, []);

  const fetchVacancies = useCallback(async (id: number) => {
    try {
      const data = await autoParseApi.getVacancies(id);
      setVacancies(data);
    } catch {
      // ignore
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
          // ignore
        }
      };

      es.onerror = () => {
        if (job?.status === 'done' || job?.status === 'failed') {
          closeEventSource();
        }
      };
    },
    [closeEventSource, fetchVacancies, job?.status],
  );

  const subscribeToGenSSE = useCallback(
    (id: number) => {
      closeGenEventSource();
      const es = autoParseApi.createGenerateEventSource(id);
      genEsRef.current = es;

      es.onmessage = (event: MessageEvent<string>) => {
        try {
          const data = JSON.parse(event.data) as {
            generated: number;
            total: number;
            status: 'running' | 'done' | 'failed';
            vacancy_id?: number;
          };

          setGenState({
            status: data.status,
            generated: data.generated,
            total: data.total,
          });

          if (data.vacancy_id) {
            setVacancies((prev) =>
              prev.map((v) =>
                v.id === data.vacancy_id ? { ...v, is_generated: true } : v,
              ),
            );
          }

          if (data.status === 'done' || data.status === 'failed') {
            closeGenEventSource();
          }
        } catch {
          // ignore
        }
      };

      es.onerror = () => closeGenEventSource();
    },
    [closeGenEventSource],
  );

  const restoreGenState = useCallback(
    async (id: number) => {
      try {
        const genStatus = await autoParseApi.getGenerationStatus(id);
        if (genStatus.is_running) {
          setGenState({ status: 'running', generated: genStatus.generated, total: genStatus.total });
          subscribeToGenSSE(id);
        } else if (genStatus.total > 0 && genStatus.generated === genStatus.total) {
          setGenState({ status: 'done', generated: genStatus.generated, total: genStatus.total });
        } else if (genStatus.generated > 0) {
          setGenState({ status: 'idle', generated: genStatus.generated, total: genStatus.total });
        }
      } catch {
        // ignore — gen status is non-critical
      }
    },
    [subscribeToGenSSE],
  );

  // On mount: restore from localStorage
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
          if (!cancelled) await restoreGenState(jobId);
        } else if (status.status === 'pending' || status.status === 'running') {
          subscribeToSSE(jobId);
        }
      } catch {
        localStorage.removeItem(STORAGE_KEY);
        setJobId(null);
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      closeEventSource();
      closeGenEventSource();
    };
  }, [closeEventSource, closeGenEventSource]);

  const startParse = useCallback(
    async (query: string) => {
      setIsStarting(true);
      try {
        const { parsing_job_id } = await autoParseApi.startParse(query);
        localStorage.setItem(STORAGE_KEY, String(parsing_job_id));
        setJobId(parsing_job_id);
        setVacancies([]);
        setJob(null);
        setGenState({ status: 'idle', generated: 0, total: 0 });
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
      closeGenEventSource();
      localStorage.setItem(STORAGE_KEY, String(id));
      setJobId(id);
      setVacancies([]);
      setGenState({ status: 'idle', generated: 0, total: 0 });

      try {
        const status = await autoParseApi.getStatus(id);
        setJob(status);
        if (status.status === 'done') {
          await fetchVacancies(id);
          await restoreGenState(id);
        } else if (status.status === 'pending' || status.status === 'running') {
          subscribeToSSE(id);
        }
      } catch {
        // ignore
      }
    },
    [closeEventSource, closeGenEventSource, fetchVacancies, subscribeToSSE, restoreGenState],
  );

  const startGeneration = useCallback(async () => {
    if (jobId === null) return;
    setIsStartingGen(true);
    try {
      await autoParseApi.generateLetters(jobId);
      subscribeToGenSSE(jobId);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        // Already running — just subscribe to existing stream
        subscribeToGenSSE(jobId);
      }
    } finally {
      setIsStartingGen(false);
    }
  }, [jobId, subscribeToGenSSE]);

  return {
    job,
    vacancies,
    isStarting,
    startParse,
    loadVacanciesForJob,
    genState,
    isStartingGen,
    startGeneration,
  };
}
