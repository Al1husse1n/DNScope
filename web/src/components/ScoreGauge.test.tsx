import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ScoreGauge } from './ScoreGauge';

describe('ScoreGauge', () => {
  it('renders score 0 with numeric label and zero fill width', () => {
    const { container } = render(<ScoreGauge score={0} riskLevel="LOW" width={320} />);
    expect(screen.getByText('0 / 100')).toBeInTheDocument();
    // No fill rect rendered when fillWidth is 0
    const rects = container.querySelectorAll('rect');
    expect(rects.length).toBe(1); // Only background track
  });

  it('renders score 50 with correct width and label', () => {
    const { container } = render(<ScoreGauge score={50} riskLevel="MEDIUM" width={320} />);
    expect(screen.getByText('50 / 100')).toBeInTheDocument();
    const rects = container.querySelectorAll('rect');
    expect(rects.length).toBe(2); // Track + fill
    const fillRect = rects[1];
    // width = 320, trackWidth = 250, fillWidth = 0.5 * (250 - 4) = 123
    expect(parseFloat(fillRect.getAttribute('width') || '0')).toBeCloseTo(123, 0);
  });

  it('renders score 100 with full fill width', () => {
    const { container } = render(<ScoreGauge score={100} riskLevel="CRITICAL" width={320} />);
    expect(screen.getByText('100 / 100')).toBeInTheDocument();
    const rects = container.querySelectorAll('rect');
    expect(rects.length).toBe(2);
    const fillRect = rects[1];
    expect(parseFloat(fillRect.getAttribute('width') || '0')).toBeCloseTo(246, 0);
  });
});
