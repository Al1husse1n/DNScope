import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { KeyRound, LayoutDashboard, ArrowRight } from 'lucide-react';
import { useAuth } from '../auth/useAuth';
import { BrandMark } from './BrandMark';

export const NavBar: React.FC = () => {
  const { rawKey, clearKey } = useAuth();
  const navigate = useNavigate();

  const handleChangeKey = () => {
    clearKey();
    navigate('/key');
  };

  return (
    <header className="bg-background border-b border-border sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <Link
          to="/"
          aria-label="dnscope"
          className="flex items-center gap-2.5 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <BrandMark size="sm" />
          <span className="text-[17px] tracking-tight text-foreground font-sans">
            dn<span className="text-accent">scope</span>
          </span>
        </Link>

        <div className="flex items-center gap-2">
          {rawKey ? (
            <>
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground px-3 py-1.5 rounded-xl transition hover:bg-secondary cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                <LayoutDashboard className="w-3.5 h-3.5 text-accent" />
                Dashboard
              </Link>
              <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs bg-risk-low-bg text-risk-low-fg">
                <span className="w-1.5 h-1.5 rounded-full bg-risk-low-fg" />
                Authenticated
              </span>
              <button
                onClick={handleChangeKey}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs text-secondary-foreground bg-secondary hover:bg-secondary-hover rounded-xl transition cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                <KeyRound className="w-3.5 h-3.5 text-muted-foreground" />
                Change key
              </button>
            </>
          ) : (
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-1.5 text-xs text-secondary-foreground bg-secondary hover:bg-secondary-hover px-3.5 py-1.5 rounded-xl transition cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              API access
              <ArrowRight className="w-3.5 h-3.5 text-accent" />
            </Link>
          )}
        </div>
      </div>
    </header>
  );
};
