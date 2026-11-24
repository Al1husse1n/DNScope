import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../auth/AuthContext';
import { createTestQueryClient } from './testUtils';
import { HomePage } from '../pages/HomePage';
import { SharedResultPage } from '../pages/SharedResultPage';
import { KeyEntryPage } from '../pages/KeyEntryPage';
import { InvestigationsListPage } from '../pages/InvestigationsListPage';
import { InvestigationDetailPage } from '../pages/InvestigationDetailPage';
import { ProtectedRoute } from '../components/ProtectedRoute';
import * as investigationsApi from '../api/investigations';
import * as publicApi from '../api/public';

vi.mock('../api/investigations');
vi.mock('../api/public');

function renderRouter(initialEntries: string[], rawKey: string | null = null) {
  if (rawKey) {
    localStorage.setItem('dnscope.api_key', rawKey);
  } else {
    localStorage.removeItem('dnscope.api_key');
  }

  const queryClient = createTestQueryClient();
  const testRouter = createMemoryRouter(
    [
      { path: '/', element: <HomePage /> },
      { path: '/r/:shareId', element: <SharedResultPage /> },
      { path: '/key', element: <KeyEntryPage /> },
      {
        path: '/dashboard',
        element: <ProtectedRoute />,
        children: [
          { index: true, element: <InvestigationsListPage /> },
          { path: 'investigations/:id', element: <InvestigationDetailPage /> },
        ],
      },
    ],
    { initialEntries },
  );

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={testRouter} />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('Router Integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('renders HomePage at / with no auth required', () => {
    renderRouter(['/'], null);

    expect(
      screen.getByRole('heading', { name: /inspect domain infrastructure risk instantly/i }),
    ).toBeInTheDocument();
  });

  it('renders SharedResultPage at /r/:shareId without redirecting to /key', async () => {
    vi.mocked(publicApi.getSharedResult).mockResolvedValueOnce({
      share_id: '123',
      domain: 'public-view.com',
      normalized_domain: 'public-view.com',
      created_at: new Date().toISOString(),
      assessment: {
        score_result: {
          score: 10,
          risk_level: 'LOW',
          rule_hits: [],
          total_points_before_clamp: 10,
        },
        rule_trace_explanation: 'none',
        narrative: 'Clean',
        inconclusive_checks: [],
      },
      narrative_source: 'gemini',
    });

    renderRouter(['/r/123'], null);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'public-view.com' })).toBeInTheDocument();
    });
  });

  it('redirects unauthenticated user from /dashboard to /key', async () => {
    renderRouter(['/dashboard'], null);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/paste your x-api-key/i)).toBeInTheDocument();
    });
  });

  it('renders InvestigationsListPage at /dashboard when authenticated', async () => {
    vi.mocked(investigationsApi.useInvestigations).mockReturnValue({
      data: { items: [], total: 0, limit: 20, offset: 0 },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof investigationsApi.useInvestigations>);

    renderRouter(['/dashboard'], 'valid-test-key');

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /^investigations$/i, level: 1 }),
      ).toBeInTheDocument();
    });
  });
});
