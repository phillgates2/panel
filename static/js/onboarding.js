// Onboarding Tutorial
document.addEventListener('DOMContentLoaded', function() {
    if (!localStorage.getItem('onboarding_complete')) {
        startOnboarding();
    }
});

function startOnboarding() {
    const steps = [
        {
            element: '#main-nav',
            intro: 'Welcome! This is the main navigation bar. Use it to explore different sections.'
        },
        {
            element: '#dashboard',
            intro: 'Here\'s your dashboard. It shows an overview of your activities.'
        },
        {
            element: '#theme-toggle-btn',
            intro: 'Toggle between light and dark modes for better viewing.'
        }
    ];

    let currentStep = 0;

    function showStep() {
        if (currentStep >= steps.length) {
            localStorage.setItem('onboarding_complete', 'true');
            hideOverlay();
            return;
        }

        const step = steps[currentStep];
        const element = document.querySelector(step.element);
        if (element) {
            highlightElement(element);
            showTooltip(element, step.intro + ' (Click to continue)');
        }
    }

    function highlightElement(el) {
        el.style.boxShadow = '0 0 0 4px var(--primary-color)';
        el.style.position = 'relative';
        el.style.zIndex = '9999';
    }

    function hideOverlay() {
        document.querySelectorAll('.highlight').forEach(el => {
            el.style.boxShadow = '';
            el.style.zIndex = '';
        });
    }

    document.addEventListener('click', function() {
        currentStep++;
        showStep();
    });

    showStep();
}