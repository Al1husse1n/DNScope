import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskBadge } from './RiskBadge';

describe('RiskBadge', () => {
  it('renders all four defined risk levels with expected text and colors', () => {
    const { rerender } = render(<RiskBadge level="LOW" />);
    expect(screen.getByText('LOW')).toBeInTheDocument();
    expect(screen.getByText('LOW')).toHaveClass('bg-emerald-950', 'text-emerald-300');

    rerender(<RiskBadge level="MEDIUM" />);
    expect(screen.getByText('MEDIUM')).toBeInTheDocument();
    expect(screen.getByText('MEDIUM')).toHaveClass('bg-amber-950', 'text-amber-300');

    rerender(<RiskBadge level="HIGH" />);
    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('HIGH')).toHaveClass('bg-orange-950', 'text-orange-300');

    rerender(<RiskBadge level="CRITICAL" />);
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('CRITICAL')).toHaveClass('bg-red-950', 'text-red-300');
  });

  it('falls back to default styling class for unknown risk level', () => {
    render(<RiskBadge level="UNKNOWN_LEVEL" />);
    const badge = screen.getByText('UNKNOWN_LEVEL');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-slate-800', 'text-slate-300');
  });
});
