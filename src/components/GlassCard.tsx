// @C5-REAL
import React from 'react';
import { cn } from './AwwwardsFadeIn';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  glowColor?: string;
}

export default function GlassCard({ children, className, glowColor = 'rgba(43,59,229,0.15)' }: GlassCardProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-md border border-white/10 bg-black/40 backdrop-blur-xl p-8 group transition-all duration-300 ease-[cubic-bezier(0.25,0.8,0.25,1)] hover:-translate-y-1.5 hover:scale-[1.01]",
        className
      )}
    >
      {/* Dynamic Glow Effect */}
      <div 
        className="absolute -inset-px opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-md pointer-events-none"
        style={{
          background: `radial-gradient(circle at 50% 0%, ${glowColor}, transparent 70%)`
        }}
      />
      
      {/* Noise Texture inside card */}
      <div className="absolute inset-0 z-0 opacity-[0.02] mix-blend-overlay pointer-events-none noise-texture" />

      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
}
