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
                    title: 'Setup', 
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
                    id: 'nest', 
                    title: 'NEST+',
                    type: 'markdown',
                    path: 'nest.md'
                },
                { 
                    id: 'canvas', 
                    title: 'Canvas LMS',
                    type: 'markdown',
                    path: 'canvas.md'
                },
                { 
                    id: 'spotify', 
                    title: 'Spotify',
                    type: 'markdown',
                    path: 'spotify.md'
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

marked.setOptions({
    highlight: function(code, lang) {
        return hljs.highlightAuto(code).value;
    },
    breaks: true
});

const themeManager = {
    init() {
        const themeButton = document.getElementById('theme-switch');
        if (!themeButton) {
            console.error('Theme button not found');
            return;
        }

        const savedTheme = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
        const defaultTheme = savedTheme || (prefersDark.matches ? 'dark' : 'light');
        
        this.setTheme(defaultTheme);

        prefersDark.addEventListener('change', (e) => {
            if (!localStorage.getItem('theme')) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });

        themeButton.addEventListener('click', () => {
            const currentTheme = document.body.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            this.setTheme(newTheme);
        });
    },

    setTheme(theme) {
        document.body.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        const button = document.getElementById('theme-switch');
        if (button) {
            button.textContent = theme === 'dark' ? '☀️' : '🌙';
            button.setAttribute('aria-label', theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
        }
    }
};

function buildNavigation() {
    const nav = document.getElementById('sidebar-nav');
    nav.innerHTML = '';
    
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
                navigateToPage(item.id);
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

function updateActiveLink(clickedLink) {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    clickedLink.classList.add('active');
}

function saveCurrentPage(pageId) {
    localStorage.setItem('currentPage', pageId);
}

async function loadPage(pageId, shouldScroll = true) {
    const page = docs.sections
        .flatMap(section => section.items)
        .find(item => item.id === pageId);
    
    if (!page) {
        if (pageId !== 'introduction') {
            navigateToPage('introduction');
        }
        return;
    }
    
    saveCurrentPage(pageId);
    
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

        marked.setOptions({
            breaks: true,
            headerIds: true,
            gfm: true
        });

        const docContent = document.getElementById('doc-content');
        docContent.innerHTML = marked.parse(content);
        docContent.classList.add('doc-content');
        
        document.querySelectorAll('.doc-content h1, .doc-content h2, .doc-content h3, .doc-content h4')
            .forEach(header => {
                header.style.display = 'inline-block';
                header.style.width = '100%';
                header.style.scrollMarginTop = '100px';
            });

        highlightCode();
        updateSectionNav();
        
        if (shouldScroll) {
            window.scrollTo({
                top: 0,
                behavior: 'auto'
            });
        }

        // Only scroll to hash element after ensuring page is at top first
        const hash = window.location.hash.slice(1);
        if (hash && hash !== pageId) {
            setTimeout(() => {
                const element = document.getElementById(hash);
                if (element) {
                    element.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            }, 100);
        }

        // Update the active link in the sidebar
        const sidebarLink = document.querySelector(`.nav-link[href="#${pageId}"]`);
        if (sidebarLink) {
            updateActiveLink(sidebarLink);
        }
    } catch (error) {
        console.error('Error loading page:', error);
        if (pageId !== 'introduction') {
            navigateToPage('introduction');
        } else {
            document.getElementById('doc-content').innerHTML = `
                <h1>Error Loading Page</h1>
                <p>Failed to load the documentation. Please try refreshing the page.</p>
            `;
        }
    }
}

function navigateToPage(pageId) {
    const newUrl = `#${pageId}`;
    history.pushState({ pageId }, '', newUrl);
    loadPage(pageId, true);
}

function highlightCode() {
    document.querySelectorAll('pre code').forEach(block => {
        hljs.highlightBlock(block);
    });
}

function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('active');
}

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
            history.pushState(null, null, `#${id}`);
        };
        
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

document.addEventListener('DOMContentLoaded', () => {
    themeManager.init();
    buildNavigation();
    
    const pageId = window.location.hash.slice(1);
    
    if (!pageId) {
        // Always navigate to introduction when no hash is present
        navigateToPage('introduction');
    } else {
        loadPage(pageId);
    }
    
    const menuToggle = document.getElementById('menu-toggle');
    if (menuToggle) {
        menuToggle.addEventListener('click', toggleSidebar);
    }
    
    window.addEventListener('popstate', (event) => {
        if (event.state && event.state.pageId) {
            loadPage(event.state.pageId);
        } else {
            const pageId = window.location.hash.slice(1) || 'introduction';
            loadPage(pageId);
        }
    });

    window.addEventListener('load', initScrollSpy);
});