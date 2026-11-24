import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HomePage } from '../pages/HomePage';
import { renderWithProviders } from './testUtils';
import * as publicApi from '../api/public';
import { ApiError } from '../api/client';

vi.mock('../api/public');

describe('HomePage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('renders hero title, input, and submit button with NO key prompt or redirect', () => {
    renderWithProviders(<HomePage />, { rawKey: null, initialEntries: ['/'] });

    expect(
      screen.getByRole('heading', { name: /inspect domain infrastructure risk instantly/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/example\.com or suspicious-domain\.net/i),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^investigate$/i })).toBeInTheDocument();
    // No redirect to /key, no key prompt
    expect(screen.queryByPlaceholderText(/paste your x-api-key/i)).not.toBeInTheDocument();
    // Navbar shows API access link
    expect(screen.getByRole('link', { name: /api access/i })).toBeInTheDocument();
  });

  it('triggers investigation when submitting domain and displays progress card', async () => {
    let resolveInvestigate: (val: publicApi.PublicInvestigationResponse) => void = () => {};
    const promise = new Promise<publicApi.PublicInvestigationResponse>((resolve) => {
      resolveInvestigate = resolve;
    });
    vi.mocked(publicApi.investigatePublic).mockReturnValueOnce(promise);

    renderWithProviders(<HomePage />, { rawKey: null });

    const input = screen.getByPlaceholderText(/example\.com or suspicious-domain\.net/i);
    const submitBtn = screen.getByRole('button', { name: /^investigate$/i });

    await userEvent.type(input, 'target-domain.com');
    await userEvent.click(submitBtn);

    expect(publicApi.investigatePublic).toHaveBeenCalledWith(
      'target-domain.com',
      expect.any(AbortSignal),
    );
    // In-flight progress card is displayed
    expect(screen.getByText('target-domain.com')).toBeInTheDocument();
    expect(screen.getByText(/running for/i)).toBeInTheDocument();

    // Resolve promise
    resolveInvestigate({
      share_id: 'abc-123',
      domain: 'target-domain.com',
      normalized_domain: 'target-domain.com',
      created_at: new Date().toISOString(),
      assessment: {
        score_result: {
          score: 10,
          risk_level: 'LOW',
          rule_hits: [],
          total_points_before_clamp: 10,
        },
        rule_trace_explanation: 'none',
        narrative: 'Clean domain',
        inconclusive_checks: [],
      },
      narrative_source: 'gemini',
    });

    await waitFor(() => {
      expect(screen.getByText(/investigation complete/i)).toBeInTheDocument();
    });
  });

  it('renders rate limit banner when rate limited', async () => {
    vi.mocked(publicApi.investigatePublic).mockRejectedValueOnce(
      new ApiError(429, 'rate_limited', 60, null, 'Rate limit reached'),
    );

    renderWithProviders(<HomePage />, { rawKey: null });

    const input = screen.getByPlaceholderText(/example\.com or suspicious-domain\.net/i);
    const submitBtn = screen.getByRole('button', { name: /^investigate$/i });

    await userEvent.type(input, 'ratelimit.com');
    await userEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/rate limit reached/i)).toBeInTheDocument();
    });
  });
});
