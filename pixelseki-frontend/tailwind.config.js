/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        game: {
          dark: '#0a0e1a',      // Deep night sky base
          panel: '#111827',     // Card/panel background
          border: '#1e293b',    // Subtle borders
          accent: '#22d3ee',    // Cyan moonlight glow
          success: '#10b981',   // Emerald status
          sakura: '#f0abfc',    // Cherry blossom pink
          sunset: '#c084fc',    // Warm purple accent
          gold: '#fbbf24',      // Lantern / coin gold
        },
        // Light mode overrides
        day: {
          bg: '#1a0a2e',        // Deep purple night base for light-mode bg
          panel: '#2d1b4e',     // Warm purple panel
          border: '#4c1d95',    // Purple border
          accent: '#e879f9',    // Pink/magenta accent
          text: '#fdf4ff',      // Light text on purple
        }
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glow-accent': '0 0 15px rgba(34, 211, 238, 0.25)',
        'glow-accent-strong': '0 0 25px rgba(34, 211, 238, 0.5)',
        'glow-sakura': '0 0 15px rgba(240, 171, 252, 0.3)',
        'glow-sakura-strong': '0 0 25px rgba(240, 171, 252, 0.5)',
        'glow-success': '0 0 15px rgba(16, 185, 129, 0.25)',
      }
    },
  },
  plugins: [],
}
