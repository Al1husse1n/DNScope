import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';
import { RateLimitBanner } from './RateLimitBanner';

describe('RateLimitBanner', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('displays countdown and enables retry when timer reaches 0', () => {
    const onRetry = vi.fn();
    render(<RateLimitBanner retryAfter={3} onRetry={onRetry} />);

    expect(screen.getByText('Rate limit reached. Retry in 3s.')).toBeInTheDocument();
    const retryBtn = screen.getByRole('button', { name: /retry/i });
    expect(retryBtn).toBeDisabled();

    // Fast-forward 1 second
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByText('Rate limit reached. Retry in 2s.')).toBeInTheDocument();

    // Fast-forward 2 more seconds
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(screen.getByText('Ready to retry.')).toBeInTheDocument();
    expect(retryBtn).not.toBeDisabled();

    // Click retry
    fireEvent.click(retryBtn);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
