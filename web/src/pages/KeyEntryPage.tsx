import React, { useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { Eye, EyeOff, ArrowRight, Loader2 } from 'lucide-react';
import { useAuth } from '../auth/useAuth';
import { testApiKey } from '../api/keys';
import { ApiError, getApiBaseUrl } from '../api/client';
import { BrandMark } from '../components/BrandMark';

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
      const target = from === '/' ? '/dashboard' : from;
      navigate(target, { replace: true });
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
    <div className="min-h-screen bg-background flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md bg-card border border-border rounded-xl p-8">
        <div className="text-center mb-8">
          <div className="inline-flex justify-center mb-3">
            <BrandMark size="md" />
          </div>
          <h1 className="text-2xl tracking-tight text-foreground font-sans">
            dn<span className="text-accent">scope</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Domain threat investigation</p>
        </div>

        {rawKey && (
          <div className="mb-6 p-3 rounded-xl bg-risk-low-bg border border-border text-xs text-risk-low-fg flex items-center justify-between">
            <span>You&apos;re authenticated.</span>
            <Link
              to="/"
              className="inline-flex items-center gap-1 text-risk-low-fg hover:text-foreground"
            >
              Continue to investigations <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="apiKeyInput" className="block text-xs text-muted-foreground mb-1.5">
              API key
            </label>
            <div className="relative">
              <input
                id="apiKeyInput"
                type={showKey ? 'text' : 'password'}
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                placeholder="Paste your X-API-Key..."
                className="w-full px-3.5 py-2.5 bg-input border border-border-strong rounded-xl text-foreground placeholder-muted-foreground/80 focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent font-mono text-sm pr-10"
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-subtle-foreground hover:text-foreground p-1 cursor-pointer"
                aria-label={showKey ? 'Hide key' : 'Show key'}
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="mt-2 text-xs text-subtle-foreground">
              Need a key? An admin can generate one with{' '}
              <code className="bg-secondary text-muted-foreground px-1.5 py-0.5 rounded font-mono">
                make seed-admin-key
              </code>
              .
            </p>
          </div>

          {errorMessage && (
            <div
              role="alert"
              className="p-3 rounded-xl bg-risk-critical-bg border border-border text-risk-critical-fg text-xs"
            >
              {errorMessage}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-50 text-primary-foreground text-sm transition flex items-center justify-center gap-2 cursor-pointer disabled:cursor-not-allowed"
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
