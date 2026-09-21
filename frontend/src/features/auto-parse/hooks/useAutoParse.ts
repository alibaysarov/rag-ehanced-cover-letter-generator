import { useState, useEffect, useRef, useCallback, type Dispatch, type SetStateAction } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { autoParseApi } from '../api/auto-parse-client';
import type { ParsingJob, AutoParsedJob, GenerationMode } from '../types';
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
  startParse: (query: string, mode: GenerationMode, vacancyLimit: number) => Promise<void>;
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
            void queryClient.invalidateQueries({ queryKey: ['parsers'] });
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
    [closeEventSource, fetchVacancies, job?.status, queryClient],
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
    if (message.type === 'generation.vacancy_ready') {
      const vacancy = message.vacancy as AutoParsedJob | undefined;
      if (message.parsing_job_id !== jobIdRef.current || !vacancy || typeof vacancy.id !== 'number') return;
      revisionRef.current.set(vacancy.id, Date.now());
      setVacancies((previous) => {
        const existingIndex = previous.findIndex((item) => item.id === vacancy.id);
        if (existingIndex === -1) return [...previous, vacancy].sort((a, b) => a.id - b.id);
        return previous.map((item) => item.id === vacancy.id ? vacancy : item);
      });
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

      const applyGenerationEvent = (event: MessageEvent<string>) => {
        try {
          const raw = JSON.parse(event.data) as Record<string, string | { status: string }>;
          const entries = event.type === 'snapshot'
            ? Object.entries(raw).map(([id, value]) => [Number(id), typeof value === 'string' ? JSON.parse(value) : value] as const)
            : [[Number(raw.vacancy_id), raw] as const];
          let generated = 0; let failed = 0;
          for (const [, item] of entries) { if (item.status === 'generated') generated++; if (item.status === 'failed') failed++; }
          if (event.type === 'snapshot') setGenState((old) => ({ status: generated + failed >= old.total && old.total > 0 ? (failed ? 'failed' : 'done') : 'running', generated, total: Math.max(old.total, entries.length) }));
          const data = entries[0]?.[1];
          if (data && Number.isFinite(entries[0][0]) && data.status === 'generated') {
            setVacancies((prev) =>
              prev.map((v) =>
                v.id === entries[0][0] ? { ...v, is_generated: true, cover_letter_text: typeof (data as { cover_letter_text?: unknown }).cover_letter_text === 'string' ? (data as { cover_letter_text: string }).cover_letter_text : v.cover_letter_text } : v,
              ),
            );
          }
        } catch {
          // ignore
        }
      };
      es.onmessage = applyGenerationEvent;
      es.addEventListener('snapshot', applyGenerationEvent as EventListener);
      es.addEventListener('complete', () => { void fetchVacancies(id); closeGenEventSource(); });

      es.onerror = () => closeGenEventSource();
    },
    [closeGenEventSource, fetchVacancies],
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

  // Template dispatch belongs to the backend and may happen shortly after the
  // parsing SSE reaches `done`. Poll only its status; never issue POST /generate.
  useEffect(() => {
    if (jobId === null || job?.generation_mode !== 'template' || job.status !== 'done' || genState.status === 'done') return;
    void restoreGenState(jobId);
    const timer = window.setInterval(() => void restoreGenState(jobId), 2000);
    return () => window.clearInterval(timer);
  }, [jobId, job?.generation_mode, job?.status, genState.status, restoreGenState]);

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
    async (query: string, mode: GenerationMode, vacancyLimit: number) => {
      setIsStarting(true);
      try {
        const { parsing_job_id } = await autoParseApi.startParse(query, mode, vacancyLimit);
        await queryClient.invalidateQueries({ queryKey: ['parsers'] });
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
          generation_mode: mode,
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
