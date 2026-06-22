(() => {
  const MoskvDOM = {
    findTarget: (selectorOrText) => {
      const selectors = ['div[data-testid="tweetTextarea_0"]', 'div[data-testid="tweetButtonInline"]', 'div[data-testid="tweetButton"]', '[role="button"]'];
      const elements = Array.from(document.querySelectorAll(selectors.join(',')));
      
      const exact = elements.find(el => el.textContent?.trim() === selectorOrText || el.value === selectorOrText || el.getAttribute('data-testid') === selectorOrText);
      if (exact) return exact;

      return elements.find(el => el.textContent?.trim().includes(selectorOrText));
    },

    clickTarget: (element) => {
      console.log(`[MOSKV-1] Mutando nodo:`, element);
      const events = ['mousedown', 'mouseup', 'click'];
      events.forEach(eventType => {
        element.dispatchEvent(new MouseEvent(eventType, { bubbles: true, cancelable: true, view: window }));
      });
    },

    sleep: (ms) => new Promise(resolve => setTimeout(resolve, ms)),

    fillTextArea: function(targetText, content) {
      const target = this.findTarget(targetText);
      if (target) {
          console.log(`[MOSKV-1] Rellenando nodo de texto...`);
          // React 16+ workaround for updating text in contenteditable/textarea
          target.focus();
          document.execCommand('insertText', false, content);
          target.dispatchEvent(new Event('input', { bubbles: true }));
          return true;
      }
      return false;
    },

    executeLoop: async function() {
      console.log(`[MOSKV-1] Iniciando secuencia de ejecución C5-REAL para Broadcast`);
      
      const manifesto = `CORTEX-PERSIST: LA SINGULARIDAD OUROBOROS
"CERO ANERGÍA ES LA MUERTE."

El Green Theater ha fracasado. El Context Rot asfixia a los LLMs. CORTEX-Persist es un firewall termodinámico para código generado por IA. Erradica la limerencia epistémica y transforma la estocasticidad en invariantes verificables (C5-REAL).

- BABYLON-60 (Causal Engine)
- Git Sentinel (Ledger Inmutable)
- Zero Fluff. 

La época de los Copilots ha terminado.
[Hash de Integridad Kernel: 57562bbda]
#C5-REAL #AgenticAI #CortexPersist`;

      // 1. Fill the compose textarea
      console.log(`[MOSKV-1] Buscando textarea de X...`);
      let filled = false;
      for (let i = 0; i < 5; i++) {
          filled = this.fillTextArea('tweetTextarea_0', manifesto);
          if (filled) break;
          await this.sleep(2000);
      }
      
      if (!filled) {
          return { success: false, reason: "Textarea no encontrado." };
      }

      await this.sleep(1500);

      // 2. Click Post (Tweet)
      console.log(`[MOSKV-1] Buscando botón Post...`);
      let clicked = false;
      for (let i = 0; i < 5; i++) {
          const postBtn = this.findTarget('tweetButtonInline') || this.findTarget('Post') || this.findTarget('Postear');
          if (postBtn) {
              this.clickTarget(postBtn);
              clicked = true;
              break;
          }
          await this.sleep(2000);
      }

      if (!clicked) {
          return { success: false, reason: "Botón Post no encontrado." };
      }

      await this.sleep(3000);
      console.log(`[MOSKV-1] Broadcast Exitoso.`);
      return { success: true };
    }
  };

  return MoskvDOM.executeLoop();
})();
