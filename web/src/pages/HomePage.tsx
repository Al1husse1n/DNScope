import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Shield, Zap, Search, Lock, ArrowRight, Loader2 } from 'lucide-react';
import { NavBar } from '../components/NavBar';
import { PendingInvestigationCard } from '../components/PendingInvestigationCard';
import { RateLimitBanner } from '../components/RateLimitBanner';
import { usePublicFlow } from '../hooks/usePublicFlow';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const [domainInput, setDomainInput] = useState('');
  const flow = usePublicFlow();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = domainInput.trim();
    if (!trimmed || flow.stage === 'running') return;
    await flow.submit(trimmed);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <NavBar />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-12 sm:py-16 flex flex-col items-center">
        {/* Hero Section */}
        <div className="text-center space-y-4 mb-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-sky-500/10 border border-sky-500/30 text-sky-400">
            <Zap className="w-3.5 h-3.5" />
            <span>Autonomous threat investigation — zero friction</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white">
            Inspect domain infrastructure risk instantly
          </h1>
          <p className="text-slate-400 text-sm sm:text-base leading-relaxed">
            Real-time DNS records, RDAP registration history, VirusTotal reputation, and an
            autonomous AI analyst narrative. No account or API key required.
          </p>
        </div>

        {/* Rate limit banner */}
        {flow.stage === 'rate_limited' && (
          <div className="w-full mb-6">
            <RateLimitBanner retryAfter={flow.retryAfter || 60} onRetry={flow.reset} />
          </div>
        )}

        {/* Domain Submission Form */}
        <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl mb-8">
          <form onSubmit={handleSubmit} className="space-y-3">
            <label htmlFor="domain-input" className="block text-sm font-medium text-slate-300">
              Investigate a domain
            </label>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Search className="w-4 h-4" />
                </div>
                <input
                  id="domain-input"
                  type="text"
                  autoFocus
                  autoComplete="off"
                  disabled={flow.stage === 'running'}
                  placeholder="example.com or suspicious-domain.net"
                  value={domainInput}
                  onChange={(e) => setDomainInput(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 font-mono text-sm sm:text-base focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
                />
              </div>
              <button
                type="submit"
                disabled={!domainInput.trim() || flow.stage === 'running'}
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm sm:text-base font-semibold shadow-lg shadow-sky-900/20 transition cursor-pointer"
              >
                {flow.stage === 'running' ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Investigating…</span>
                  </>
                ) : (
                  <span>Investigate</span>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Pending / In-flight / Completed / Failed Card */}
        {flow.stage === 'running' && (
          <div className="w-full mb-8">
            <PendingInvestigationCard
              stage={{
                kind: 'polling',
                jobId: 'public',
                domain: flow.domain,
                startedAt: flow.startedAt || Date.now(),
              }}
              onNavigate={(id) => navigate(`/r/${id}`)}
              onDismiss={flow.reset}
            />
          </div>
        )}

        {flow.stage === 'complete' && flow.result && (
          <div className="w-full mb-8">
            <PendingInvestigationCard
              stage={{
                kind: 'completed',
                jobId: 'public',
                investigationId: flow.result.share_id,
              }}
              onNavigate={(id) => navigate(`/r/${id}`)}
              onDismiss={flow.reset}
            />
          </div>
        )}

        {flow.stage === 'failed' && (
          <div className="w-full mb-8">
            <PendingInvestigationCard
              stage={{
                kind: 'failed',
                jobId: 'public',
                domain: flow.domain,
                error: flow.error || 'Investigation failed',
              }}
              onNavigate={() => {}}
              onDismiss={flow.reset}
            />
          </div>
        )}

        {/* Feature Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full mt-6 text-left">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 mb-3">
              <Search className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-semibold text-white mb-1">Deep DNS & RDAP</h2>
            <p className="text-xs text-slate-400">
              Validates A, AAAA, MX, NS, and SPF records alongside registrar data and domain age.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-3">
              <Shield className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-semibold text-white mb-1">VirusTotal Intel</h2>
            <p className="text-xs text-slate-400">
              Cross-checks domain reputation across 70+ threat intelligence engines.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 mb-3">
              <Lock className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-semibold text-white mb-1">Shareable Reports</h2>
            <p className="text-xs text-slate-400">
              Instant 1-hour shareable URLs with full score gauges, rule traces, and narratives.
            </p>
          </div>
        </div>

        {/* Footer / API Link */}
        <div className="mt-12 text-center text-xs text-slate-500 font-mono">
          <span>Need programmatic access or background jobs? </span>
          <Link
            to="/dashboard"
            className="text-sky-400 hover:text-sky-300 inline-flex items-center gap-1 font-medium underline underline-offset-4"
          >
            Access API Dashboard
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </main>
    </div>
  );
};
