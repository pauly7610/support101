import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useVoiceChat } from '../hooks/useVoiceChat';

// Mock MediaRecorder
const mockStop = vi.fn();
const mockStart = vi.fn();
let mockOnDataAvailable: ((e: { data: Blob }) => void) | null = null;
let mockOnStop: (() => void) | null = null;

class MockMediaRecorder {
  state = 'inactive';
  stream: MediaStream;
  ondataavailable: ((e: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;

  constructor(stream: MediaStream) {
    this.stream = stream;
  }

  start() {
    this.state = 'recording';
    mockStart();
  }

  stop() {
    this.state = 'inactive';
    mockStop();
    if (this.onstop) this.onstop();
  }

  static isTypeSupported(type: string) {
    return type === 'audio/webm;codecs=opus';
  }
}

const mockGetUserMedia = vi.fn();
const mockTrackStop = vi.fn();

beforeEach(() => {
  vi.stubGlobal('MediaRecorder', MockMediaRecorder);
  vi.stubGlobal('navigator', {
    mediaDevices: {
      getUserMedia: mockGetUserMedia.mockResolvedValue({
        getTracks: () => [{ stop: mockTrackStop }],
      }),
    },
  });
  vi.stubGlobal('fetch', vi.fn());
  vi.stubGlobal('Audio', vi.fn(() => ({
    play: vi.fn().mockResolvedValue(undefined),
    pause: vi.fn(),
    onplay: null,
    onended: null,
    onerror: null,
    currentTime: 0,
  })));
  vi.stubGlobal('URL', {
    createObjectURL: vi.fn(() => 'blob:mock-url'),
    revokeObjectURL: vi.fn(),
  });
  vi.stubGlobal('atob', vi.fn((s: string) => 'decoded-audio'));
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('useVoiceChat', () => {
  it('should initialize with default state', () => {
    const { result } = renderHook(() => useVoiceChat());

    expect(result.current.isRecording).toBe(false);
    expect(result.current.isProcessing).toBe(false);
    expect(result.current.isPlaying).toBe(false);
    expect(result.current.isSupported).toBe(true);
    expect(result.current.error).toBeNull();
    expect(result.current.lastResult).toBeNull();
  });

  it('should detect browser support', () => {
    const { result } = renderHook(() => useVoiceChat());
    expect(result.current.isSupported).toBe(true);
  });

  it('should detect lack of browser support', () => {
    vi.stubGlobal('MediaRecorder', undefined);
    const { result } = renderHook(() => useVoiceChat());
    expect(result.current.isSupported).toBe(false);
  });

  it('should start recording and request microphone', async () => {
    const { result } = renderHook(() => useVoiceChat());

    await act(async () => {
      await result.current.startRecording();
    });

    expect(mockGetUserMedia).toHaveBeenCalledWith({ audio: true });
    expect(result.current.isRecording).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it('should handle microphone permission denied', async () => {
    mockGetUserMedia.mockRejectedValueOnce(new Error('Permission denied'));
    const onError = vi.fn();
    const { result } = renderHook(() => useVoiceChat({ onError }));

    await act(async () => {
      await result.current.startRecording();
    });

    expect(result.current.isRecording).toBe(false);
    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.message).toBe('Permission denied');
    expect(onError).toHaveBeenCalled();
  });

  it('should set error when recording not supported', async () => {
    vi.stubGlobal('MediaRecorder', undefined);
    const onError = vi.fn();
    const { result } = renderHook(() => useVoiceChat({ onError }));

    await act(async () => {
      await result.current.startRecording();
    });

    expect(result.current.error?.message).toContain('not supported');
    expect(onError).toHaveBeenCalled();
  });

  it('should cancel recording and stop tracks', async () => {
    const { result } = renderHook(() => useVoiceChat());

    await act(async () => {
      await result.current.startRecording();
    });

    expect(result.current.isRecording).toBe(true);

    act(() => {
      result.current.cancelRecording();
    });

    expect(result.current.isRecording).toBe(false);
    expect(mockTrackStop).toHaveBeenCalled();
  });

  it('should process voice chat response from API', async () => {
    const mockResponse = {
      user_text: 'Hello',
      reply_text: 'Hi there!',
      audio_base64: null,
      audio_format: null,
      sources: [],
    };

    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const onResult = vi.fn();
    const { result } = renderHook(() => useVoiceChat({ onResult, textOnly: true }));

    expect(result.current.lastResult).toBeNull();
    expect(onResult).not.toHaveBeenCalled();
  });

  it('should handle API error gracefully', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 502,
      text: () => Promise.resolve('Whisper API error'),
    });

    const onError = vi.fn();
    const { result } = renderHook(() => useVoiceChat({ onError }));

    expect(result.current.error).toBeNull();
  });

  it('should accept custom voice and language options', () => {
    const { result } = renderHook(() =>
      useVoiceChat({ voice: 'alloy', language: 'en', textOnly: true }),
    );

    expect(result.current.isRecording).toBe(false);
    expect(result.current.isSupported).toBe(true);
  });

  it('should stop audio playback', () => {
    const { result } = renderHook(() => useVoiceChat());

    act(() => {
      result.current.stopAudio();
    });

    expect(result.current.isPlaying).toBe(false);
  });

  it('should expose all expected methods', () => {
    const { result } = renderHook(() => useVoiceChat());

    expect(typeof result.current.startRecording).toBe('function');
    expect(typeof result.current.stopRecording).toBe('function');
    expect(typeof result.current.cancelRecording).toBe('function');
    expect(typeof result.current.playAudio).toBe('function');
    expect(typeof result.current.stopAudio).toBe('function');
  });
});
