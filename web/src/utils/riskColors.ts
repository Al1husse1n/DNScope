import type { RiskLevel } from '../api/types';

export function getRiskColors(level: RiskLevel | string): string {
  switch (level) {
    case 'LOW':
      return 'bg-emerald-950 text-emerald-300 border-emerald-800';
    case 'MEDIUM':
      return 'bg-amber-950 text-amber-300 border-amber-800';
    case 'HIGH':
      return 'bg-orange-950 text-orange-300 border-orange-800';
    case 'CRITICAL':
      return 'bg-red-950 text-red-300 border-red-800';
    default:
      return 'bg-slate-800 text-slate-300 border-slate-700';
  }
}

export function getRiskFillColor(level: RiskLevel | string): string {
  switch (level) {
    case 'LOW':
      return '#10b981';
    case 'MEDIUM':
      return '#f59e0b';
    case 'HIGH':
      return '#f97316';
    case 'CRITICAL':
      return '#ef4444';
    default:
      return '#64748b';
  }
}
