/**
 * Loading States Management
 * Provides client-side loading indicators for better UX
 */

class LoadingManager {
    constructor() {
        this.activeLoadings = new Set();
    }

    /**
     * Show loading indicator for an element
     * @param {string|Element} element - Element or selector to show loading for
     * @param {Object} options - Loading options
     */
    show(element, options = {}) {
        const el = typeof element === 'string' ? document.querySelector(element) : element;
        if (!el) return;

        const {
            text = 'Loading...',
            size = 'md',
            overlay = false,
            spinner = 'border'
        } = options;

        // Prevent multiple loading states on same element
        const key = el.id || el.className || Math.random().toString(36);
        if (this.activeLoadings.has(key)) return;
        this.activeLoadings.add(key);

        // Create loading container
        const loadingContainer = document.createElement('div');
        loadingContainer.className = `loading-container loading-${size}`;
        loadingContainer.setAttribute('role', 'status');
        loadingContainer.setAttribute('aria-live', 'polite');

        // Create spinner
        const spinnerEl = document.createElement('div');
        spinnerEl.className = `spinner-${spinner} text-primary`;
        spinnerEl.setAttribute('aria-hidden', 'true');

        // Create text
        const textEl = document.createElement('span');
        textEl.className = 'loading-text ms-2';
        textEl.textContent = text;

        // Assemble
        loadingContainer.appendChild(spinnerEl);
        loadingContainer.appendChild(textEl);

        // Handle overlay
        if (overlay) {
            loadingContainer.className += ' loading-overlay';
            el.style.position = el.style.position || 'relative';
            el.appendChild(loadingContainer);
        } else {
            // Replace content or add to end
            el.innerHTML = '';
            el.appendChild(loadingContainer);
        }

        // Store reference for cleanup
        el._loadingContainer = loadingContainer;
        el._loadingKey = key;
    }

    /**
     * Hide loading indicator for an element
     * @param {string|Element} element - Element or selector to hide loading for
     */
    hide(element) {
        const el = typeof element === 'string' ? document.querySelector(element) : element;
        if (!el || !el._loadingContainer) return;

        // Remove loading container
        if (el._loadingContainer.parentNode) {
            el._loadingContainer.parentNode.removeChild(el._loadingContainer);
        }

        // Clean up references
        this.activeLoadings.delete(el._loadingKey);
        delete el._loadingContainer;
        delete el._loadingKey;
    }

    /**
     * Show global loading overlay
     * @param {string} text - Loading text
     */
    showGlobal(text = 'Loading...') {
        let overlay = document.getElementById('global-loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'global-loading-overlay';
            overlay.className = 'global-loading-overlay';
            overlay.innerHTML = `
                <div class="global-loading-content">
                    <div class="spinner-border text-primary" role="status" aria-hidden="true"></div>
                    <span class="loading-text ms-2">${text}</span>
                </div>
            `;
            document.body.appendChild(overlay);
        }
        overlay.style.display = 'flex';
    }

    /**
     * Hide global loading overlay
     */
    hideGlobal() {
        const overlay = document.getElementById('global-loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
}

// Global loading manager instance
const loadingManager = new LoadingManager();

// Convenience functions
function showLoading(element, options) {
    loadingManager.show(element, options);
}

function hideLoading(element) {
    loadingManager.hide(element);
}

function showGlobalLoading(text) {
    loadingManager.showGlobal(text);
}

function hideGlobalLoading() {
    loadingManager.hideGlobal();
}

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add loading styles if not present
    if (!document.getElementById('loading-styles')) {
        const style = document.createElement('style');
        style.id = 'loading-styles';
        style.textContent = `
            .loading-container {
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 1rem;
            }

            .loading-container.loading-sm {
                padding: 0.5rem;
                font-size: 0.875rem;
            }

            .loading-container.loading-lg {
                padding: 2rem;
                font-size: 1.25rem;
            }

            .loading-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(255, 255, 255, 0.8);
                backdrop-filter: blur(2px);
                z-index: 1000;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .global-loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(4px);
                z-index: 9999;
                display: none;
                align-items: center;
                justify-content: center;
            }

            .global-loading-content {
                background: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .loading-text {
                font-weight: 500;
                color: #6c757d;
            }

            /* Dark mode support */
            @media (prefers-color-scheme: dark) {
                .loading-overlay {
                    background: rgba(33, 37, 41, 0.8);
                }

                .global-loading-content {
                    background: #343a40;
                    color: white;
                }

                .loading-text {
                    color: #adb5bd;
                }
            }
        `;
        document.head.appendChild(style);
    }
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { LoadingManager, loadingManager, showLoading, hideLoading, showGlobalLoading, hideGlobalLoading };
}