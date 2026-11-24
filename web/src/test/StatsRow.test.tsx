import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatsRow } from '../components/StatsRow';
import type { InvestigationSummary } from '../api/types';

describe('StatsRow', () => {
  it('renders all zeros for empty items', () => {
    render(<StatsRow items={[]} />);

    const zeros = screen.getAllByText('0');
    expect(zeros).toHaveLength(3);
    expect(screen.getByText('TOTAL')).toBeInTheDocument();
    expect(screen.getByText('HIGH RISK')).toBeInTheDocument();
    expect(screen.getByText('LAST 24H')).toBeInTheDocument();
  });

  it('correctly calculates high risk count for HIGH and CRITICAL items', () => {
    const items: InvestigationSummary[] = [
      {
        id: '1',
        domain: 'high.com',
        normalized_domain: 'high.com',
        risk_score: 85,
        risk_level: 'HIGH',
        created_at: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        id: '2',
        domain: 'critical.com',
        normalized_domain: 'critical.com',
        risk_score: 95,
        risk_level: 'CRITICAL',
        created_at: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        id: '3',
        domain: 'low.com',
        normalized_domain: 'low.com',
        risk_score: 10,
        risk_level: 'LOW',
        created_at: new Date(Date.now() - 3600000).toISOString(),
      },
    ];

    render(<StatsRow items={items} />);

    expect(screen.getByTestId('stat-total')).toHaveTextContent('3');
    expect(screen.getByTestId('stat-high-risk')).toHaveTextContent('2');
  });

  it('counts items created within the last 24 hours but ignores older items', () => {
    const now = Date.now();
    const items: InvestigationSummary[] = [
      {
        id: '1',
        domain: 'recent.com',
        normalized_domain: 'recent.com',
        risk_score: 20,
        risk_level: 'LOW',
        created_at: new Date(now - 2 * 60 * 60 * 1000).toISOString(), // 2h ago
      },
      {
        id: '2',
        domain: 'old.com',
        normalized_domain: 'old.com',
        risk_score: 20,
        risk_level: 'LOW',
        created_at: new Date(now - 48 * 60 * 60 * 1000).toISOString(), // 48h ago
      },
    ];

    render(<StatsRow items={items} />);

    expect(screen.getByTestId('stat-total')).toHaveTextContent('2');
    expect(screen.getByTestId('stat-recent')).toHaveTextContent('1');
  });
});
