import React, { useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { Shield, Eye, EyeOff, ArrowRight, Loader2 } from 'lucide-react';
import { useAuth } from '../auth/useAuth';
import { testApiKey } from '../api/keys';
import { ApiError, getApiBaseUrl } from '../api/client';

export const KeyEntryPage: React.FC = () => {
  const { rawKey, setRawKey } = useAuth();
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = apiKeyInput.trim();
    if (!trimmed) {
      setErrorMessage('Please enter an API key.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      await testApiKey(trimmed);
      setRawKey(trimmed);
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setErrorMessage('Invalid API key. Try again.');
        } else if (err.status === 0) {
          setErrorMessage(`Could not reach API at ${getApiBaseUrl()}. Is the backend running?`);
        } else {
          setErrorMessage(err.message || 'Verification failed.');
        }
      } else {
        setErrorMessage('An unexpected error occurred.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center px-4 py-12 bg-slate-950">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl shadow-sky-950/20">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400 mb-3">
            <Shield className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white font-mono">dnscope</h1>
          <p className="text-sm text-slate-400 mt-1">Domain threat investigation</p>
        </div>

        {rawKey && (
          <div className="mb-6 p-3 rounded-lg bg-emerald-950/40 border border-emerald-900/60 text-xs text-emerald-300 flex items-center justify-between">
            <span>You&apos;re authenticated.</span>
            <Link
              to="/"
              className="inline-flex items-center gap-1 font-semibold text-emerald-400 hover:text-emerald-300"
            >
              Continue to investigations <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="apiKeyInput"
              className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5"
            >
              API Key
            </label>
            <div className="relative">
              <input
                id="apiKeyInput"
                type={showKey ? 'text' : 'password'}
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                placeholder="Paste your X-API-Key..."
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-750 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent font-mono text-sm pr-10"
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 p-1"
                aria-label={showKey ? 'Hide key' : 'Show key'}
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Need a key? An admin can generate one with{' '}
              <code className="bg-slate-800 text-slate-300 px-1 py-0.5 rounded font-mono">
                make seed-admin-key
              </code>
              .
            </p>
          </div>

          {errorMessage && (
            <div
              role="alert"
              className="p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-200 text-xs"
            >
              {errorMessage}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-medium text-sm transition flex items-center justify-center gap-2 cursor-pointer disabled:cursor-not-allowed shadow-lg shadow-sky-600/20"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Verifying key...
              </>
            ) : (
              'Test & continue'
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
