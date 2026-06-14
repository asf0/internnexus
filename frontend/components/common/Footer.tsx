'use client';

import { useState } from 'react';
import { Github, Linkedin, Mail } from 'lucide-react';
import { AboutModal, PrivacyModal, TermsModal } from '@/components/modals';
import { Button } from '@/components/ui';

export default function Footer() {
  const currentYear = new Date().getFullYear();
  const [aboutOpen, setAboutOpen] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const [termsOpen, setTermsOpen] = useState(false);

  const socialLinks = [
    {
      name: 'GitHub',
      href: 'https://github.com/asf0',
      icon: Github,
    },
    {
      name: 'LinkedIn',
      href: 'https://linkedin.com/in/ataidesantos',
      icon: Linkedin,
    },
    {
      name: 'Contact',
      href: 'mailto:your.email@example.com',
      icon: Mail,
    },
  ];

  const footerLinks = [
    { name: 'About', action: () => setAboutOpen(true) },
    { name: 'Privacy', action: () => setPrivacyOpen(true) },
    { name: 'Terms', action: () => setTermsOpen(true) },
  ];

  return (
    <footer className="dark:text-md-on-surface bg-transparent text-slate-900 dark:bg-transparent">
      <div className="mx-auto w-full max-w-(--breakpoint-2xl) px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
          {/* Logo/Brand */}
          <div className="flex items-center gap-2">
            <span className="dark:text-md-on-surface text-xl font-bold text-slate-900">
              InternNexus
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
            {footerLinks.map((link) => (
              <Button key={link.name} variant="ghost" size="sm" onClick={link.action}>
                {link.name}
              </Button>
            ))}
          </nav>

          {/* Social Links */}
          <div className="flex items-center gap-4">
            {socialLinks.map((social) => (
              <a
                key={social.name}
                href={social.href}
                target="_blank"
                rel="noopener noreferrer"
                className="dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high dark:hover:text-md-on-surface flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-600 transition-all hover:bg-slate-200 hover:text-slate-900"
                aria-label={social.name}
              >
                <social.icon className="h-5 w-5" />
              </a>
            ))}
          </div>
        </div>

        {/* Bottom bar */}
        <div className="dark:border-md-outline-variant mt-8 flex flex-col items-center justify-between gap-4 border-t border-slate-200 pt-8 md:flex-row">
          <p className="dark:text-md-on-surface-variant text-sm text-slate-500">
            © {currentYear} InternNexus. Built with ❤️ by asf0.
          </p>
          <p className="dark:text-md-on-surface-variant text-xs text-slate-400">
            Smart Job Matching Platform
          </p>
        </div>
      </div>

      {/* Modals */}
      <AboutModal isOpen={aboutOpen} onClose={() => setAboutOpen(false)} />
      <PrivacyModal isOpen={privacyOpen} onClose={() => setPrivacyOpen(false)} />
      <TermsModal isOpen={termsOpen} onClose={() => setTermsOpen(false)} />
    </footer>
  );
}
