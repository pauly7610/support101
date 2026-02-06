import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import AdminDashboard from '../pages/index';

const mockCostData = {
  period: '2026-02',
  current_spend_usd: 42.5,
  monthly_budget_usd: 100,
  budget_remaining_usd: 57.5,
  budget_utilization_pct: 42.5,
  total_requests: 1250,
  total_tokens: 500000,
  avg_cost_per_request_usd: 0.034,
  by_model: {
    'gpt-4o': { requests: 500, tokens: 200000, cost_usd: 30.0 },
    'gpt-4o-mini': { requests: 750, tokens: 300000, cost_usd: 12.5 },
  },
  by_tenant: {},
  daily_trend: {},
  recent_alerts: [],
};

const mockGovernanceData = {
  agents: { total: 5, active: 3, awaiting_human: 1 },
  hitl: { pending: 2, completed: 45, expired: 1 },
  audit: { total_events: 320, recent_events: 15 },
};

const mockVoiceStatus = {
  enabled: true,
  supported_audio_formats: ['mp3', 'wav', 'webm', 'ogg', 'flac'],
  supported_voices: ['alloy', 'echo', 'fable', 'nova', 'onyx', 'shimmer'],
};

function mockFetchResponses() {
  (globalThis.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
    if (url.includes('/v1/analytics/costs')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockCostData) });
    }
    if (url.includes('/v1/governance/dashboard')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockGovernanceData) });
    }
    if (url.includes('/v1/voice/status')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockVoiceStatus) });
    }
    return Promise.resolve({ ok: false, json: () => Promise.resolve({}) });
  });
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.stubGlobal('fetch', vi.fn());
  mockFetchResponses();
});

describe('AdminDashboard', () => {
  it('should render the dashboard with sidebar and header', async () => {
    render(<AdminDashboard />);

    expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Support101')).toBeInTheDocument();
    expect(screen.getByText('Refresh')).toBeInTheDocument();
  });

  it('should render all sidebar navigation tabs', async () => {
    render(<AdminDashboard />);

    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Knowledge Base')).toBeInTheDocument();
    expect(screen.getByText('Agents')).toBeInTheDocument();
    expect(screen.getByText('Cost Tracking')).toBeInTheDocument();
    expect(screen.getByText('Voice I/O')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('should show overview tab by default', async () => {
    render(<AdminDashboard />);

    expect(screen.getByText('Dashboard Overview')).toBeInTheDocument();
  });

  it('should fetch data on mount', async () => {
    render(<AdminDashboard />);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(3);
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/v1/analytics/costs'),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/v1/governance/dashboard'),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/v1/voice/status'),
    );
  });

  it('should display overview metrics after data loads', async () => {
    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText('$42.50')).toBeInTheDocument();
    });

    expect(screen.getByText('Active Agents')).toBeInTheDocument();
    expect(screen.getByText('HITL Pending')).toBeInTheDocument();
    expect(screen.getByText('Monthly Spend')).toBeInTheDocument();
    expect(screen.getByText('API Requests')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument(); // active agents
    expect(screen.getByText('2')).toBeInTheDocument(); // hitl pending
  });

  it('should switch to Knowledge Base tab', async () => {
    render(<AdminDashboard />);

    fireEvent.click(screen.getByText('Knowledge Base'));

    await waitFor(() => {
      expect(screen.getByText('Knowledge Base Management')).toBeInTheDocument();
    });

    expect(screen.getByText('Upload Document')).toBeInTheDocument();
    expect(screen.getByText('Index Statistics')).toBeInTheDocument();
  });

  it('should switch to Agents tab and show agent data', async () => {
    render(<AdminDashboard />);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByText('Agents'));

    await waitFor(() => {
      expect(screen.getByText('Agent Configuration')).toBeInTheDocument();
    });

    expect(screen.getByText('Total Agents')).toBeInTheDocument();
    expect(screen.getByText('Awaiting Human')).toBeInTheDocument();
    expect(screen.getByText('Agent Blueprints')).toBeInTheDocument();
    expect(screen.getByText('triage_agent')).toBeInTheDocument();
    expect(screen.getByText('knowledge_manager_agent')).toBeInTheDocument();
    expect(screen.getByText('compliance_auditor_agent')).toBeInTheDocument();
  });

  it('should switch to Cost Tracking tab and show cost data', async () => {
    render(<AdminDashboard />);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByText('Cost Tracking'));

    await waitFor(() => {
      expect(screen.getByText('LLM Cost Tracking')).toBeInTheDocument();
    });

    expect(screen.getByText('Current Spend')).toBeInTheDocument();
    expect(screen.getByText('Budget')).toBeInTheDocument();
    expect(screen.getByText('Total Requests')).toBeInTheDocument();
    expect(screen.getByText('Avg Cost/Request')).toBeInTheDocument();
    expect(screen.getByText('Cost by Model')).toBeInTheDocument();
    expect(screen.getByText('gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('gpt-4o-mini')).toBeInTheDocument();
  });

  it('should switch to Voice tab and show voice status', async () => {
    render(<AdminDashboard />);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByText('Voice I/O'));

    await waitFor(() => {
      expect(screen.getByText('Voice I/O Configuration')).toBeInTheDocument();
    });

    expect(screen.getByText('Voice Status')).toBeInTheDocument();
    expect(screen.getByText('Enabled')).toBeInTheDocument();
    expect(screen.getByText('Supported Audio Formats')).toBeInTheDocument();
    expect(screen.getByText('Available Voices')).toBeInTheDocument();
    expect(screen.getByText('Environment Variables')).toBeInTheDocument();
  });

  it('should switch to Settings tab', async () => {
    render(<AdminDashboard />);

    fireEvent.click(screen.getByText('Settings'));

    await waitFor(() => {
      expect(screen.getByText('API Configuration')).toBeInTheDocument();
    });

    expect(screen.getByText('Feature Flags')).toBeInTheDocument();
  });

  it('should call fetchData when Refresh button is clicked', async () => {
    render(<AdminDashboard />);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(3);
    });

    fireEvent.click(screen.getByText('Refresh'));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(6);
    });
  });

  it('should handle API failures gracefully', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockImplementation(() =>
      Promise.resolve({ ok: false, json: () => Promise.resolve({}) }),
    );

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Dashboard Overview')).toBeInTheDocument();
    });

    // Should show placeholder values
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThan(0);
  });

  it('should handle network errors gracefully', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Dashboard Overview')).toBeInTheDocument();
    });
  });

  it('should show budget alerts when present', async () => {
    const costsWithAlerts = {
      ...mockCostData,
      recent_alerts: [{ message: 'Budget at 85% utilization', percentage: 85 }],
    };

    (globalThis.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/v1/analytics/costs')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(costsWithAlerts) });
      }
      if (url.includes('/v1/governance/dashboard')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockGovernanceData) });
      }
      if (url.includes('/v1/voice/status')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockVoiceStatus) });
      }
      return Promise.resolve({ ok: false });
    });

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Recent Alerts')).toBeInTheDocument();
    });

    expect(screen.getByText('Budget at 85% utilization')).toBeInTheDocument();
  });

  it('should show voice disabled state', async () => {
    const disabledVoice = { ...mockVoiceStatus, enabled: false };

    (globalThis.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/v1/voice/status')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(disabledVoice) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });

    render(<AdminDashboard />);

    fireEvent.click(screen.getByText('Voice I/O'));

    await waitFor(() => {
      expect(screen.getByText('Disabled')).toBeInTheDocument();
    });
  });
});
