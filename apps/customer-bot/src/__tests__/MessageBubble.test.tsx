import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import MessageBubble from '../components/customer/ChatWidget/MessageBubble';

describe('MessageBubble', () => {
  const baseProps = {
    from: 'bot' as const,
    text: 'Hello, how can I help?',
    timestamp: new Date().toLocaleTimeString(),
    sources: [] as string[],
  };

  it('renders message text', () => {
    render(<MessageBubble {...baseProps} />);
    expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
  });

  it('renders agent avatar for agent messages', () => {
    render(<MessageBubble {...baseProps} from="bot" />);
    const avatar = screen.getByLabelText(/agent/i);
    expect(avatar).toBeInTheDocument();
  });

  it('renders user avatar for user messages', () => {
    render(<MessageBubble {...baseProps} from="user" />);
    const avatar = screen.getByLabelText(/you/i);
    expect(avatar).toBeInTheDocument();
  });

  it('renders citation badges when sources provided', () => {
    const sources = ['FAQ: docs.example.com/faq'];
    render(<MessageBubble {...baseProps} sources={sources} />);
    expect(screen.getByText('[1]')).toBeInTheDocument();
  });

  it('displays relative timestamp', () => {
    render(<MessageBubble {...baseProps} timestamp="12:00:00 PM" />);
    expect(screen.getByText('12:00:00 PM')).toBeInTheDocument();
  });
});
