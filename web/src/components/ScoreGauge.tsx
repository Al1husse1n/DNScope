import React from 'react';
import type { RiskLevel } from '../api/types';
import { getRiskFillColor } from '../utils/riskColors';

interface ScoreGaugeProps {
  score: number;
  riskLevel?: RiskLevel | string;
  width?: number;
}

export const ScoreGauge: React.FC<ScoreGaugeProps> = ({
  score,
  riskLevel = 'LOW',
  width = 320,
}) => {
  const clampedScore = Math.max(0, Math.min(100, score));
  const height = 24;
  const barPadding = 2;
  const fillWidth = Math.max(0, (clampedScore / 100) * (width - 70 - barPadding * 2));
  const fillColor = getRiskFillColor(riskLevel);

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="overflow-visible font-sans"
      role="img"
      aria-label={`Risk score: ${score} out of 100`}
    >
      {/* Neutral track */}
      <rect x="0" y="5" width={width - 70} height="14" rx="6" fill="#12283f" />

      {/* Semantic progress fill */}
      {fillWidth > 0 && (
        <rect x={barPadding} y="6" width={fillWidth} height="12" rx="5" fill={fillColor} />
      )}

      {/* Tick marks at 25%, 50%, 75% */}
      {[25, 50, 75].map((tick) => {
        const xPos = (tick / 100) * (width - 70);
        return (
          <line
            key={tick}
            x1={xPos}
            y1="5"
            x2={xPos}
            y2="19"
            stroke="#234b73"
            strokeWidth="1"
            strokeDasharray="2 2"
          />
        );
      })}

      {/* Numeric score label */}
      <text x={width - 60} y="16" className="fill-foreground text-xs font-mono">
        {`${clampedScore} / 100`}
      </text>
    </svg>
  );
};
