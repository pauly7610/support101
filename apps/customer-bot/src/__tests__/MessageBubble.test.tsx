import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import MessageBubble from '../components/customer/ChatWidget/MessageBubble';

describe('MessageBubble', () => {
  const baseProps = {
    text: 'Hello, how can I help?',
    sender: 'agent' as const,
    timestamp: Date.now(),
  };

  it('renders message text', () => {
    render(<MessageBubble {...baseProps} />);
    expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
  });

  it('renders agent avatar for agent messages', () => {
    render(<MessageBubble {...baseProps} sender="agent" />);
    const avatar = screen.getByLabelText(/agent/i);
    expect(avatar).toBeInTheDocument();
  });

  it('renders user avatar for user messages', () => {
    render(<MessageBubble {...baseProps} sender="user" />);
    const avatar = screen.getByLabelText(/you/i);
    expect(avatar).toBeInTheDocument();
  });

  it('renders citation badges when sources provided', () => {
    const sources = [
      { url: 'https://docs.example.com/faq', excerpt: 'FAQ answer', confidence: 0.9 },
    ];
    render(<MessageBubble {...baseProps} sources={sources} onCitationClick={vi.fn()} />);
    expect(screen.getByText('[1]')).toBeInTheDocument();
  });

  it('displays relative timestamp', () => {
    render(<MessageBubble {...baseProps} timestamp={Date.now() - 60000} />);
    expect(screen.getByText(/1m ago/i)).toBeInTheDocument();
  });
});
