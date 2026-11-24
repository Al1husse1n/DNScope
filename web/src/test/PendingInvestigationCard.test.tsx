import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { PendingInvestigationCard } from '../components/PendingInvestigationCard';
import type { SubmissionStage } from '../hooks/useSubmissionFlow';

describe('PendingInvestigationCard', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders nothing when stage is idle', () => {
    const stage: SubmissionStage = { kind: 'idle' };
    const { container } = render(
      <PendingInvestigationCard stage={stage} onNavigate={vi.fn()} onDismiss={vi.fn()} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders domain and all four stages waiting at t=0 of polling', () => {
    const startedAt = Date.now();
    const stage: SubmissionStage = {
      kind: 'polling',
      jobId: 'job-1',
      domain: 'test-pending.com',
      startedAt,
    };

    render(<PendingInvestigationCard stage={stage} onNavigate={vi.fn()} onDismiss={vi.fn()} />);

    expect(screen.getByText('test-pending.com')).toBeInTheDocument();
    expect(screen.getByText('Running for 0s…')).toBeInTheDocument();

    // All four stages show waiting (●)
    expect(screen.getByTestId('stage-0-waiting')).toBeInTheDocument();
    expect(screen.getByTestId('stage-1-waiting')).toBeInTheDocument();
    expect(screen.getByTestId('stage-2-waiting')).toBeInTheDocument();
    expect(screen.getByTestId('stage-3-waiting')).toBeInTheDocument();
    expect(screen.getByText('Progress is approximate. Actual timing varies.')).toBeInTheDocument();
  });

  it('shows DNS complete (✓) and Registration running at t=5s', () => {
    const baseTime = 10000;
    vi.setSystemTime(baseTime);

    const stage: SubmissionStage = {
      kind: 'polling',
      jobId: 'job-1',
      domain: 'test-pending.com',
      startedAt: baseTime,
    };

    render(<PendingInvestigationCard stage={stage} onNavigate={vi.fn()} onDismiss={vi.fn()} />);

    // Advance 5 seconds
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(screen.getByText('Running for 5s…')).toBeInTheDocument();
    expect(screen.getByTestId('stage-0-done')).toBeInTheDocument();
    expect(screen.getByTestId('stage-1-running')).toBeInTheDocument();
    expect(screen.getByTestId('stage-2-waiting')).toBeInTheDocument();
    expect(screen.getByTestId('stage-3-waiting')).toBeInTheDocument();
  });

  it('shows first three stages complete (✓) and Narrative running at t=12s', () => {
    const baseTime = 10000;
    vi.setSystemTime(baseTime);

    const stage: SubmissionStage = {
      kind: 'polling',
      jobId: 'job-1',
      domain: 'test-pending.com',
      startedAt: baseTime,
    };

    render(<PendingInvestigationCard stage={stage} onNavigate={vi.fn()} onDismiss={vi.fn()} />);

    // Advance 12 seconds
    act(() => {
      vi.advanceTimersByTime(12000);
    });

    expect(screen.getByText('Running for 12s…')).toBeInTheDocument();
    expect(screen.getByTestId('stage-0-done')).toBeInTheDocument();
    expect(screen.getByTestId('stage-1-done')).toBeInTheDocument();
    expect(screen.getByTestId('stage-2-done')).toBeInTheDocument();
    expect(screen.getByTestId('stage-3-running')).toBeInTheDocument();
  });

  it('renders failed state with error message and calls onDismiss on click', () => {
    const onDismiss = vi.fn();
    const stage: SubmissionStage = {
      kind: 'failed',
      jobId: 'job-1',
      domain: 'fail.com',
      error: 'Upstream VT lookup failed',
    };

    render(<PendingInvestigationCard stage={stage} onNavigate={vi.fn()} onDismiss={onDismiss} />);

    expect(screen.getByText(/Investigation failed/)).toBeInTheDocument();
    expect(screen.getByText('Upstream VT lookup failed')).toBeInTheDocument();

    const dismissBtn = screen.getByRole('button', { name: /dismiss/i });
    fireEvent.click(dismissBtn);
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('calls onNavigate with investigation id after 600ms delay in completed state', () => {
    const onNavigate = vi.fn();
    const stage: SubmissionStage = {
      kind: 'completed',
      jobId: 'job-1',
      investigationId: 'inv-456',
    };

    render(<PendingInvestigationCard stage={stage} onNavigate={onNavigate} onDismiss={vi.fn()} />);

    expect(screen.getByText(/Investigation complete/)).toBeInTheDocument();
    expect(onNavigate).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(600);
    });

    expect(onNavigate).toHaveBeenCalledWith('inv-456');
  });
});
