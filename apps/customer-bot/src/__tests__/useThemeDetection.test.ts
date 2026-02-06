import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useThemeDetection } from '../hooks/useThemeDetection';

describe('useThemeDetection', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  it('defaults to light theme', () => {
    const { result } = renderHook(() => useThemeDetection());
    expect(result.current[0]).toBe('light');
  });

  it('persists theme to localStorage', () => {
    const { result } = renderHook(() => useThemeDetection());
    act(() => {
      result.current[1]('dark');
    });
    expect(localStorage.getItem('theme')).toBe('dark');
  });

  it('adds dark class to document element', () => {
    const { result } = renderHook(() => useThemeDetection());
    act(() => {
      result.current[1]('dark');
    });
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('removes dark class when switching to light', () => {
    const { result } = renderHook(() => useThemeDetection());
    act(() => {
      result.current[1]('dark');
    });
    act(() => {
      result.current[1]('light');
    });
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('reads stored theme from localStorage', () => {
    localStorage.setItem('theme', 'dark');
    const { result } = renderHook(() => useThemeDetection());
    expect(result.current[0]).toBe('dark');
  });
});
