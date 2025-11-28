// Dark Mode Toggle Script
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.createElement('div');
    themeToggle.className = 'theme-toggle';
    themeToggle.innerHTML = '<button id="theme-toggle-btn">?? Dark Mode</button>';
    document.body.appendChild(themeToggle);

    const toggleBtn = document.getElementById('theme-toggle-btn');
    const currentTheme = localStorage.getItem('theme') || 'light';

    // Set initial theme
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateToggleButton(currentTheme);

    toggleBtn.addEventListener('click', function() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateToggleButton(newTheme);

        // Send to server to save preference
        fetch('/api/user/theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ theme: newTheme })
        });
    });

    function updateToggleButton(theme) {
        toggleBtn.textContent = theme === 'dark' ? '?? Light Mode' : '?? Dark Mode';
    }
});

// Accessibility: Keyboard navigation
document.addEventListener('keydown', function(e) {
    if (e.key === 'Tab') {
        document.body.classList.add('keyboard-navigation');
    }
});

document.addEventListener('mousedown', function() {
    document.body.classList.remove('keyboard-navigation');
});

// Tooltips for better UX
function showTooltip(element, text) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    document.body.appendChild(tooltip);

    const rect = element.getBoundingClientRect();
    tooltip.style.left = rect.left + 'px';
    tooltip.style.top = (rect.top - 30) + 'px';

    setTimeout(() => {
        document.body.removeChild(tooltip);
    }, 2000);
}

// Add tooltips to buttons
document.addEventListener('DOMContentLoaded', function() {
    const buttons = document.querySelectorAll('button[title]');
    buttons.forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            showTooltip(this, this.getAttribute('title'));
        });
    });
});