import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskBadge } from './RiskBadge';

describe('RiskBadge', () => {
  it('renders all four defined risk levels with expected text and colors', () => {
    const { rerender } = render(<RiskBadge level="LOW" />);
    expect(screen.getByText('LOW')).toBeInTheDocument();
    expect(screen.getByText('LOW')).toHaveClass('bg-risk-low-bg', 'text-risk-low-fg');

    rerender(<RiskBadge level="MEDIUM" />);
    expect(screen.getByText('MEDIUM')).toBeInTheDocument();
    expect(screen.getByText('MEDIUM')).toHaveClass('bg-risk-medium-bg', 'text-risk-medium-fg');

    rerender(<RiskBadge level="HIGH" />);
    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('HIGH')).toHaveClass('bg-risk-high-bg', 'text-risk-high-fg');

    rerender(<RiskBadge level="CRITICAL" />);
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('CRITICAL')).toHaveClass(
      'bg-risk-critical-bg',
      'text-risk-critical-fg',
    );
  });

  it('falls back to default styling class for unknown risk level', () => {
    render(<RiskBadge level="UNKNOWN_LEVEL" />);
    const badge = screen.getByText('UNKNOWN_LEVEL');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-secondary', 'text-muted-foreground');
  });
});
