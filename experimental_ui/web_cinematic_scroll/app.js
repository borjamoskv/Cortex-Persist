gsap.registerPlugin(ScrollTrigger);

// Utility function for Wow 7: Fibonacci Jumpscare
function isFibonacci(n) {
  if (n <= 0) return false;
  let a = 0;
  let b = 1;
  while (b < n) {
    const temp = a;
    a = b;
    b = temp + b;
  }
  return b === n;
}

document.addEventListener("DOMContentLoaded", () => {
  
  const video = document.getElementById("bg-video");
  const scrollContainer = document.getElementById("scroll-container");
  const scrollWrapper = document.getElementById("scroll-wrapper");

  // Wow 1: Custom Inverted Cursor (Blend Mode)
  const cursor = document.createElement('div');
  cursor.classList.add('custom-cursor');
  document.body.appendChild(cursor);

  document.addEventListener('mousemove', (e) => {
    gsap.to(cursor, {
      x: e.clientX,
      y: e.clientY,
      duration: 0.1,
      ease: "power2.out"
    });
  });

  // Ensure video is loaded enough to know its duration
  video.onloadedmetadata = () => {
    initScrollToPlay(video.duration);
  };

  if (video.readyState >= 1) {
    initScrollToPlay(video.duration);
  } else {
    setTimeout(() => {
      if (!isInitialized) initScrollToPlay(10); 
    }, 2000);
  }

  let isInitialized = false;

  function initScrollToPlay(duration) {
    if (isInitialized) return;
    isInitialized = true;
    
    video.pause();

    function getScrollAmount() {
      let scrollWidth = scrollWrapper.scrollWidth;
      return -(scrollWidth - window.innerWidth);
    }

    // Horizontal Scroll Tween
    const tween = gsap.to(scrollWrapper, {
      x: getScrollAmount,
      ease: "none"
    });

    ScrollTrigger.create({
      trigger: scrollContainer,
      start: "top top",
      end: () => `+=${getScrollAmount() * -1}`, 
      pin: true,
      animation: tween,
      scrub: 1, // Increased scrub for smoother, heavier feel (Wow 2)
      invalidateOnRefresh: true,
    });

    // Video Scroll Sync
    ScrollTrigger.create({
      trigger: scrollContainer,
      start: "top top",
      end: () => `+=${getScrollAmount() * -1}`,
      scrub: 0.5,
      onUpdate: (self) => {
        const targetTime = self.progress * (duration - 0.1); 
        if (targetTime !== undefined && !isNaN(targetTime)) {
             video.currentTime = targetTime;
        }
      }
    });

    // Wow 3: Kinetic Text Reveal (Hero)
    gsap.from(".hero .title", {
      y: 100,
      opacity: 0,
      duration: 1.5,
      ease: "expo.out",
      delay: 0.5
    });

    // Wow 4: Parallax Images
    gsap.utils.toArray(".image-waypoint").forEach((panel) => {
      const img = panel.querySelector("img");
      
      // We calculate the parallax horizontally since we are scrolling horizontally
      gsap.to(img, {
        xPercent: 20, // Move image 20% to the right inside its container
        ease: "none",
        scrollTrigger: {
          trigger: panel,
          containerAnimation: tween, // Important: tie it to the horizontal tween
          start: "left right", // When the panel's left hits the viewport's right
          end: "right left",   // When the panel's right hits the viewport's left
          scrub: true
        }
      });

      // Wow 5: Scale Up on Enter
      gsap.from(panel.querySelector(".image-wrapper"), {
        scale: 0.8,
        opacity: 0.5,
        duration: 1,
        ease: "power3.out",
        scrollTrigger: {
          trigger: panel,
          containerAnimation: tween,
          start: "left center", // Trigger when the panel reaches the center of screen
          toggleActions: "play reverse play reverse"
        }
      });
    });

    // Wow 6: Magnetic Hover Elements
    const magneticElements = document.querySelectorAll('.glass-box, .image-wrapper');
    magneticElements.forEach((el) => {
      el.addEventListener('mousemove', (e) => {
        const rect = el.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const dx = e.clientX - centerX;
        const dy = e.clientY - centerY;
        
        gsap.to(el, {
          x: dx * 0.1,
          y: dy * 0.1,
          duration: 0.5,
          ease: "power2.out"
        });
      });
      el.addEventListener('mouseleave', () => {
        gsap.to(el, {
          x: 0,
          y: 0,
          duration: 0.8,
          ease: "elastic.out(1, 0.3)"
        });
      });
    });

    // Wow 7: Golden Ratio / Fibonacci Jumpscare & Click Marks
    let clickCount = 0;
    const jumpscareOverlay = document.getElementById('jumpscare');
    const jumpscareImg = document.getElementById('jumpscare-img');
    const jumpscares = [
      "../../borjamoskv_site/img/desagradable_elon.png",
      "../../borjamoskv_site/img/nano_porro_perfecto.png",
      "../../borjamoskv_site/img/nano_tanga_limon.png",
      "../../borjamoskv_site/img/nano_gitano_humor.png"
    ];

    document.addEventListener('click', (e) => {
      // 7A: Create permanent mark (.puntazo)
      const puntazo = document.createElement('div');
      puntazo.classList.add('puntazo');
      puntazo.style.left = e.clientX + 'px';
      puntazo.style.top = e.clientY + 'px';
      document.body.appendChild(puntazo);

      clickCount++;

      // 7B: Fibonacci Jumpscare Trigger
      // Trigger safely starting from hit 2
      if (isFibonacci(clickCount) && clickCount > 1) { 
        // Randomize image
        const imgPath = jumpscares[Math.floor(Math.random() * jumpscares.length)];
        jumpscareImg.src = imgPath;
        
        // Flash it
        jumpscareOverlay.classList.add('active');
        
        // Minimal timeout for extreme subliminal impact (O(1) perception)
        setTimeout(() => {
          jumpscareOverlay.classList.remove('active');
        }, 120); 
      }
    });

  }
});
