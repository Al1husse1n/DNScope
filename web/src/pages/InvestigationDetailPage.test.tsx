import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { InvestigationDetailPage } from './InvestigationDetailPage';
import { renderWithProviders } from '../test/testUtils';
import * as investigationsHooks from '../api/investigations';
import type { InvestigationResponse } from '../api/types';
import type { UseQueryResult } from '@tanstack/react-query';
import type { ApiError } from '../api/client';

vi.mock('../api/investigations');

describe('InvestigationDetailPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
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
});
