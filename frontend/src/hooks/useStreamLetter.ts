import { useState, useCallback, useRef } from 'react';
import { API_BASE_URL } from '@/api/client';
import { TokenManager } from '@/features/auth';
import type {
  StreamLetterFromUrlRequest,
  StreamLetterFromTextRequest,
  StreamStatus,
} from '@/types/letter';

interface UseStreamLetterReturn {
  content: string;
  status: StreamStatus;
  error: string | null;
  streamFromUrl: (req: StreamLetterFromUrlRequest) => void;
  streamFromText: (req: StreamLetterFromTextRequest) => void;
  reset: () => void;
}

export function useStreamLetter(): UseStreamLetterReturn {
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

  const _stream = useCallback(async (endpoint: string, body: FormData) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setContent('');
    setError(null);
    setStatus('parsing');

    const token = TokenManager.getAccessToken();

    try {
      const response = await fetch(`${API_BASE_URL}/letter/${endpoint}`, {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body,
        signal: controller.signal,
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `HTTP ${response.status}`);
      }

      const reader = response.body!.getReader();
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
          const chunk = JSON.parse(raw) as { delta?: string; status?: string; error?: string };
          if (chunk.error) {
            setError(chunk.error);
            setStatus('error');
            return;
          }
          if (chunk.status === '__PARSING__') {
            setStatus('parsing');
          } else if (chunk.status === '__READY__') {
            setStatus('streaming');
          } else if (chunk.delta) {
            setStatus('streaming');
            setContent(prev => prev + chunk.delta);
          }
        }
      }
      setStatus('done');
    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') return;
      setError((err as Error).message ?? 'Unknown error');
      setStatus('error');
    }
  }, []);

  const streamFromUrl = useCallback(
    (req: StreamLetterFromUrlRequest) => {
      const fd = new FormData();
      fd.append('url', req.url);
      fd.append('source_id', req.source_id.toString());
      _stream('url/stream', fd);
    },
    [_stream],
  );

  const streamFromText = useCallback(
    (req: StreamLetterFromTextRequest) => {
      const fd = new FormData();
      fd.append('name', req.name);
      fd.append('description', req.description);
      fd.append('source_id', req.source_id.toString());
      _stream('text/stream', fd);
    },
    [_stream],
  );

  return { content, status, error, streamFromUrl, streamFromText, reset };
}