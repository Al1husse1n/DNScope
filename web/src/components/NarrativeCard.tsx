import React from 'react';
import { Bot } from 'lucide-react';

interface NarrativeCardProps {
  narrative: string | null;
}

export const NarrativeCard: React.FC<NarrativeCardProps> = ({ narrative }) => {
  if (!narrative) {
    return (
      <div className="p-4 rounded-xl bg-card border border-border text-muted-foreground text-sm">
        No narrative available (explainer not configured).
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-band border border-border overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <Bot className="w-3.5 h-3.5 text-accent" />
          <span>Threat explanation</span>
        </div>
        <span className="text-subtle-foreground">Narrated by Gemini</span>
      </div>
      <div className="p-4 rounded-[calc(0.75rem-1px)] bg-card border-t border-border">
        <p className="text-sm leading-relaxed text-foreground font-sans whitespace-pre-wrap">
          {narrative}
        </p>
      </div>
    </div>
  );
};
