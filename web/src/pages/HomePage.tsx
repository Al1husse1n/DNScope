import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Shield, Zap, Search, Lock, ArrowRight, Loader2 } from 'lucide-react';
import { NavBar } from '../components/NavBar';
import { DnsGlobeGraphic } from '../components/DnsGlobeGraphic';
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
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <NavBar />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-10 sm:py-14 flex flex-col items-center">
        {/* Hero with subtle DNS Globe Mesh */}
        <div className="relative w-full flex flex-col items-center text-center pt-4 pb-8 mb-6 overflow-hidden">
          <div className="absolute inset-x-0 bottom-0 h-56 opacity-60 pointer-events-none">
            <DnsGlobeGraphic />
          </div>

          <div className="relative z-10 space-y-4 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md text-xs bg-band border border-border text-accent">
              <Zap className="w-3.5 h-3.5" />
              <span>Autonomous threat investigation — zero friction</span>
            </div>
            <h1 className="text-3xl sm:text-5xl tracking-tight text-foreground leading-tight">
              Inspect domain infrastructure risk instantly
            </h1>
            <p className="text-muted-foreground text-sm sm:text-base leading-relaxed">
              Real-time DNS records, RDAP registration history, VirusTotal reputation, and a
              deterministic risk score. No account or API key required.
            </p>
          </div>
        </div>

        {/* Rate limit banner */}
        {flow.stage === 'rate_limited' && (
          <div className="w-full mb-6">
            <RateLimitBanner retryAfter={flow.retryAfter || 60} onRetry={flow.reset} />
          </div>
        )}

        {/* Domain Submission Card (band + concentric card) */}
        <div className="w-full rounded-xl bg-band border border-border overflow-hidden mb-8">
          <div className="flex items-center justify-between px-5 py-2.5 text-xs text-muted-foreground">
            <label htmlFor="domain-input" className="cursor-pointer">
              Investigate a domain
            </label>
            <div className="hidden sm:flex items-center gap-1.5 font-mono text-subtle-foreground">
              <span>Try:</span>
              {['example.com', 'google.com'].map((sample) => (
                <button
                  key={sample}
                  type="button"
                  disabled={flow.stage === 'running'}
                  onClick={() => setDomainInput(sample)}
                  className="px-2 py-0.5 rounded-md bg-secondary hover:bg-secondary-hover text-secondary-foreground transition cursor-pointer disabled:opacity-40"
                >
                  {sample}
                </button>
              ))}
            </div>
          </div>

          <form
            onSubmit={handleSubmit}
            className="p-5 sm:p-6 bg-card border-t border-border rounded-[calc(0.75rem-1px)]"
          >
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-subtle-foreground">
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
                  className="w-full pl-10 pr-4 py-3 rounded-xl bg-input border border-border-strong text-foreground placeholder-muted-foreground/80 font-mono text-sm sm:text-base focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent disabled:opacity-50 disabled:cursor-not-allowed transition"
                />
              </div>
              <button
                type="submit"
                disabled={!domainInput.trim() || flow.stage === 'running'}
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed text-primary-foreground text-sm sm:text-base transition cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                {flow.stage === 'running' ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Investigating…</span>
                  </>
                ) : (
                  <>
                    <span>Investigate</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
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
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full mt-2 text-left">
          <div className="p-5 rounded-xl bg-card border border-border">
            <div className="w-8 h-8 rounded-lg bg-band border border-border flex items-center justify-center text-accent mb-3">
              <Search className="w-4 h-4" />
            </div>
            <h2 className="text-sm text-foreground mb-1">Deep DNS & RDAP</h2>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Validates A, AAAA, MX, NS, and SPF records alongside registrar data and domain age.
            </p>
          </div>

          <div className="p-5 rounded-xl bg-card border border-border">
            <div className="w-8 h-8 rounded-lg bg-band border border-border flex items-center justify-center text-accent mb-3">
              <Shield className="w-4 h-4" />
            </div>
            <h2 className="text-sm text-foreground mb-1">VirusTotal intel</h2>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Cross-checks domain reputation across 70+ threat intelligence engines.
            </p>
          </div>

          <div className="p-5 rounded-xl bg-card border border-border">
            <div className="w-8 h-8 rounded-lg bg-band border border-border flex items-center justify-center text-accent mb-3">
              <Lock className="w-4 h-4" />
            </div>
            <h2 className="text-sm text-foreground mb-1">Shareable reports</h2>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Instant 1-hour shareable URLs with full score gauges, rule traces, and narratives.
            </p>
          </div>
        </div>

        {/* Footer / API Link */}
        <div className="mt-10 text-center text-xs text-subtle-foreground">
          <span>Need programmatic access or background jobs? </span>
          <Link
            to="/dashboard"
            className="text-accent hover:text-primary-hover inline-flex items-center gap-1 transition"
          >
            Access API Dashboard
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </main>
    </div>
  );
};
