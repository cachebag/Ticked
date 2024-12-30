const docs = {
    sections: [
        {
            title: 'Getting Started',
            items: [
                { id: 'introduction', title: 'Introduction', content: `
# Introduction

Welcome to our documentation! This guide will help you get started with our platform.

## Overview

Our platform provides a simple and intuitive way to manage your documentation.

### Key Features

- **Markdown Support**: Write your documentation in Markdown
- **Dark Mode**: Toggle between light and dark themes
- **Mobile Responsive**: Works great on all devices
- **Fast**: No build step required
                `},
                { id: 'quick-start', title: 'Quick Start', content: `
# Quick Start Guide

Get up and running in minutes!

\`\`\`javascript
// Example code
const docs = new Docs({
    container: '#app',
    theme: 'light'
});
\`\`\`
                `}
            ]
        },
        {
            title: 'Core Concepts',
            items: [
                { id: 'basics', title: 'Basic Concepts', content: `# Basic Concepts...` },
                { id: 'advanced', title: 'Advanced Usage', content: `# Advanced Usage...` }
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
function loadPage(pageId) {
    const page = docs.sections
        .flatMap(section => section.items)
        .find(item => item.id === pageId);
    
    if (page) {
        document.getElementById('doc-content').innerHTML = marked(page.content);
        document.getElementById('breadcrumb').textContent = page.title;
        updateUrl(pageId);
        highlightCode();
    } else {
        document.getElementById('doc-content').innerHTML = marked('# Page Not Found');
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
