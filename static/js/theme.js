(function() {
    // Function to apply the theme
    function applyTheme(theme) {
        document.documentElement.dataset.theme = theme;
        localStorage.setItem('theme', theme);
    }

    // Function to get preferred theme
    function getPreferredTheme() {
        // 1. Check local storage
        const storedTheme = localStorage.getItem('theme');
        if (storedTheme) {
            return storedTheme;
        }

        // 2. Check system preference
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)');
        if (systemPrefersDark.matches) {
            return 'dark';
        }

        // 3. Default to light
        return 'light';
    }

    // Apply the theme on initial load
    const initialTheme = getPreferredTheme();
    applyTheme(initialTheme);

    // Optional: You can add a button later to call this function
    window.toggleTheme = function() {
        const currentTheme = document.documentElement.dataset.theme || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        applyTheme(newTheme);
    }
})();