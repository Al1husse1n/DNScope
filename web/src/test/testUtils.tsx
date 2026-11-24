import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../auth/AuthContext';

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: string[];
  queryClient?: QueryClient;
  rawKey?: string | null;
}

export function renderWithProviders(ui: React.ReactElement, options: CustomRenderOptions = {}) {
  const {
    initialEntries = ['/'],
    queryClient = createTestQueryClient(),
    rawKey = 'test-api-key',
    ...renderOptions
  } = options;

  if (rawKey !== undefined) {
    if (rawKey) {
      localStorage.setItem('dnscope.api_key', rawKey);
    } else {
      localStorage.removeItem('dnscope.api_key');
    }
  }

  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    queryClient,
  };
}
