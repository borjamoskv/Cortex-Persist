(() => {
  const MoskvDOMLeads = {
    findLeads: () => {
      console.log(`[MOSKV-1] Escaneando DOM para extraer prospectos...`);
      // Selectors for LinkedIn Sales Navigator, LinkedIn search, and generic lists
      const selectors = [
        'a[data-anonymize="person-name"]', // Sales Nav name link
        'span.entity-result__title-text a', // LinkedIn Search name
        'a.app-aware-link', // Generic LinkedIn profile link
        'div.lead-name a',
        '[data-testid="User-Name"] a', // Twitter user name sub-anchor
        'a[data-testid="User-Name"]' // Twitter user name anchor itself
      ];
      
      const elements = Array.from(document.querySelectorAll(selectors.join(',')));
      const leads = [];
      const seen = new Set();
      
      elements.forEach(el => {
        const name = el.textContent?.trim().replace(/\n/g, ' ');
        const href = el.getAttribute('href');
        if (name && href && (href.includes('/in/') || href.includes('/sales/people/') || href.includes('twitter.com/') || href.includes('x.com/'))) {
          const absoluteUrl = href.startsWith('http') ? href : window.location.origin + href;
          if (!seen.has(absoluteUrl)) {
            seen.add(absoluteUrl);
            leads.push({
              name: name,
              url: absoluteUrl,
              timestamp: new Date().toISOString()
            });
          }
        }
      });
      
      return leads;
    },

    executeLoop: function() {
      console.log(`[MOSKV-1] Iniciando extracción de leads en el DOM...`);
      const leads = this.findLeads();
      console.log(`[MOSKV-1] Extracción completada. leads_count=${leads.length}`);
      return JSON.stringify(leads, null, 2);
    }
  };

  return MoskvDOMLeads.executeLoop();
})();
