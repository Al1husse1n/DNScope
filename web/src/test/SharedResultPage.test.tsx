import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route } from 'react-router-dom';
import { SharedResultPage } from '../pages/SharedResultPage';
import { renderWithProviders } from './testUtils';
import * as publicApi from '../api/public';
import { ApiError } from '../api/client';
import type { PublicInvestigationResponse } from '../api/public';

vi.mock('../api/public');

const mockReport: PublicInvestigationResponse = {
  share_id: 'share-uuid-1234',
  domain: 'shared-domain.org',
  normalized_domain: 'shared-domain.org',
  created_at: new Date().toISOString(),
  assessment: {
    score_result: {
      score: 75,
      risk_level: 'HIGH',
      rule_hits: [
        {
          rule_id: 'SUSPICIOUS_NAMESERVERS',
          description: 'Nameservers mapped to known bulletproof hosts',
          points: 75,
          evidence_refs: ['ns1.bulletproof.example'],
        },
      ],
      total_points_before_clamp: 75,
    },
    rule_trace_explanation: 'Rule hit evaluated: +75 points.',
    narrative: 'High infrastructure risk observed due to bulletproof hosting.',
    inconclusive_checks: [
      {
        agent_name: 'reputation',
        reason: 'VirusTotal rate limit exceeded during lookup',
      },
    ],
  },
  narrative_source: 'gemini',
};

function renderSharedPage(initialEntry: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/r/:shareId" element={<SharedResultPage />} />
    </Routes>,
    {
      initialEntries: [initialEntry],
    },
  );
}

describe('SharedResultPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders full investigation details, score gauge, rule table, and narrative without re-run button', async () => {
    vi.mocked(publicApi.getSharedResult).mockResolvedValueOnce(mockReport);

    renderSharedPage('/r/share-uuid-1234');

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'shared-domain.org' })).toBeInTheDocument();
    });

    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('SUSPICIOUS_NAMESERVERS')).toBeInTheDocument();
    expect(
      screen.getByText(/high infrastructure risk observed due to bulletproof hosting/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/inconclusive checks/i)).toBeInTheDocument();

    // Verify copy button exists
    expect(screen.getByRole('button', { name: /copy share link/i })).toBeInTheDocument();

    // Verify re-run button does NOT exist on shared page
    expect(screen.queryByRole('button', { name: /re-run/i })).not.toBeInTheDocument();
  });

  it('copies link to clipboard and displays copied feedback', async () => {
    vi.mocked(publicApi.getSharedResult).mockResolvedValueOnce(mockReport);
    const writeTextSpy = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextSpy,
      },
    });

    renderSharedPage('/r/share-uuid-1234');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /copy share link/i })).toBeInTheDocument();
    });

    const copyBtn = screen.getByRole('button', { name: /copy share link/i });
    await userEvent.click(copyBtn);

    expect(writeTextSpy).toHaveBeenCalled();
    expect(screen.getByText('Copied!')).toBeInTheDocument();
  });

  it('renders 404 expired state when report has expired or is not found', async () => {
    vi.mocked(publicApi.getSharedResult).mockRejectedValueOnce(
      new ApiError(404, 'not_found', null, null, 'Expired'),
    );

    renderSharedPage('/r/non-existent-or-expired');

    await waitFor(() => {
      expect(screen.getByText(/this result has expired/i)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /investigate again →/i })).toBeInTheDocument();
    });
  });

  it('renders daily AI cap warning banner when narrative_source is deterministic_only', async () => {
    const deterministicReport: PublicInvestigationResponse = {
      ...mockReport,
      narrative_source: 'deterministic_only',
      assessment: {
        ...mockReport.assessment,
        narrative: null,
      },
    };
    vi.mocked(publicApi.getSharedResult).mockResolvedValueOnce(deterministicReport);

    renderSharedPage('/r/share-uuid-1234');

    await waitFor(() => {
      expect(screen.getByText(/daily ai analysis cap reached/i)).toBeInTheDocument();
    });
  });
});
