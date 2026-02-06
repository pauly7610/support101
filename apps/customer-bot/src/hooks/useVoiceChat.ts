/**
 * Voice chat hook for the customer chat widget.
 *
 * Provides:
 * - Microphone recording via MediaRecorder API
 * - Audio upload to /v1/voice/chat endpoint
 * - Playback of synthesized response audio
 * - Recording state management
 *
 * Gracefully degrades when:
 * - Browser doesn't support MediaRecorder
 * - Microphone permission is denied
 * - Voice API is unavailable
 */

import { useCallback, useRef, useState } from 'react';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

interface VoiceSource {
  url: string;
  excerpt: string;
  confidence: number;
}

interface VoiceChatResult {
  userText: string;
  replyText: string;
  audioBase64: string | null;
  audioFormat: string | null;
  sources: VoiceSource[];
}

interface UseVoiceChatOptions {
  voice?: string;
  language?: string;
  textOnly?: boolean;
  onResult?: (result: VoiceChatResult) => void;
  onError?: (error: Error) => void;
}

interface UseVoiceChatReturn {
  isRecording: boolean;
  isProcessing: boolean;
  isPlaying: boolean;
  isSupported: boolean;
  error: Error | null;
  lastResult: VoiceChatResult | null;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  cancelRecording: () => void;
  playAudio: (base64: string, format?: string) => void;
  stopAudio: () => void;
}

export function useVoiceChat(options: UseVoiceChatOptions = {}): UseVoiceChatReturn {
  const { voice = 'nova', language, textOnly = false, onResult, onError } = options;

  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastResult, setLastResult] = useState<VoiceChatResult | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const isSupported =
    typeof window !== 'undefined' &&
    typeof navigator !== 'undefined' &&
    typeof navigator.mediaDevices !== 'undefined' &&
    typeof MediaRecorder !== 'undefined';

  const startRecording = useCallback(async () => {
    if (!isSupported) {
      const err = new Error('Voice recording is not supported in this browser');
      setError(err);
      onError?.(err);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : 'audio/mp4';

      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());

        if (chunksRef.current.length === 0) return;

        const blob = new Blob(chunksRef.current, { type: mimeType });
        chunksRef.current = [];
        await sendAudio(blob);
      };

      mediaRecorderRef.current = recorder;
      recorder.start(250);
      setIsRecording(true);
      setError(null);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      onError?.(error);
    }
  }, [isSupported, onError]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, []);

  const cancelRecording = useCallback(() => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.ondataavailable = null;
      mediaRecorderRef.current.onstop = null;
      if (mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
      mediaRecorderRef.current.stream.getTracks().forEach((t) => t.stop());
      mediaRecorderRef.current = null;
    }
    chunksRef.current = [];
    setIsRecording(false);
  }, []);

  const sendAudio = useCallback(
    async (blob: Blob) => {
      setIsProcessing(true);
      setError(null);

      try {
        const ext = blob.type.includes('webm') ? 'webm' : 'mp4';
        const formData = new FormData();
        formData.append('file', blob, `recording.${ext}`);
        formData.append('voice', voice);
        formData.append('text_only', String(textOnly));
        if (language) {
          formData.append('language', language);
        }

        const res = await fetch(`${BACKEND_URL}/v1/voice/chat`, {
          method: 'POST',
          body: formData,
        });

        if (!res.ok) {
          const errBody = await res.text();
          throw new Error(`Voice API error ${res.status}: ${errBody}`);
        }

        const data = await res.json();

        const result: VoiceChatResult = {
          userText: data.user_text || '',
          replyText: data.reply_text || '',
          audioBase64: data.audio_base64 || null,
          audioFormat: data.audio_format || null,
          sources: data.sources || [],
        };

        setLastResult(result);
        onResult?.(result);

        if (result.audioBase64) {
          playAudio(result.audioBase64, result.audioFormat || 'mp3');
        }
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        onError?.(error);
      } finally {
        setIsProcessing(false);
      }
    },
    [voice, textOnly, language, onResult, onError],
  );

  const playAudio = useCallback((base64: string, format: string = 'mp3') => {
    stopAudio();

    const mimeMap: Record<string, string> = {
      mp3: 'audio/mpeg',
      opus: 'audio/opus',
      aac: 'audio/aac',
      flac: 'audio/flac',
      wav: 'audio/wav',
    };

    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: mimeMap[format] || 'audio/mpeg' });
    const url = URL.createObjectURL(blob);

    const audio = new Audio(url);
    audioRef.current = audio;

    audio.onplay = () => setIsPlaying(true);
    audio.onended = () => {
      setIsPlaying(false);
      URL.revokeObjectURL(url);
    };
    audio.onerror = () => {
      setIsPlaying(false);
      URL.revokeObjectURL(url);
    };

    audio.play().catch(() => setIsPlaying(false));
  }, []);

  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    setIsPlaying(false);
  }, []);

  return {
    isRecording,
    isProcessing,
    isPlaying,
    isSupported,
    error,
    lastResult,
    startRecording,
    stopRecording,
    cancelRecording,
    playAudio,
    stopAudio,
  };
}
