// @C5-REAL
import React, { useEffect, useRef, useState } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface AwwwardsFadeInProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  direction?: 'up' | 'down' | 'left' | 'right' | 'none';
  duration?: number;
}

export default function AwwwardsFadeIn({ 
  children, 
  className, 
  delay = 0, 
  direction = 'up',
  duration = 0.8 
}: AwwwardsFadeInProps) {
  const [isInView, setIsInView] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.1, rootMargin: "-10% 0px" }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, []);

  const getDirectionClass = () => {
    if (isInView) return 'opacity-100 translate-x-0 translate-y-0';
    switch (direction) {
      case 'up': return 'opacity-0 translate-y-10';
      case 'down': return 'opacity-0 -translate-y-10';
      case 'left': return 'opacity-0 translate-x-10';
      case 'right': return 'opacity-0 -translate-x-10';
      case 'none': return 'opacity-0';
      default: return 'opacity-0 translate-y-10';
    }
  };

  return (
    <div
      ref={ref}
      className={cn(
        "transition-all ease-[cubic-bezier(0.21,0.47,0.32,0.98)]",
        getDirectionClass(),
        className
      )}
      style={{
        transitionDuration: `${duration}s`,
        transitionDelay: `${delay}s`,
      }}
    >
      {children}
    </div>
  );
}
