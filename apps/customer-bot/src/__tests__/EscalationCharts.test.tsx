import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import EscalationCharts from '../components/EscalationCharts';

vi.mock('idb-keyval', () => ({
  get: vi.fn(),
  set: vi.fn(),
}));

import * as idb from 'idb-keyval';

describe('EscalationCharts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading skeleton initially', () => {
    (idb.get as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));
    const { container } = render(<EscalationCharts />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows empty state when no escalations', async () => {
    (idb.get as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    render(<EscalationCharts />);
    await waitFor(() => {
      expect(screen.getByText(/no escalations yet/i)).toBeInTheDocument();
    });
  });

  it('renders chart when escalations exist', async () => {
    const mockData = [
      { timestamp: Date.now() - 86400000, text: 'Issue 1' },
      { timestamp: Date.now() - 86400000, text: 'Issue 2' },
      { timestamp: Date.now(), text: 'Issue 3' },
    ];
    (idb.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockData);
    render(<EscalationCharts />);
    await waitFor(() => {
      expect(screen.getByText(/escalations per day/i)).toBeInTheDocument();
    });
  });
});
