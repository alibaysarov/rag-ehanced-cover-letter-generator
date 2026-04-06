import { useState, useCallback, useRef } from 'react';
import { API_BASE_URL } from '@/api/client';
import { TokenManager } from '@/features/auth';
import type { TranslateRequest, StreamStatus } from '@/types/letter';

interface UseStreamTranslateReturn {
  content: string;
  status: StreamStatus;
  error: string | null;
  translate: (req: TranslateRequest) => void;
  reset: () => void;
}

export function useStreamTranslate(): UseStreamTranslateReturn {
  const [content, setContent] = useState('');
  const [status, setStatus] = useState<StreamStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setContent('');
    setStatus('idle');
    setError(null);
  }, []);

  const translate = useCallback((req: TranslateRequest) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setContent('');
    setError(null);
    setStatus('streaming');

    const formData = new FormData();
    formData.append('text', req.text);
    formData.append('target_language', req.target_language);

    const token = TokenManager.getAccessToken();

    fetch(`${API_BASE_URL}/letter/translate/stream`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (!res.body) throw new Error('No response body');

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            if (!line.startsWith('data:')) continue;
            const raw = line.slice(5).trim();
            if (raw === '[DONE]') {
              setStatus('done');
              return;
            }
            try {
              const parsed = JSON.parse(raw) as { delta?: string; error?: string };
              if (parsed.error) {
                setError(parsed.error);
                setStatus('error');
                return;
              }
              if (parsed.delta) {
                setContent((prev) => prev + parsed.delta);
              }
            } catch {
              // skip malformed lines
            }
          }
        }
        setStatus('done');
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Unknown error');
        setStatus('error');
      });
  }, []);

  return { content, status, error, translate, reset };
}
