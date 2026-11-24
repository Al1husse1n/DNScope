import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { InvestigationsListPage } from './InvestigationsListPage';
import { renderWithProviders } from '../test/testUtils';
import * as investigationsHooks from '../api/investigations';
import type { ListInvestigationsResponse } from '../api/types';
import type { UseQueryResult } from '@tanstack/react-query';
import type { ApiError } from '../api/client';

vi.mock('../api/investigations');

describe('InvestigationsListPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders investigations list with domain names, badges, and total count', () => {
    const mockData: ListInvestigationsResponse = {
      items: [
        {
          id: '11111111-1111-1111-1111-111111111111',
          domain: 'phishing-alert.com',
          normalized_domain: 'phishing-alert.com',
          risk_score: 85,
          risk_level: 'CRITICAL',
          created_at: new Date().toISOString(),
        },
        {
          id: '22222222-2222-2222-2222-222222222222',
          domain: 'safe-portal.org',
          normalized_domain: 'safe-portal.org',
          risk_score: 10,
          risk_level: 'LOW',
          created_at: new Date().toISOString(),
        },
      ],
      total: 2,
      limit: 20,
      offset: 0,
    };

    vi.mocked(investigationsHooks.useInvestigations).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as UseQueryResult<ListInvestigationsResponse, ApiError>);

    renderWithProviders(<InvestigationsListPage />);

    expect(screen.getByText('phishing-alert.com')).toBeInTheDocument();
    expect(screen.getByText('safe-portal.org')).toBeInTheDocument();
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('LOW')).toBeInTheDocument();
    expect(screen.getAllByText('2').length).toBeGreaterThanOrEqual(1);
  });

  it('renders empty state when items list is empty', () => {
    const mockEmpty: ListInvestigationsResponse = {
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
    };

    vi.mocked(investigationsHooks.useInvestigations).mockReturnValue({
      data: mockEmpty,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as UseQueryResult<ListInvestigationsResponse, ApiError>);

    renderWithProviders(<InvestigationsListPage />);

    expect(screen.getByText(/no investigations yet/i)).toBeInTheDocument();
    expect(screen.getByText(/domain submission arrives in p6b/i)).toBeInTheDocument();
  });
});
