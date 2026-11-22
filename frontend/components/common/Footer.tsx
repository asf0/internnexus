'use client';

import { useState } from 'react';
import Link from 'next/link';
import { MessageCircle } from 'lucide-react';
import { AboutModal, PrivacyModal, TermsModal } from '@/components/modals';
import { Button } from '@/components/ui';
import { GitHubBrandIcon, LinkedInBrandIcon } from './BrandIcons';

export default function Footer() {
  const currentYear = new Date().getFullYear();
  const [aboutOpen, setAboutOpen] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const [termsOpen, setTermsOpen] = useState(false);

  const socialLinks = [
    {
      name: 'GitHub',
      href: 'https://github.com/asf0',
      icon: GitHubBrandIcon,
    },
    {
      name: 'LinkedIn',
      href: 'https://linkedin.com/in/ataidesantos',
      icon: LinkedInBrandIcon,
    },
    {
      name: 'Support',
      href: 'https://github.com/asf0/internnexus/issues',
      icon: MessageCircle,
    },
  ];

  const footerLinks = [
    { name: 'Companies', href: '/companies', action: null },
    { name: 'Categories', href: '/categories', action: null },
    { name: 'About', href: '/about', action: () => setAboutOpen(true) },
    { name: 'Privacy', href: '/privacy', action: () => setPrivacyOpen(true) },
    { name: 'Terms', href: '/terms', action: () => setTermsOpen(true) },
  ];

  return (
    <footer className="text-foreground bg-transparent">
      <div className="mx-auto w-full max-w-(--breakpoint-2xl) px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
          {/* Logo/Brand */}
          <div className="flex items-center gap-2">
            <span className="text-foreground text-xl font-bold">InternNexus</span>
          </div>

          {/* Navigation Links */}
          <nav className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
            {footerLinks.map((link) =>
              link.action ? (
                <Button key={link.name} variant="ghost" size="sm" asChild>
                  <Link
                    href={link.href}
                    onClick={(event) => {
                      event.preventDefault();
                      link.action();
                    }}
                  >
                    {link.name}
                  </Link>
                </Button>
              ) : (
                <Button key={link.name} variant="ghost" size="sm" asChild>
                  <Link href={link.href}>{link.name}</Link>
                </Button>
              )
            )}
          </nav>

          {/* Social Links */}
          <div className="flex items-center gap-4">
            {socialLinks.map((social) => (
              <a
                key={social.name}
                href={social.href}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-surface-subtle text-foreground-secondary hover:bg-surface-raised hover:text-foreground focus-visible:ring-focus-ring flex h-10 w-10 items-center justify-center rounded-full transition-colors focus-visible:ring-2 focus-visible:outline-none"
                aria-label={social.name}
              >
                <social.icon className="h-5 w-5" />
              </a>
            ))}
          </div>
        </div>

        {/* Bottom bar */}
        <div className="border-border mt-8 flex flex-col items-center justify-between gap-4 border-t pt-8 md:flex-row">
          <p className="text-foreground-muted text-sm">
            © {currentYear} InternNexus. Built and maintained by asf0.
          </p>
          <p className="text-foreground-muted text-xs">Job discovery and matching</p>
        </div>
      </div>

      {/* Modals */}
      <AboutModal isOpen={aboutOpen} onClose={() => setAboutOpen(false)} />
      <PrivacyModal isOpen={privacyOpen} onClose={() => setPrivacyOpen(false)} />
      <TermsModal isOpen={termsOpen} onClose={() => setTermsOpen(false)} />
    </footer>
  );
}
