import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Nerdy Ad Engine", description: "Autonomous Ad Copy Generation System" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en"><body>
      <nav style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: '0 2rem', height: '56px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 100 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          <span className="mono" style={{ color: 'var(--accent)', fontWeight: 700, fontSize: '0.9rem', letterSpacing: '0.05em' }}>NERDY // AD ENGINE</span>
          <div style={{ display: 'flex', gap: '1.5rem' }}>
            {[{ href: '/', label: 'Dashboard' }, { href: '/campaigns', label: 'Campaigns' }, { href: '/survey', label: 'Survey' }, { href: '/insights', label: 'Insights' }].map(({ href, label }) => (
              <a key={href} href={href} style={{ color: 'var(--muted)', textDecoration: 'none', fontSize: '0.875rem', fontWeight: 500 }}>{label}</a>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><div className="live-dot" /><span className="mono" style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>LIVE</span></div>
      </nav>
      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>{children}</main>
    </body></html>
  );
}
