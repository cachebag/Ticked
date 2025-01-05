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
                    title: 'Setup and Spotify Access', 
                    type: 'markdown',
                    path: 'quick-start.md'
                }
            ]
        },
        {
            title: 'Core Features',
            items: [
                { 
                    id: 'basics', 
                    title: 'Calendar and Task Management',
                    type: 'markdown',
                    path: 'task.md'
                },
                { 
                    id: 'advanced', 
                    title: 'NEST+',
                    type: 'markdown',
                    path: 'nest.md'
                },
                {
                    id: 'dev',
                    title: 'Development',
                    type: 'markdown',
                    path: 'dev.md'
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

// Add this function to store current page
function saveCurrentPage(pageId) {
    localStorage.setItem('currentPage', pageId);
}

// Load page content
async function loadPage(pageId) {
    // Always scroll to top first
    window.scrollTo(0, 0);
    
    const page = docs.sections
        .flatMap(section => section.items)
        .find(item => item.id === pageId);
    
    if (!page) {
        loadPage('introduction');
        return;
    }
    
    saveCurrentPage(pageId);
    
    // Update page title
    const pageTitleElement = document.getElementById('current-page-title');
    if (pageTitleElement) {
        pageTitleElement.textContent = page.title;
    }
    
    try {
        let content;
        if (page.type === 'markdown') {
            const response = await fetch(page.path);
            if (!response.ok) {
                throw new Error(`Failed to load ${page.path}`);
            }
            content = await response.text();
        } else {
            content = page.content;
        }

        // Configure marked options
        marked.setOptions({
            breaks: true,
            headerIds: true,
            gfm: true
        });

        // Render the content
        const docContent = document.getElementById('doc-content');
        docContent.innerHTML = marked.parse(content);
        docContent.classList.add('doc-content');
        
        // Style headers
        document.querySelectorAll('.doc-content h1, .doc-content h2, .doc-content h3, .doc-content h4')
            .forEach(header => {
                header.style.display = 'inline-block';
                header.style.width = '100%';
                header.style.scrollMarginTop = '100px';
            });

        highlightCode();
        updateSectionNav();
        
        // Update URL without triggering scroll
        history.pushState(null, '', `#${pageId}`);
    } catch (error) {
        console.error('Error loading page:', error);
        if (pageId !== 'introduction') {
            loadPage('introduction');
        } else {
            document.getElementById('doc-content').innerHTML = `
                <h1>Error Loading Page</h1>
                <p>Failed to load the documentation. Please try refreshing the page.</p>
            `;
        }
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
    themeManager.init();
    buildNavigation();
    
    // Check if this is the first visit to the site
    const hasVisited = localStorage.getItem('hasVisited');
    
    if (!hasVisited) {
        // First visit - load intro and set visited flag
        localStorage.setItem('hasVisited', 'true');
        loadPage('introduction');
    } else {
        // Return visitor - load page based on hash or stored page
        const pageId = window.location.hash.slice(1) || 
                      localStorage.getItem('currentPage') || 
                      'introduction';
        loadPage(pageId);
    }
    
    // Rest of initialization code
    const menuToggle = document.getElementById('menu-toggle');
    if (menuToggle) {
        menuToggle.addEventListener('click', toggleSidebar);
    }
    
    // Always load introduction page on back/forward navigation
    window.addEventListener('popstate', () => {
        loadPage('introduction');
    });

    window.addEventListener('load', initScrollSpy);
});

// Extract and display section headings
function updateSectionNav() {
    const sectionNav = document.getElementById('section-nav');
    const headings = document.querySelectorAll('#doc-content h1, #doc-content h2');
    
    sectionNav.innerHTML = '';
    
    headings.forEach(heading => {
        const id = heading.textContent.toLowerCase().replace(/[^a-z0-9]+/g, '-');
        heading.id = id;
        
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = `#${id}`;
        a.textContent = heading.textContent;
        a.onclick = (e) => {
            e.preventDefault();
            heading.scrollIntoView({ 
                behavior: 'smooth',
                block: 'start'
            });
            updateActiveSectionLink(a);
            // Update URL hash without triggering scroll
            history.pushState(null, null, `#${id}`);
        };
        
        // Add indent for h2
        if (heading.tagName === 'H2') {
            a.style.paddingLeft = '1rem';
        }
        
        li.appendChild(a);
        sectionNav.appendChild(li);
    });
}

function updateActiveSectionLink(clickedLink) {
    document.querySelectorAll('.section-nav a').forEach(link => {
        link.classList.remove('active');
    });
    if (clickedLink) clickedLink.classList.add('active');
}

// Add scroll spy functionality
function initScrollSpy() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.id;
                const link = document.querySelector(`.section-nav a[href="#${id}"]`);
                if (link) updateActiveSectionLink(link);
            }
        });
    }, { threshold: 0.5 });

    document.querySelectorAll('#doc-content h1, #doc-content h2').forEach(heading => {
        observer.observe(heading);
    });
}
