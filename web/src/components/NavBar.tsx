import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Shield, KeyRound, LayoutDashboard, ArrowRight } from 'lucide-react';
import { useAuth } from '../auth/useAuth';

export const NavBar: React.FC = () => {
  const { rawKey, clearKey } = useAuth();
  const navigate = useNavigate();

  const handleChangeKey = () => {
    clearKey();
    navigate('/key');
  };

  return (
    <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 group-hover:bg-sky-500/20 transition">
            <Shield className="w-5 h-5" />
          </div>
          <span className="text-lg font-bold tracking-tight text-white font-mono">dnscope</span>
        </Link>

        <div className="flex items-center gap-3">
          {rawKey ? (
            <>
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-1.5 text-xs text-slate-300 hover:text-white px-2.5 py-1.5 rounded transition hover:bg-slate-800"
              >
                <LayoutDashboard className="w-3.5 h-3.5" />
                Dashboard
              </Link>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-emerald-950/60 border border-emerald-800 text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Authenticated
              </span>
              <button
                onClick={handleChangeKey}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded transition border border-slate-700 cursor-pointer"
              >
                <KeyRound className="w-3.5 h-3.5" />
                Change key
              </button>
            </>
          ) : (
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded transition border border-slate-700 cursor-pointer"
            >
              API access
              <ArrowRight className="w-3.5 h-3.5 text-sky-400" />
            </Link>
          )}
        </div>
      </div>
    </header>
  );
};
