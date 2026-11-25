import React from 'react';

interface LoadingSkeletonProps {
  rows?: number;
  type?: 'table' | 'detail';
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ rows = 5, type = 'table' }) => {
  if (type === 'detail') {
    return (
      <div className="space-y-6 animate-pulse max-w-4xl mx-auto py-4">
        <div className="h-8 bg-band rounded-xl w-1/3" />
        <div className="h-24 bg-card border border-border rounded-xl" />
        <div className="h-48 bg-card border border-border rounded-xl" />
        <div className="h-32 bg-card border border-border rounded-xl" />
      </div>
    );
  }

  return (
    <div className="border border-border rounded-xl bg-card overflow-hidden animate-pulse">
      <div className="h-10 bg-band border-b border-border" />
      <div className="divide-y divide-border">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-14 flex items-center px-4 gap-4">
            <div className="h-4 bg-band rounded w-1/4" />
            <div className="h-5 bg-band rounded w-16" />
            <div className="h-4 bg-band rounded w-1/3" />
            <div className="h-4 bg-band rounded w-20 ml-auto" />
          </div>
        ))}
      </div>
    </div>
  );
};
