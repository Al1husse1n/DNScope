import type { RiskLevel } from '../api/types';

export function getRiskColors(level: RiskLevel | string): string {
  switch (level) {
    case 'LOW':
      return 'bg-risk-low-bg text-risk-low-fg';
    case 'MEDIUM':
      return 'bg-risk-medium-bg text-risk-medium-fg';
    case 'HIGH':
      return 'bg-risk-high-bg text-risk-high-fg';
    case 'CRITICAL':
      return 'bg-risk-critical-bg text-risk-critical-fg';
    default:
      return 'bg-secondary text-muted-foreground';
  }
}

export function getRiskFillColor(level: RiskLevel | string): string {
  switch (level) {
    case 'LOW':
      return '#34d399';
    case 'MEDIUM':
      return '#fbbf24';
    case 'HIGH':
      return '#fb923c';
    case 'CRITICAL':
      return '#f87171';
    default:
      return '#5e7c99';
  }
}
