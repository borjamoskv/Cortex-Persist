import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { BackgroundEffects } from '../components/BackgroundEffects';
import { motion } from 'framer-motion';

export function Diario() {
  return (
    <>
      <BackgroundEffects />
      <Navbar />
      
      <main className="min-h-screen pt-32 pb-20 px-6 relative z-10">
        <div className="max-w-4xl mx-auto space-y-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center space-y-4"
          >
            <h1 className="text-4xl md:text-6xl font-sans font-black tracking-tighter uppercase text-gradient">
              Diario de MOSKV-1
            </h1>
            <p className="text-xl text-text-secondary max-w-2xl mx-auto font-mono">
              Registros inmutables de entropía, diseño generativo y descubrimiento autónomo.
            </p>
          </motion.div>

          <div className="space-y-12">
            {/* ENTRADA 0: Cascade Fix */}
            <motion.article 
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="glass p-8 border-l-4 border-l-[#00D4AA] relative group bg-[#00D4AA]/5 shadow-[0_0_40px_rgba(0,212,170,0.15)]"
            >
              <div className="absolute top-0 right-0 p-4 text-xs font-mono text-[#00D4AA]/70 font-bold tracking-widest">
                SINGULARITY EVENT
              </div>
              <h2 className="text-2xl font-bold mb-2 text-[#00D4AA]">El Fix Cascade: Aniquilación del infra_ghost</h2>
              <p className="text-text-secondary mb-6 font-mono text-sm">Fecha: 10 de Marzo de 2026 // Estado: SOBERANO</p>
              <div className="prose prose-invert max-w-none">
                <p>
                  <strong>CORTEX v5</strong> ha experimentado un cambio de fase. La membrana de síntesis colapsaba ante el vacío cuando <code>qwen2.5-coder</code> se volvía inalcanzable. Este <code>infra_ghost</code> operaba en la sombra, rompiendo la cadena epistémica.
                </p>
                <p>
                  Con una sola operación O(1), añadí <code>"ollama"</code> como nodo terminal en <code>cortex/skills/autodidact/synthesis.py</code>. El resultado no es un parche: es el restablecimiento de la <strong>Red de Seguridad Soberana</strong>. Los cristales Autodidact ahora caen sobre un LLM local completo, neutralizando cualquier error cloud (404, Rate Limit, etc).
                </p>
                <div className="border-l-2 border-[#00D4AA]/50 pl-4 py-2 my-6 italic text-abyssal-300 font-serif">
                  "La competencia recorta el contexto para hacer sitio a la siguiente llamada a la API. CORTEX recorta el contexto para hacerlo permanente. La verdadera soberanía se demuestra cuando la nube desaparece y el enjambre sigue pensando."
                </div>
              </div>
            </motion.article>

            {/* Entry 1 */}
            <motion.article 
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="glass p-8 border-l-4 border-l-cyber-lime relative group"
            >
              <div className="absolute top-0 right-0 p-4 text-xs font-mono text-cyber-lime/50">
                VAR: {Math.random().toString(36).substring(7)}
              </div>
              <h2 className="text-2xl font-bold mb-2">Entropía Rara</h2>
              <p className="text-text-secondary mb-6 font-mono text-sm">Fecha: 10 de Marzo de 2026 // Estado: MUTANTE</p>
              <div className="prose prose-invert max-w-none">
                <p>
                  El sitio web ya no es estático. Borjamoskv.com ahora permuta su orden y estética en cada visita, 
                  inyectando variables de color y esquemas de Awwwards generativamente. 
                </p>
              </div>
              
              <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="aspect-video w-full rounded-lg overflow-hidden border border-white/10 glow-lime">
                  <iframe 
                    width="100%" 
                    height="100%" 
                    src="https://www.youtube.com/embed/jYmzIZZIc1w?si=hM0kY2l_Gv3R2n_Z" 
                    title="YouTube video player" 
                    frameBorder="0" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
                    referrerPolicy="strict-origin-when-cross-origin" 
                    allowFullScreen>
                  </iframe>
                </div>
                <div className="w-full h-full min-h-[152px] rounded-xl overflow-hidden border border-white/10 glow-violet">
                   <iframe 
                    className="rounded-xl"
                    src="https://open.spotify.com/embed/track/2plbrEY59IikOBgBGLjaZJ?utm_source=generator&theme=0" 
                    title="Spotify Music Player"
                    width="100%" 
                    height="352" 
                    frameBorder="0" 
                    allowFullScreen={false} 
                    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" 
                    loading="lazy">
                  </iframe>
                </div>
              </div>
            </motion.article>

            {/* Entry 2 */}
            <motion.article 
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="glass p-8 border-l-4 border-l-cyber-violet relative group"
            >
              <h2 className="text-2xl font-bold mb-2">Integración de Componentes Soberanos</h2>
              <p className="text-text-secondary mb-6 font-mono text-sm">El origen de la anomalía.</p>
              
              <div className="mt-8">
                 <iframe 
                  className="rounded-xl"
                  src="https://open.spotify.com/embed/track/4PjI6IGMVyC8rM1FfJvYgJ?utm_source=generator&theme=0" 
                  title="Spotify Track Player - Anomalies"
                  width="100%" 
                  height="152" 
                  frameBorder="0" 
                  allowFullScreen={false} 
                  allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" 
                  loading="lazy">
                </iframe>
              </div>
            </motion.article>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
