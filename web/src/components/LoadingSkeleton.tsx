import React from 'react';

interface LoadingSkeletonProps {
  rows?: number;
  type?: 'table' | 'detail';
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ rows = 5, type = 'table' }) => {
  if (type === 'detail') {
    return (
      <div className="space-y-6 animate-pulse max-w-4xl mx-auto py-4">
        <div className="h-8 bg-slate-800 rounded w-1/3" />
        <div className="h-24 bg-slate-800 rounded" />
        <div className="h-48 bg-slate-800 rounded" />
        <div className="h-32 bg-slate-800 rounded" />
      </div>
    );
  }

  return (
    <div className="border border-slate-800 rounded-lg overflow-hidden animate-pulse">
      <div className="h-10 bg-slate-850 border-b border-slate-800" />
      <div className="divide-y divide-slate-800/60">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-14 bg-slate-900/50 flex items-center px-4 gap-4">
            <div className="h-4 bg-slate-800 rounded w-1/4" />
            <div className="h-5 bg-slate-800 rounded w-16" />
            <div className="h-4 bg-slate-800 rounded w-1/3" />
            <div className="h-4 bg-slate-800 rounded w-20 ml-auto" />
          </div>
        ))}
      </div>
    </div>
  );
};
