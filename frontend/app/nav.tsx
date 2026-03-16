'use client';
import { useTheme } from './theme-provider';

export function Nav() {
  const { theme, toggle } = useTheme();
  return (
    <nav style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: '0 2rem', height: '64px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 100, boxShadow: 'var(--nav-shadow)', transition: 'background 0.3s, border-color 0.3s, box-shadow 0.3s' }}>
      <a href="/" style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}>
        <img className="nav-logo" src="/nerdy_x_varsitytutors_logo.png" alt="Nerdy x Varsity Tutors" />
      </a>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {[{ href: '/', label: 'Dashboard' }, { href: '/campaigns', label: 'Campaigns' }, { href: '/create', label: 'Create' }, { href: '/survey', label: 'Survey' }, { href: '/insights', label: 'Insights' }].map(({ href, label }) => (
          <a key={href} href={href} className="nav-btn">{label}</a>
        ))}
        <div style={{ width: '1px', height: '24px', background: 'var(--border)', margin: '0 4px' }} />
        <button className="theme-toggle" onClick={toggle} title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}>
          {theme === 'light' ? '\u{1F319}' : '\u{2600}\u{FE0F}'}
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '2px' }}><div className="live-dot" /><span className="mono" style={{ fontSize: '0.65rem', color: 'var(--muted)' }}>LIVE</span></div>
      </div>
    </nav>
  );
}
