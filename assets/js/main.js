(() => {
  // Mobile navigation toggle
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector("#site-nav");
  
  if (toggle && nav) {
    const setExpanded = (isOpen) => {
      toggle.setAttribute("aria-expanded", String(isOpen));
      nav.classList.toggle("open", isOpen);
      
      // Prevent body scroll when menu is open on mobile
      if (isOpen) {
        document.body.style.overflow = 'hidden';
      } else {
        document.body.style.overflow = '';
      }
    };

    toggle.addEventListener("click", () => {
      const isOpen = toggle.getAttribute("aria-expanded") === "true";
      setExpanded(!isOpen);
    });

    // Close menu when a link is clicked
    nav.addEventListener("click", (e) => {
      const target = e.target;
      if (target && target.matches("a")) {
        setExpanded(false);
      }
    });

    // Close on escape key
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        setExpanded(false);
      }
    });

    // Close when switching to desktop layout
    const mq = window.matchMedia("(min-width: 860px)");
    const handleResize = () => {
      if (mq.matches) {
        setExpanded(false);
      }
    };
    
    if (mq.addEventListener) {
      mq.addEventListener("change", handleResize);
    } else if (mq.addListener) {
      // Fallback for older browsers
      mq.addListener(handleResize);
    }
  }

  // Header shadow on scroll
  const header = document.querySelector(".site-header");
  if (header) {
    let ticking = false;
    
    const updateHeaderShadow = () => {
      const scrolled = window.scrollY > 10;
      header.classList.toggle("scrolled", scrolled);
      ticking = false;
    };

    window.addEventListener("scroll", () => {
      if (!ticking) {
        window.requestAnimationFrame(updateHeaderShadow);
        ticking = true;
      }
    });
  }

  // Sticky download CTA
  const createStickyDownload = () => {
    // Only create on pages that aren't the download page
    const isDownloadPage = window.location.pathname.includes('download.html');
    if (isDownloadPage) return;

    // Check if sticky bar already exists
    if (document.querySelector('.sticky-download')) return;

    const stickyBar = document.createElement('div');
    stickyBar.className = 'sticky-download';
    stickyBar.setAttribute('role', 'banner');
    stickyBar.setAttribute('aria-label', 'Download call to action');
    
    stickyBar.innerHTML = `
      <div class="container">
        <div class="sticky-download-text">
          Get PDA Support Today
          <span>— Available now on the App Store</span>
        </div>
        <a href="download.html" class="btn">Download Now</a>
      </div>
    `;
    
    document.body.appendChild(stickyBar);

    // Show sticky bar after scrolling down
    let lastScrollY = window.scrollY;
    let ticking = false;
    const scrollThreshold = 400; // Show after scrolling 400px down

    const updateStickyBar = () => {
      const currentScrollY = window.scrollY;
      const shouldShow = currentScrollY > scrollThreshold;
      
      stickyBar.classList.toggle('visible', shouldShow);
      
      lastScrollY = currentScrollY;
      ticking = false;
    };

    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(updateStickyBar);
        ticking = true;
      }
    });
  };

  // Initialize sticky download on page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createStickyDownload);
  } else {
    createStickyDownload();
  }

  // Smooth scroll for anchor links (if any are added later)
  document.addEventListener('click', (e) => {
    const target = e.target;
    if (target && target.matches('a[href^="#"]')) {
      const href = target.getAttribute('href');
      if (href === '#') return;
      
      const targetElement = document.querySelector(href);
      if (targetElement) {
        e.preventDefault();
        targetElement.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
        
        // Update URL without jumping
        history.pushState(null, null, href);
        
        // Focus the target for accessibility
        targetElement.setAttribute('tabindex', '-1');
        targetElement.focus();
      }
    }
  });

  // Add subtle fade-in animation for cards
  const observeCards = () => {
    const cards = document.querySelectorAll('.card, .testimonial');
    
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.style.opacity = '0';
            entry.target.style.transform = 'translateY(20px)';
            
            // Trigger animation
            setTimeout(() => {
              entry.target.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
              entry.target.style.opacity = '1';
              entry.target.style.transform = 'translateY(0)';
            }, 100);
            
            observer.unobserve(entry.target);
          }
        });
      }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
      });

      cards.forEach(card => observer.observe(card));
    }
  };

  // Only run animations if user hasn't requested reduced motion
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (!prefersReducedMotion.matches) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', observeCards);
    } else {
      observeCards();
    }
  }

  // Keyboard navigation improvements
  document.addEventListener('keydown', (e) => {
    // Allow Escape to close any open interactive elements
    if (e.key === 'Escape') {
      // Close mobile menu (already handled above)
      // Could add more escape handlers here for modals, etc.
    }
  });

  // Add focus styles for keyboard navigation
  let isUsingKeyboard = false;
  
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      isUsingKeyboard = true;
      document.body.classList.add('keyboard-nav');
    }
  });
  
  document.addEventListener('mousedown', () => {
    isUsingKeyboard = false;
    document.body.classList.remove('keyboard-nav');
  });

})();
