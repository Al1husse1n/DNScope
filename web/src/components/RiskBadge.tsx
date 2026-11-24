import React from 'react';
import type { RiskLevel } from '../api/types';
import { getRiskColors } from '../utils/riskColors';

interface RiskBadgeProps {
  level: RiskLevel | string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level }) => {
  const colorClasses = getRiskColors(level);
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wider border ${colorClasses}`}
    >
      {level}
    </span>
  );
};
