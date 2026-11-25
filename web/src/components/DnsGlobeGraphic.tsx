import React from 'react';

export const DnsGlobeGraphic: React.FC = () => {
  return (
    <svg
      viewBox="0 0 800 300"
      className="w-full h-full pointer-events-none select-none"
      aria-hidden="true"
    >
      {/* Horizon globe arc & latitude/longitude lines */}
      <g fill="none" stroke="#17324d" strokeWidth="1">
        <circle cx="400" cy="340" r="260" />
        <ellipse cx="400" cy="340" rx="200" ry="260" />
        <ellipse cx="400" cy="340" rx="120" ry="260" />
        <ellipse cx="400" cy="340" rx="45" ry="260" />
        <path d="M 155 245 Q 400 205 645 245" />
        <path d="M 185 185 Q 400 140 615 185" />
        <path d="M 245 130 Q 400 95 555 130" />
      </g>

      {/* Global DNS query arcs */}
      <g fill="none" stroke="#0ea5e9" strokeOpacity="0.45" strokeWidth="1.25">
        <path d="M 210 215 Q 305 70 400 100" />
        <path d="M 400 100 Q 505 55 590 195" />
        <path d="M 270 165 Q 395 40 530 155" />
        <path d="M 175 260 Q 280 120 355 155" />
        <path d="M 355 155 Q 470 110 620 250" />
        <path d="M 295 225 Q 400 135 505 220" />
      </g>

      {/* Resolver nodes */}
      <g fill="#38bdf8">
        <circle cx="210" cy="215" r="3" />
        <circle cx="270" cy="165" r="3" />
        <circle cx="400" cy="100" r="3.5" />
        <circle cx="530" cy="155" r="3" />
        <circle cx="590" cy="195" r="3" />
        <circle cx="355" cy="155" r="2.5" />
        <circle cx="505" cy="220" r="2.5" />
        <circle cx="295" cy="225" r="2.5" />
        <circle cx="175" cy="260" r="2.5" />
        <circle cx="620" cy="250" r="2.5" />
      </g>
    </svg>
  );
};
