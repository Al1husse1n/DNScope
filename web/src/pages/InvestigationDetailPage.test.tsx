import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { InvestigationDetailPage } from './InvestigationDetailPage';
import { renderWithProviders } from '../test/testUtils';
import * as investigationsHooks from '../api/investigations';
import * as flowHooks from '../hooks/useSubmissionFlow';
import type { InvestigationResponse } from '../api/types';
import type { UseQueryResult } from '@tanstack/react-query';
import type { ApiError } from '../api/client';

vi.mock('../api/investigations');
vi.mock('../hooks/useSubmissionFlow');

describe('InvestigationDetailPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.mocked(flowHooks.useSubmissionFlow).mockReturnValue({
      stage: { kind: 'idle' },
      formError: null,
      submit: vi.fn(),
      dismiss: vi.fn(),
    });
  });

  it('renders full investigation details, rule evaluation trace, narrative, and inconclusive panel', () => {
    const mockDetail: InvestigationResponse = {
      id: 'ecebad4e-0e22-4c08-be50-2e6f88137630',
      domain: 'example.com',
      normalized_domain: 'example.com',
      created_at: '2026-11-24T13:14:59.265871Z',
      assessment: {
        score_result: {
          score: 0,
          risk_level: 'LOW',
          rule_hits: [
            {
              rule_id: 'DOMAIN_AGE_OVER_2Y',
              description: 'Domain has been registered for over 2 years (>= 730 days)',
              points: -10,
              evidence_refs: ['domain_age_over_2y'],
            },
            {
              rule_id: 'VT_UNAVAILABLE',
              description: 'VirusTotal reputation check was unavailable',
              points: 0,
              evidence_refs: ['vt_unavailable'],
            },
          ],
          total_points_before_clamp: -10,
        },
        rule_trace_explanation:
          '- DOMAIN_AGE_OVER_2Y (-10): registered for over 2 years\n- VT_UNAVAILABLE (0): skipped',
        narrative: 'The domain example.com has a LOW risk assessment with a score of 0/100.',
        inconclusive_checks: [
          {
            agent_name: 'reputation',
            reason: 'missing VT_API_KEY',
          },
        ],
      },
    };

    vi.mocked(investigationsHooks.useInvestigation).mockReturnValue({
      data: mockDetail,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as UseQueryResult<InvestigationResponse, ApiError>);

    renderWithProviders(<InvestigationDetailPage />, {
      initialEntries: ['/investigations/ecebad4e-0e22-4c08-be50-2e6f88137630'],
    });

    expect(screen.getByText('example.com')).toBeInTheDocument();
    expect(screen.getByText('0 / 100')).toBeInTheDocument();
    expect(screen.getByText('DOMAIN_AGE_OVER_2Y')).toBeInTheDocument();
    expect(screen.getByText('VT_UNAVAILABLE')).toBeInTheDocument();
    expect(
      screen.getByText('The domain example.com has a LOW risk assessment with a score of 0/100.'),
    ).toBeInTheDocument();
    expect(screen.getByText(/missing VT_API_KEY/i)).toBeInTheDocument();
    expect(screen.getByText('REPUTATION')).toBeInTheDocument();
  });

  it('renders re-run button and clicking it triggers submission flow with the current domain', () => {
    const mockSubmit = vi.fn().mockResolvedValue(undefined);
    vi.mocked(flowHooks.useSubmissionFlow).mockReturnValue({
      stage: { kind: 'idle' },
      formError: null,
      submit: mockSubmit,
      dismiss: vi.fn(),
    });

    const mockDetail: InvestigationResponse = {
      id: 'inv-rerun-123',
      domain: 'rerun-target.org',
      normalized_domain: 'rerun-target.org',
      created_at: '2026-11-24T13:14:59.265871Z',
      assessment: {
        score_result: {
          score: 15,
          risk_level: 'LOW',
          rule_hits: [],
          total_points_before_clamp: 15,
        },
        rule_trace_explanation: 'clean trace',
        narrative: 'Narrative summary',
        inconclusive_checks: [],
      },
    };

    vi.mocked(investigationsHooks.useInvestigation).mockReturnValue({
      data: mockDetail,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as UseQueryResult<InvestigationResponse, ApiError>);

    renderWithProviders(<InvestigationDetailPage />, {
      initialEntries: ['/investigations/inv-rerun-123'],
    });

    const rerunBtn = screen.getByRole('button', { name: /re-run investigation/i });
    expect(rerunBtn).toBeInTheDocument();
    expect(rerunBtn).not.toBeDisabled();

    fireEvent.click(rerunBtn);
    expect(mockSubmit).toHaveBeenCalledWith('rerun-target.org');
  });
});
