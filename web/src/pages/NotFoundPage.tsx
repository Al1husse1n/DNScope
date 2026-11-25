import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, ArrowLeft } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center px-4 text-center">
      <div className="w-12 h-12 rounded-xl bg-band border border-border flex items-center justify-center text-accent mb-4">
        <ShieldAlert className="w-6 h-6" />
      </div>
      <h1 className="text-2xl font-mono text-foreground mb-2">404 — Page not found</h1>
      <p className="text-sm text-muted-foreground max-w-sm mb-6">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        to="/"
        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-secondary hover:bg-secondary-hover text-secondary-foreground text-xs transition"
      >
        <ArrowLeft className="w-4 h-4" /> Return to investigations
      </Link>
    </div>
  );
};
