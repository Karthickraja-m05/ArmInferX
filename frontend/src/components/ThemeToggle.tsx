import React from 'react';
import { useTheme } from './ThemeProvider';
import { Sun, Moon } from 'lucide-react';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme, isDark } = useTheme();

  return (
    <button
      className="theme-toggle-btn"
      onClick={toggleTheme}
      title={`Switch to ${isDark ? 'Light' : 'Dark'} Mode`}
      aria-label={`Switch to ${isDark ? 'Light' : 'Dark'} Mode`}
    >
      <span className="toggle-track">
        <span className={`toggle-thumb ${theme}`}>
          <span className="toggle-icon-wrap">
            {isDark ? (
              <Moon size={14} className="toggle-icon moon-icon" />
            ) : (
              <Sun size={14} className="toggle-icon sun-icon" />
            )}
          </span>
        </span>

        {/* Ambient glow orbs */}
        <span className="toggle-glow" />
      </span>
    </button>
  );
};
