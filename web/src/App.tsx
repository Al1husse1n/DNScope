import React, { useMemo } from 'react';
import { RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider, QueryCache } from '@tanstack/react-query';
import { AuthProvider } from './auth/AuthContext';
import { useAuth } from './auth/useAuth';
import { ApiError } from './api/client';
import { router } from './router';

const AppContent: React.FC = () => {
  const { clearKey } = useAuth();

  const queryClient = useMemo(() => {
    return new QueryClient({
      queryCache: new QueryCache({
        onError: (error) => {
          if (error instanceof ApiError && error.status === 401) {
            clearKey();
          }
        },
      }),
      defaultOptions: {
        queries: {
          staleTime: 30_000,
          retry: (failureCount, error) => {
            if (error instanceof ApiError && error.status === 429) {
              return false;
            }
            return failureCount < 2;
          },
        },
      },
    });
  }, [clearKey]);

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
