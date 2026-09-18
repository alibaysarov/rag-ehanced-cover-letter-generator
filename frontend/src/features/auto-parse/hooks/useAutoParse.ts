import { useState, useEffect, useRef, useCallback, type Dispatch, type SetStateAction } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { autoParseApi } from '../api/auto-parse-client';
import type { ParsingJob, AutoParsedJob } from '../types';
import useWebSocket from '@/hooks/useWebSocket';
import { AUTO_PARSE_HISTORY_KEY } from '../components/ParseHistory';

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
  setVacancies: Dispatch<SetStateAction<AutoParsedJob[]>>
}

export function useAutoParse(): UseAutoParseReturn {
  const queryClient = useQueryClient();
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
  const jobIdRef = useRef(jobId);
  const revisionRef = useRef(new Map<number, number>());
  const requestRef = useRef(0);
  jobIdRef.current = jobId;

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
    const request = ++requestRef.current;
    const before = new Map(revisionRef.current);
    try {
      const data = await autoParseApi.getVacancies(id);
      if (jobIdRef.current !== id || request !== requestRef.current) return;
      setVacancies((current) => {
        const currentById = new Map(current.map((item) => [item.id, item]));
        const merged = data.map((item) =>
          (revisionRef.current.get(item.id) ?? 0) > (before.get(item.id) ?? 0)
            ? currentById.get(item.id) ?? item
            : item,
        );
        for (const item of current) if (!merged.some((candidate) => candidate.id === item.id)) merged.push(item);
        return merged.sort((a, b) => a.id - b.id);
      });
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
          if (jobIdRef.current !== id) return;
          setJob(parsed);
          if (parsed.status === 'done' || parsed.status === 'failed') {
            closeEventSource();
            void fetchVacancies(id);
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

  const handleWebSocket = useCallback((event: MessageEvent<string>) => {
    let data: unknown;
    try { data = JSON.parse(event.data); } catch { return; }
    if (!data || typeof data !== 'object') return;
    const message = data as Record<string, unknown>;
    if (message.type === 'parsing.vacancy_saved') {
      const vacancy = message.vacancy as AutoParsedJob | undefined;
      if (message.parsing_job_id !== jobIdRef.current || !vacancy || typeof vacancy.id !== 'number') return;
      revisionRef.current.set(vacancy.id, Date.now());
      setVacancies((previous) => previous.some((item) => item.id === vacancy.id)
        ? previous
        : [...previous, vacancy].sort((a, b) => a.id - b.id));
      return;
    }
    if (Number(message.batch_id) !== jobIdRef.current || message.status !== 'generated' || typeof message.vacancy_id !== 'number') return;
    revisionRef.current.set(message.vacancy_id, Date.now());
    setVacancies((previous) => previous.map((item) => item.id === message.vacancy_id
      ? { ...item, is_generated: true, cover_letter_text: typeof message.cover_letter_text === 'string' ? message.cover_letter_text : item.cover_letter_text }
      : item));
  }, []);

  useWebSocket({ messageHandler: handleWebSocket, onOpen: () => { if (jobIdRef.current !== null) void fetchVacancies(jobIdRef.current); } });

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
        await fetchVacancies(jobId);
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

  useEffect(() => {
    if (jobId === null || (job?.status !== 'pending' && job?.status !== 'running')) return;
    const timer = window.setInterval(() => void fetchVacancies(jobId), 5000);
    return () => window.clearInterval(timer);
  }, [jobId, job?.status, fetchVacancies]);

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
        const pendingJob: ParsingJob = {
          id: parsing_job_id,
          query,
          status: 'pending',
          saved_count: 0,
          total_found: 0,
          created_at: new Date().toISOString(),
          finished_at: null,
          error: null,
        };
        setJob(pendingJob);
        queryClient.setQueryData<ParsingJob[]>(AUTO_PARSE_HISTORY_KEY, (history = []) => [
          pendingJob,
          ...history.filter((item) => item.id !== parsing_job_id),
        ]);
        void queryClient.invalidateQueries({ queryKey: AUTO_PARSE_HISTORY_KEY });
        setGenState({ status: 'idle', generated: 0, total: 0 });
        void fetchVacancies(parsing_job_id);
        subscribeToSSE(parsing_job_id);
      } finally {
        setIsStarting(false);
      }
    },
    [fetchVacancies, queryClient, subscribeToSSE],
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
    setVacancies,
  };
}
