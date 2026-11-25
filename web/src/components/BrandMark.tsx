import React from 'react';

interface BrandMarkProps {
  size?: 'sm' | 'md';
}

export const BrandMark: React.FC<BrandMarkProps> = ({ size = 'sm' }) => {
  const boxClass = size === 'md' ? 'w-11 h-11 rounded-xl' : 'w-8 h-8 rounded-lg';
  const svgClass = size === 'md' ? 'w-6 h-6' : 'w-5 h-5';

  return (
    <div
      className={`${boxClass} bg-band border border-border flex items-center justify-center shrink-0`}
      aria-hidden="true"
    >
      <svg viewBox="0 0 24 24" fill="none" className={svgClass}>
        {/* Outer DNS scope ring */}
        <circle cx="12" cy="12" r="8.5" stroke="#234b73" strokeWidth="1.25" />
        {/* Equatorial & meridian DNS arcs */}
        <ellipse
          cx="12"
          cy="12"
          rx="4.25"
          ry="8.5"
          stroke="#38bdf8"
          strokeOpacity="0.65"
          strokeWidth="1.15"
        />
        <path d="M 4 12 H 20" stroke="#38bdf8" strokeOpacity="0.45" strokeWidth="1.15" />
        {/* Scope crosshair ticks */}
        <path
          d="M 12 1.75 V 4.25 M 12 19.75 V 22.25 M 1.75 12 H 4.25 M 19.75 12 H 22.25"
          stroke="#38bdf8"
          strokeWidth="1.35"
          strokeLinecap="round"
        />
        {/* Central resolver node */}
        <circle cx="12" cy="12" r="2.25" fill="#38bdf8" />
      </svg>
    </div>
  );
};
