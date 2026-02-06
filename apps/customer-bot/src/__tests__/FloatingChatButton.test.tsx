import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FloatingChatButton from '../components/customer/ChatWidget/FloatingChatButton';

describe('FloatingChatButton', () => {
  it('renders the chat button', () => {
    render(<FloatingChatButton onClick={() => {}} />);
    const button = screen.getByRole('button', { name: /open chat/i });
    expect(button).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<FloatingChatButton onClick={handleClick} />);
    fireEvent.click(screen.getByRole('button', { name: /open chat/i }));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('shows unread badge when unreadCount > 0', () => {
    render(<FloatingChatButton onClick={() => {}} unreadCount={3} />);
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('hides unread badge when unreadCount is 0', () => {
    render(<FloatingChatButton onClick={() => {}} unreadCount={0} />);
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });
});
