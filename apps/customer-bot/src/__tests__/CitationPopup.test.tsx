import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CitationPopup from '../components/CitationPopup';

describe('CitationPopup', () => {
  const baseProps = {
    excerpt: 'This is a documentation excerpt about password resets.',
    confidence: 0.92,
    lastUpdated: '2026-01-15',
    sourceUrl: 'https://docs.example.com/password-reset',
    onClose: vi.fn(),
  };

  it('renders the citation popup with excerpt', () => {
    render(<CitationPopup {...baseProps} />);
    expect(screen.getByText(/password resets/i)).toBeInTheDocument();
  });

  it('displays confidence percentage', () => {
    render(<CitationPopup {...baseProps} />);
    expect(screen.getByText(/92%/)).toBeInTheDocument();
  });

  it('displays last updated date', () => {
    render(<CitationPopup {...baseProps} />);
    expect(screen.getByText(/2026-01-15/)).toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(<CitationPopup {...baseProps} onClose={onClose} />);
    const closeBtn = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when backdrop clicked', () => {
    const onClose = vi.fn();
    render(<CitationPopup {...baseProps} onClose={onClose} />);
    const backdrop = screen.getByTestId('citation-backdrop');
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('renders source URL link', () => {
    render(<CitationPopup {...baseProps} />);
    const link = screen.getByRole('link', { name: /view source/i });
    expect(link).toHaveAttribute('href', baseProps.sourceUrl);
  });
});
