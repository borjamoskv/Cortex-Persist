import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

export function BackgroundEffects() {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePos({
        x: e.clientX,
        y: e.clientY
      });
    };
    
    globalThis.addEventListener('mousemove', handleMouseMove);
    return () => globalThis.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <>
      <div className="crt-scanline" />
      <div className="crt-glow" />
      
      {/* Dynamic Cursor Light */}
      <motion.div 
        className="fixed inset-0 pointer-events-none z-[1] mix-blend-screen"
        animate={{
          background: `radial-gradient(circle 600px at ${mousePos.x}px ${mousePos.y}px, rgba(204, 255, 0, 0.03), transparent 80%)`
        }}
        transition={{ type: "tween", ease: "linear", duration: 0.1 }}
      />
    </>
  );
}
