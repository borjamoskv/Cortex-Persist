document.addEventListener("DOMContentLoaded", () => {
    // Reveal animations using IntersectionObserver
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.15
    };

    const handleIntersect = (entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Determine animation delay if element has a '--delay' custom property
                const delayStr = entry.target.style.getPropertyValue('--delay');
                const delay = delayStr ? parseFloat(delayStr) * 150 : 0;
                
                setTimeout(() => {
                    entry.target.classList.add('visible');
                }, delay);
                
                // Stop observing after reveal
                observer.unobserve(entry.target);
            }
        });
    };

    const observer = new IntersectionObserver(handleIntersect, observerOptions);

    // Initial load fade-in nav
    const nav = document.querySelector('.top-nav');
    if(nav) setTimeout(() => nav.classList.add('visible'), 100);

    // Observe all components marked for reveal
    const elementsToReveal = document.querySelectorAll('.fade-in, .reveal-item');
    elementsToReveal.forEach(el => observer.observe(el));
    
    // Minimalist parallax for scanlines (ties into Industrial Noir scroll-as-timeline effect)
    window.addEventListener('scroll', () => {
        requestAnimationFrame(() => {
            const scrolled = window.scrollY;
            const scanlines = document.querySelector('.scanlines');
            if (scanlines) {
                scanlines.style.transform = `translateY(${scrolled * 0.15}px)`;
            }
        });
    }, { passive: true });
});
