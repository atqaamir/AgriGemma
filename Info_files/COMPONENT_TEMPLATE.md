# Standardized Header and Navigation Components

This document provides the standardized header and navigation bar components for use across all pages in the Climate Adaptation Planner project.

## Tailwind Configuration

Add this to every new page's `<head>` section (in a `<script id="tailwind-config">` tag):

```javascript
tailwind.config = {
  darkMode: "class",
  theme: {
    extend: {
      "colors": {
        "surface": "#fcf9f0",
        "secondary-fixed": "#d5e9c1",
        "on-error-container": "#93000a",
        "inverse-primary": "#bbccaa",
        "on-tertiary-fixed": "#1e1c12",
        "tertiary-fixed-dim": "#ccc6b6",
        "surface-container-high": "#ebe8df",
        "primary": "#47573b",
        "on-secondary-fixed-variant": "#3b4b2e",
        "secondary-fixed-dim": "#bacda7",
        "surface-dim": "#dddad1",
        "surface-variant": "#e5e2da",
        "on-secondary-fixed": "#111f07",
        "surface-container-highest": "#e5e2da",
        "on-tertiary-container": "#f1ebda",
        "on-secondary-container": "#586a4a",
        "inverse-on-surface": "#f4f1e8",
        "on-primary": "#ffffff",
        "on-primary-fixed": "#121f09",
        "on-primary-container": "#dff1cd",
        "secondary-container": "#d5e9c1",
        "background": "#fcf9f0",
        "on-surface": "#1c1c17",
        "outline": "#75786f",
        "error": "#ba1a1a",
        "on-error": "#ffffff",
        "primary-container": "#5f6f52",
        "tertiary-container": "#6e6a5d",
        "surface-container-low": "#f7f3ea",
        "tertiary": "#555246",
        "on-surface-variant": "#444840",
        "error-container": "#ffdad6",
        "on-tertiary-fixed-variant": "#4a473b",
        "primary-fixed": "#d6e8c5",
        "primary-fixed-dim": "#bbccaa",
        "on-primary-fixed-variant": "#3c4b31",
        "tertiary-fixed": "#e8e2d2",
        "inverse-surface": "#31312b",
        "surface-bright": "#fcf9f0",
        "surface-container-lowest": "#ffffff",
        "secondary": "#536344",
        "surface-container": "#f1eee5",
        "on-secondary": "#ffffff",
        "on-tertiary": "#ffffff",
        "surface-tint": "#536347",
        "outline-variant": "#c5c8bd",
        "on-background": "#1c1c17"
      },
      "borderRadius": {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "1.5rem",
        "full": "9999px"
      },
      "fontFamily": {
        "headline": ["Manrope"],
        "body": ["Work Sans"],
        "label": ["Work Sans"]
      }
    },
  },
}
```

## Theme Initialization Script

Add this to the `<head>` section before any other scripts:

```html
<script>
  // Initialize theme immediately to avoid flickering
  (function() {
    const theme = localStorage.getItem('theme') || 'light';
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    }
  })();
</script>
```

## Standard Header Component

```html
<!-- TopAppBar Section -->
<header class="bg-[#fcf9f0] dark:bg-[#1c1c17] flex justify-between items-center w-full px-6 py-4 sticky top-0 z-50">
  <div class="flex items-center gap-3">
    <span class="material-symbols-outlined text-[#47573b] dark:text-[#d5e9c1]" style="font-size: 28px;">agriculture</span>
    <h1 class="text-2xl font-semibold text-[#47573b] dark:text-[#d5e9c1] font-['Manrope'] tracking-tight">Climate Adaptation Planner</h1>
  </div>
  <div class="flex gap-4">
    <button class="hover:bg-[#f1eee5] dark:hover:bg-[#2a2a24] transition-colors p-2 rounded-full active:scale-95 duration-150" onclick="toggleTheme()" id="themeToggle">
      <span class="material-symbols-outlined text-[#47573b] dark:text-[#d5e9c1]">brightness_4</span>
    </button>
    <button class="hover:bg-[#f1eee5] dark:hover:bg-[#2a2a24] transition-colors p-2 rounded-full active:scale-95 duration-150" onclick="showNotifications()">
      <span class="material-symbols-outlined text-[#47573b] dark:text-[#d5e9c1]">notifications</span>
    </button>
    <button class="hover:bg-[#f1eee5] dark:hover:bg-[#2a2a24] transition-colors p-2 rounded-full active:scale-95 duration-150" onclick="openSearch()">
      <span class="material-symbols-outlined text-[#47573b] dark:text-[#d5e9c1]">search</span>
    </button>
  </div>
</header>
```

## Standard Navigation Bar Component

**Note:** The active nav item should match the current page.

```html
<!-- BottomNavBar Section -->
<nav class="fixed bottom-0 left-0 w-full z-50 bg-[#fcf9f0]/80 dark:bg-stone-950/80 backdrop-blur-md rounded-t-[24px] shadow-[0_-8px_24px_rgba(28,28,23,0.06)] flex justify-around items-center px-4 pb-6 pt-3">
  <!-- Dashboard (inactive by default) -->
  <a class="flex flex-col items-center justify-center text-stone-500 dark:text-stone-400 px-3 py-1.5 transition-transform hover:scale-105 duration-150" href="/dashboard">
    <span class="material-symbols-outlined" data-icon="dashboard">dashboard</span>
    <span class="font-['Work_Sans'] text-[11px] font-medium tracking-wide">Dashboard</span>
  </a>

  <!-- Fields (active on fields.html) -->
  <a class="flex flex-col items-center justify-center bg-secondary-fixed dark:bg-primary-container text-on-background dark:text-surface-bright rounded-2xl px-3 py-1.5 transition-transform hover:scale-105 duration-150" href="/myfields">
    <span class="material-symbols-outlined" data-icon="landscape" style="font-variation-settings: 'FILL' 1;">landscape</span>
    <span class="font-['Work_Sans'] text-[11px] font-medium tracking-wide">Fields</span>
  </a>

  <!-- Crops (active on crops.html) -->
  <a class="flex flex-col items-center justify-center bg-secondary-fixed dark:bg-primary-container text-on-background dark:text-surface-bright rounded-2xl px-3 py-1.5 transition-transform hover:scale-105 duration-150" href="/mycrops">
    <span class="material-symbols-outlined" data-icon="eco" style="font-variation-settings: 'FILL' 1;">eco</span>
    <span class="font-['Work_Sans'] text-[11px] font-medium tracking-wide">Crops</span>
  </a>

  <!-- Tasks (inactive by default) -->
  <a class="flex flex-col items-center justify-center text-stone-500 dark:text-stone-400 px-3 py-1.5 transition-transform hover:scale-105 duration-150" href="/mytasks">
    <span class="material-symbols-outlined" data-icon="assignment_turned_in">assignment_turned_in</span>
    <span class="font-['Work_Sans'] text-[11px] font-medium tracking-wide">Tasks</span>
  </a>

  <!-- Planner (inactive by default) -->
  <a class="flex flex-col items-center justify-center text-stone-500 dark:text-stone-400 px-3 py-1.5 transition-transform hover:scale-105 duration-150" href="/myplanner">
    <span class="material-symbols-outlined" data-icon="calendar_today">calendar_today</span>
    <span class="font-['Work_Sans'] text-[11px] font-medium tracking-wide">Planner</span>
  </a>

  <!-- Chat (inactive by default) -->
  <a class="flex flex-col items-center justify-center text-stone-500 dark:text-stone-400 px-3 py-1.5 transition-transform hover:scale-105 duration-150" href="#">
    <span class="material-symbols-outlined" data-icon="chat">chat</span>
    <span class="font-['Work_Sans'] text-[11px] font-medium tracking-wide">Chat</span>
  </a>
</nav>
```

## Theme Toggle Functions

Add these JavaScript functions to your page:

```javascript
function initTheme() {
  const savedTheme = localStorage.getItem('theme') || 'light';
  if (savedTheme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

function toggleTheme() {
  const html = document.documentElement;
  if (html.classList.contains('dark')) {
    html.classList.remove('dark');
    localStorage.setItem('theme', 'light');
  } else {
    html.classList.add('dark');
    localStorage.setItem('theme', 'dark');
  }
}

// Initialize theme on page load
initTheme();
```

## CSS Requirements

Every page must link to the base CSS file for semantic utilities:
- Link `fields.css` or `crops.css` (which imports `base.css`)

The base.css provides:
- **CSS Variables** for light mode (default) and dark mode
- **Semantic Utility Classes** like `.bg-secondary-fixed`, `.text-on-background`, etc.
- **Color Theme Overrides** that automatically apply when `.dark` class is on html element

## Navigation Bar Details

### Color Scheme by Theme:
- **Light Mode (Default):**
  - Background: #fcf9f0 (light cream)
  - Active tab: #d5e9c1 (light green) background
  - Text: #47573b (dark green)
  
- **Dark Mode:**
  - Background: stone-950 (very dark)
  - Active tab: #47573b (green) background
  - Text: #fcf9f0 (light cream)

### How to Mark a Tab Active:
Replace the inactive `<a>` tag with the active version:
```html
<!-- Inactive -->
<a class="flex flex-col items-center justify-center text-stone-500 dark:text-stone-400 px-3 py-1.5 ...">

<!-- Active (add these classes: bg-secondary-fixed dark:bg-primary-container text-on-background dark:text-surface-bright rounded-2xl) -->
<a class="flex flex-col items-center justify-center bg-secondary-fixed dark:bg-primary-container text-on-background dark:text-surface-bright rounded-2xl px-3 py-1.5 ...">
```

## Best Practices

1. Always include the theme initialization script in `<head>` before other scripts
2. Always include the Tailwind config to ensure consistent styling
3. Always link the CSS file (fields.css or crops.css) which imports base.css
4. Use semantic utility classes from base.css instead of hardcoded hex values
5. Use the `.dark` class for dark mode (controlled by JavaScript)
6. Test theme toggle on each new page before deployment
