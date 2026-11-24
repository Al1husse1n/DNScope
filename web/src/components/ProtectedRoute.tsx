import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import { NavBar } from './NavBar';

export const ProtectedRoute: React.FC = () => {
  const { rawKey } = useAuth();
  const location = useLocation();

  if (!rawKey) {
    return <Navigate to="/key" replace state={{ from: location }} />;
  }

  return (
    <>
      <NavBar />
      <main className="min-h-[calc(100vh-4rem)]">
        <Outlet />
      </main>
    </>
  );
};
