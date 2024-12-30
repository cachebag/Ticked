// Documentation content structure
const docs = {
    sections: [
        {
            title: 'Getting Started',
            items: [
                { 
                    id: 'introduction', 
                    title: 'Intro',
                    type: 'markdown',
                    path: 'intro.md'
                },
                { 
                    id: 'quick-start', 
                    title: 'Quick Start', 
                    type: 'embedded',
                    content: `
# Quick Start Guide

Get up and running in minutes!

\`\`\`javascript
// Example code
const docs = new Docs({
    container: '#app',
    theme: 'light'
});
\`\`\`
                    `
                }
            ]
        },
        {
            title: 'Core Concepts',
            items: [
                { 
                    id: 'basics', 
                    title: 'Basic Concepts',
                    type: 'embedded',
                    content: `# Basic Concepts...` 
                },
                { 
                    id: 'advanced', 
                    title: 'Advanced Usage',
                    type: 'embedded',
                    content: `# Advanced Usage...` 
                }
            ]
        }
    ]
};

// Initialize marked with options
marked.setOptions({
    highlight: function(code, lang) {
        return hljs.highlightAuto(code).value;
    },
    breaks: true
});

// Theme management
const themeManager = {
    init() {
        // Get theme button
        const themeButton = document.getElementById('theme-switch');
        if (!themeButton) {
            console.error('Theme button not found');
            return;
        }

        // Check for saved theme preference or system preference
        const savedTheme = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
        const defaultTheme = savedTheme || (prefersDark.matches ? 'dark' : 'light');
        
        // Initial theme setup
        this.setTheme(defaultTheme);

        // Add system theme change listener
        prefersDark.addEventListener('change', (e) => {
            if (!localStorage.getItem('theme')) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });

        // Add click event listener directly in init
        themeButton.addEventListener('click', () => {
            const currentTheme = document.body.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            this.setTheme(newTheme);
        });
    },

    setTheme(theme) {
        // Set theme on body
        document.body.setAttribute('data-theme', theme);
        // Save to localStorage
        localStorage.setItem('theme', theme);
        // Update button appearance
        const button = document.getElementById('theme-switch');
        if (button) {
            button.textContent = theme === 'dark' ? '☀️' : '🌙';
            button.setAttribute('aria-label', theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
        }
    }
};

// Build sidebar navigation
function buildNavigation() {
    const nav = document.getElementById('sidebar-nav');
    nav.innerHTML = ''; // Clear existing navigation
    
    docs.sections.forEach(section => {
        const sectionEl = document.createElement('div');
        sectionEl.className = 'nav-section';
        
        const titleEl = document.createElement('h2');
        titleEl.className = 'nav-section-title';
        titleEl.textContent = section.title;
        
        const itemsEl = document.createElement('ul');
        itemsEl.className = 'nav-items';
        
        section.items.forEach(item => {
            const li = document.createElement('li');
            li.className = 'nav-item';
            
            const a = document.createElement('a');
            a.href = `#${item.id}`;
            a.className = 'nav-link';
            a.textContent = item.title;
            a.onclick = (e) => {
                e.preventDefault();
                loadPage(item.id);
                updateActiveLink(a);
                if (window.innerWidth <= 768) {
                    toggleSidebar();
                }
            };
            
            li.appendChild(a);
            itemsEl.appendChild(li);
        });
        
        sectionEl.appendChild(titleEl);
        sectionEl.appendChild(itemsEl);
        nav.appendChild(sectionEl);
    });
}

// Update active link in sidebar
function updateActiveLink(clickedLink) {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    clickedLink.classList.add('active');
}

// Load page content
async function loadPage(pageId) {
    const page = docs.sections
        .flatMap(section => section.items)
        .find(item => item.id === pageId);
    
    if (page) {
        let content;
        
        try {
            if (page.type === 'markdown') {
                console.log('Attempting to load:', page.path);
                const response = await fetch(page.path);
                console.log('Response status:', response.status);
                if (!response.ok) {
                    throw new Error(`Failed to load ${page.path} (Status: ${response.status})`);
                }
                content = await response.text();
            } else {
                content = page.content;
            }

            // Check if marked is available
            if (typeof marked === 'undefined') {
                throw new Error('Markdown parser not loaded');
            }

            // Use marked.parse instead of marked directly
            document.getElementById('doc-content').innerHTML = marked.parse(content);
            document.getElementById('breadcrumb').textContent = page.title;
            updateUrl(pageId);
            highlightCode();
        } catch (error) {
            console.error('Error details:', error);
            document.getElementById('doc-content').innerHTML = `
                <h1>Error Loading Page</h1>
                <p>Failed to load the documentation.</p>
                <pre>${error.message}</pre>
            `;
        }
    } else {
        document.getElementById('doc-content').innerHTML = '<h1>Page Not Found</h1>';
    }
}

// Update URL without page reload
function updateUrl(pageId) {
    history.pushState(null, '', `#${pageId}`);
}

// Highlight code blocks
function highlightCode() {
    document.querySelectorAll('pre code').forEach(block => {
        hljs.highlightBlock(block);
    });
}

// Toggle sidebar on mobile
function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('active');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme first
    themeManager.init();
    
    // Build navigation
    buildNavigation();
    
    // Load default page or page from URL hash
    const pageId = window.location.hash.slice(1) || 'introduction';
    loadPage(pageId);
    
    // Set up menu toggle
    document.getElementById('menu-toggle').addEventListener('click', toggleSidebar);
    
    // Handle back/forward navigation
    window.addEventListener('popstate', () => {
        const pageId = window.location.hash.slice(1) || 'introduction';
        loadPage(pageId);
    });
});
