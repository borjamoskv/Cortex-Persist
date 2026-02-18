// MOSKV // Kitchen Artifact Logic
console.log("BLUEPRINT LOADED // SYSTEM_VERSION_2026");

// Simple Clock
function updateClock() {
    const clock = document.getElementById('clock');
    const now = new Date();
    clock.textContent = now.toTimeString().split(' ')[0];
}
setInterval(updateClock, 1000);
updateClock();

// Typographic Reveal
document.addEventListener('DOMContentLoaded', () => {
    const lines = document.querySelectorAll('.line');
    lines.forEach((line, index) => {
        line.style.opacity = '0';
        line.style.transform = 'translateY(20px)';
        setTimeout(() => {
            line.style.transition = 'all 0.8s cubic-bezier(0.16, 1, 0.3, 1)';
            line.style.opacity = '1';
            line.style.transform = 'translateY(0)';
        }, 200 + (index * 150));
    });
});

// Interactive hover effect for the main title
const title = document.querySelector('.main-title');
document.addEventListener('mousemove', (e) => {
    const x = e.clientX / window.innerWidth;
    const y = e.clientY / window.innerHeight;
    
    // Subtle shift
    title.style.transform = `translate(${(x - 0.5) * 10}px, ${(y - 0.5) * 10}px)`;
});
