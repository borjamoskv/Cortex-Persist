import { useRef, useEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export default function PanoramicOuroboros() {
  const containerRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !ringRef.current) return;

    const ctx = gsap.context(() => {
      // 8x scroll duration
      ScrollTrigger.create({
        trigger: containerRef.current,
        start: "top top",
        end: "+=800%", 
        pin: true,
        animation: gsap.to(ringRef.current, {
          rotationY: -360,
          ease: "none"
        }),
        scrub: 1, // Smooth dampening
      });
    }, containerRef);

    return () => ctx.revert();
  }, []);

  // Using real artworks from the public folder
  const artPanels = [
    { src: '/artworks/101549487_628782907708753_7125389685821132908_n.jpg', text: 'NIHIL' },
    { src: '/artworks/119955685_1990522601249282_8870928824701066432_n.jpg', text: 'VOID' },
    { src: '/artworks/135416275_422684262495279_427569959808682920_n.jpg', text: 'CARNE' },
    { src: '/artworks/136071070_876820339796009_2596570326950532412_n.jpg', text: 'AUREA' },
    { src: '/artworks/143780702_256050945962164_8413509095668583723_n.jpg', text: 'ROSA' },
    { src: '/artworks/152488927_1162588127511226_283068153373529688_n.jpg', text: 'MUTRA' },
  ];

  return (
    <section 
      ref={containerRef} 
      className="h-screen w-full relative overflow-hidden bg-[#0A0A0A] flex items-center justify-center [perspective:2000px]"
    >
      <div 
        ref={ringRef} 
        className="relative w-full h-full flex items-center justify-center [transform-style:preserve-3d]"
      >
        {artPanels.map((panel, idx) => {
          // Calculate the angle for each panel to form a continuous cylinder/ring
          const angle = (360 / artPanels.length) * idx;
          // Translate Z needs to be large enough to push panels outward into a ring
          const radius = "1200px"; 

          return (
            <div 
              key={`panel-${panel.text}`}
              className="absolute w-[80vw] md:w-[40vw] h-[60vh] flex flex-col items-center justify-center opacity-80"
              style={{
                transform: `rotateY(${angle}deg) translateZ(${radius})`
              }}
            >
              <img 
                src={panel.src} 
                alt={panel.text} 
                className="w-full h-full object-cover filter grayscale hover:grayscale-0 transition-all duration-700"
              />
              <h3 className="text-4xl md:text-[6vw] font-black text-[#CCFF00] mt-8 tracking-[0.2em] font-display uppercase">
                {panel.text}
              </h3>
            </div>
          );
        })}
      </div>

      {/* Central Axis Text */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10 pointer-events-none mix-blend-difference">
        <h2 className="text-white text-[20vw] font-black opacity-10 leading-none">
          360°
        </h2>
      </div>
    </section>
  );
}
