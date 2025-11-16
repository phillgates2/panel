/**
 * Browser Detection and Compatibility System
 * Detects browser type, version, and OS, then applies appropriate CSS classes and adjustments
 */

(function() {
  'use strict';

  // Browser Detection
  const BrowserDetect = {
    // User agent string
    ua: navigator.userAgent,
    
    // Browser information
    browser: {
      name: 'Unknown',
      version: 0,
      engine: 'Unknown'
    },
    
    // OS information
    os: {
      name: 'Unknown',
      version: ''
    },
    
    // Feature detection
    features: {
      touch: false,
      webgl: false,
      serviceworker: false,
      websockets: false,
      flexbox: false,
      grid: false,
      customprops: false
    },
    
    /**
     * Detect browser name and version
     */
    detectBrowser: function() {
      const ua = this.ua;
      
      // Edge (Chromium-based)
      if (/Edg\//.test(ua)) {
        this.browser.name = 'Edge';
        this.browser.version = parseFloat(ua.match(/Edg\/([\d.]+)/)[1]);
        this.browser.engine = 'Blink';
      }
      // Opera
      else if (/OPR\//.test(ua) || /Opera\//.test(ua)) {
        this.browser.name = 'Opera';
        this.browser.version = parseFloat((ua.match(/OPR\/([\d.]+)/) || ua.match(/Opera\/([\d.]+)/))[1]);
        this.browser.engine = 'Blink';
      }
      // Chrome
      else if (/Chrome\//.test(ua) && !/Edg\//.test(ua)) {
        this.browser.name = 'Chrome';
        this.browser.version = parseFloat(ua.match(/Chrome\/([\d.]+)/)[1]);
        this.browser.engine = 'Blink';
      }
      // Safari
      else if (/Safari\//.test(ua) && !/Chrome\//.test(ua)) {
        this.browser.name = 'Safari';
        const match = ua.match(/Version\/([\d.]+)/);
        this.browser.version = match ? parseFloat(match[1]) : 0;
        this.browser.engine = 'WebKit';
      }
      // Firefox
      else if (/Firefox\//.test(ua)) {
        this.browser.name = 'Firefox';
        this.browser.version = parseFloat(ua.match(/Firefox\/([\d.]+)/)[1]);
        this.browser.engine = 'Gecko';
      }
      // Internet Explorer
      else if (/MSIE|Trident\//.test(ua)) {
        this.browser.name = 'IE';
        const match = ua.match(/MSIE ([\d.]+)/) || ua.match(/rv:([\d.]+)/);
        this.browser.version = match ? parseFloat(match[1]) : 0;
        this.browser.engine = 'Trident';
      }
      // Brave (difficult to detect, uses Chrome UA)
      else if (navigator.brave && navigator.brave.isBrave) {
        this.browser.name = 'Brave';
        this.browser.version = parseFloat(ua.match(/Chrome\/([\d.]+)/)[1]);
        this.browser.engine = 'Blink';
      }
      
      return this.browser;
    },
    
    /**
     * Detect operating system
     */
    detectOS: function() {
      const ua = this.ua;
      
      if (/Windows NT 10/.test(ua)) {
        this.os.name = 'Windows';
        this.os.version = '10/11';
      } else if (/Windows NT 6.3/.test(ua)) {
        this.os.name = 'Windows';
        this.os.version = '8.1';
      } else if (/Windows NT 6.2/.test(ua)) {
        this.os.name = 'Windows';
        this.os.version = '8';
      } else if (/Windows NT 6.1/.test(ua)) {
        this.os.name = 'Windows';
        this.os.version = '7';
      } else if (/Windows/.test(ua)) {
        this.os.name = 'Windows';
        this.os.version = 'Other';
      } else if (/Mac OS X ([\d_]+)/.test(ua)) {
        this.os.name = 'macOS';
        const match = ua.match(/Mac OS X ([\d_]+)/);
        this.os.version = match ? match[1].replace(/_/g, '.') : '';
      } else if (/Android ([\d.]+)/.test(ua)) {
        this.os.name = 'Android';
        const match = ua.match(/Android ([\d.]+)/);
        this.os.version = match ? match[1] : '';
      } else if (/iPhone|iPad|iPod/.test(ua)) {
        this.os.name = 'iOS';
        const match = ua.match(/OS ([\d_]+)/);
        this.os.version = match ? match[1].replace(/_/g, '.') : '';
      } else if (/Linux/.test(ua)) {
        this.os.name = 'Linux';
      } else if (/FreeBSD/.test(ua)) {
        this.os.name = 'FreeBSD';
      } else if (/CrOS/.test(ua)) {
        this.os.name = 'ChromeOS';
      }
      
      return this.os;
    },
    
    /**
     * Detect browser features and capabilities
     */
    detectFeatures: function() {
      // Touch support
      this.features.touch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      
      // WebGL support
      try {
        const canvas = document.createElement('canvas');
        this.features.webgl = !!(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'));
      } catch(e) {
        this.features.webgl = false;
      }
      
      // Service Worker support
      this.features.serviceworker = 'serviceWorker' in navigator;
      
      // WebSocket support
      this.features.websockets = 'WebSocket' in window;
      
      // CSS Flexbox support
      this.features.flexbox = CSS.supports('display', 'flex');
      
      // CSS Grid support
      this.features.grid = CSS.supports('display', 'grid');
      
      // CSS Custom Properties support
      this.features.customprops = CSS.supports('--test', '0');
      
      return this.features;
    },
    
    /**
     * Check if browser is mobile
     */
    isMobile: function() {
      return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(this.ua);
    },
    
    /**
     * Check if browser is tablet
     */
    isTablet: function() {
      return /(iPad|Android(?!.*Mobile))/.test(this.ua);
    },
    
    /**
     * Initialize detection and apply classes
     */
    init: function() {
      this.detectBrowser();
      this.detectOS();
      this.detectFeatures();
      
      const root = document.documentElement;
      const body = document.body;
      
      // Add browser classes
      root.classList.add('browser-' + this.browser.name.toLowerCase());
      root.classList.add('browser-v' + Math.floor(this.browser.version));
      root.classList.add('engine-' + this.browser.engine.toLowerCase());
      
      // Add OS classes
      root.classList.add('os-' + this.os.name.toLowerCase().replace(/\s+/g, '-'));
      
      // Add device type classes
      if (this.isMobile()) {
        root.classList.add('device-mobile');
      } else if (this.isTablet()) {
        root.classList.add('device-tablet');
      } else {
        root.classList.add('device-desktop');
      }
      
      // Add feature classes
      if (this.features.touch) root.classList.add('has-touch');
      if (this.features.webgl) root.classList.add('has-webgl');
      if (!this.features.flexbox) root.classList.add('no-flexbox');
      if (!this.features.grid) root.classList.add('no-grid');
      if (!this.features.customprops) root.classList.add('no-custom-props');
      
      // Store in data attributes for CSS access
      root.setAttribute('data-browser', this.browser.name);
      root.setAttribute('data-browser-version', Math.floor(this.browser.version));
      root.setAttribute('data-os', this.os.name);
      root.setAttribute('data-engine', this.browser.engine);
      
      // Apply browser-specific fixes
      this.applyFixes();
      
      // Log detection info (dev mode only)
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.log('🌐 Browser Detection:', {
          browser: this.browser,
          os: this.os,
          features: this.features,
          mobile: this.isMobile(),
          tablet: this.isTablet()
        });
      }
      
      return this;
    },
    
    /**
     * Apply browser-specific fixes and adjustments
     */
    applyFixes: function() {
      // IE11 and older - show warning
      if (this.browser.name === 'IE') {
        this.showBrowserWarning('Internet Explorer is not supported. Please use a modern browser like Chrome, Firefox, Edge, or Safari.');
      }
      
      // Old Safari - smooth scroll fix
      if (this.browser.name === 'Safari' && this.browser.version < 15.4) {
        document.documentElement.style.scrollBehavior = 'auto';
      }
      
      // iOS Safari - viewport height fix for bottom bars
      if (this.os.name === 'iOS') {
        const setVH = () => {
          const vh = window.innerHeight * 0.01;
          document.documentElement.style.setProperty('--vh', `${vh}px`);
        };
        setVH();
        window.addEventListener('resize', setVH);
      }
      
      // Firefox - smooth scrolling enhancement
      if (this.browser.name === 'Firefox') {
        document.documentElement.style.scrollBehavior = 'smooth';
      }
    },
    
    /**
     * Show browser compatibility warning
     */
    showBrowserWarning: function(message) {
      const warning = document.createElement('div');
      warning.className = 'browser-warning';
      warning.innerHTML = `
        <div class="browser-warning-content">
          <strong>⚠️ Browser Compatibility Warning</strong>
          <p>${message}</p>
          <button onclick="this.parentElement.parentElement.remove()">Dismiss</button>
        </div>
      `;
      document.body.insertBefore(warning, document.body.firstChild);
    }
  };
  
  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      BrowserDetect.init();
    });
  } else {
    BrowserDetect.init();
  }
  
  // Expose globally for debugging
  window.BrowserDetect = BrowserDetect;
  
})();
