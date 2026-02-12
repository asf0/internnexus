"use client";

import { useState } from "react";
import { Github, Linkedin, Mail } from "lucide-react";
import AboutModal from "./AboutModal";
import PrivacyModal from "./PrivacyModal";
import TermsModal from "./TermsModal";
import { Button } from "./ui";

export default function Footer() {
  const currentYear = new Date().getFullYear();
  const [aboutOpen, setAboutOpen] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const [termsOpen, setTermsOpen] = useState(false);

  const socialLinks = [
    {
      name: "GitHub",
      href: "https://github.com/asf0",
      icon: Github,
    },
    {
      name: "LinkedIn",
      href: "https://linkedin.com/in/ataidesantos",
      icon: Linkedin,
    },
    {
      name: "Contact",
      href: "mailto:your.email@example.com",
      icon: Mail,
    },
  ];

  const footerLinks = [
    { name: "About", action: () => setAboutOpen(true) },
    { name: "Privacy", action: () => setPrivacyOpen(true) },
    { name: "Terms", action: () => setTermsOpen(true) },
  ];

  return (
    <footer className="bg-transparent text-slate-900 dark:bg-transparent dark:text-md-on-surface">
      <div className="mx-auto w-full max-w-(--breakpoint-2xl) px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
          {/* Logo/Brand */}
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-slate-900 dark:text-md-on-surface">
              InternNexus
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
            {footerLinks.map((link) => (
              <Button
                key={link.name}
                variant="ghost"
                size="sm"
                onClick={link.action}
              >
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
                className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-600 transition-all hover:bg-slate-200 hover:text-slate-900 dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high dark:hover:text-md-on-surface"
                aria-label={social.name}
              >
                <social.icon className="h-5 w-5" />
              </a>
            ))}
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-8 flex flex-col items-center justify-between gap-4 border-t border-slate-200 pt-8 dark:border-md-outline-variant md:flex-row">
          <p className="text-sm text-slate-500 dark:text-md-on-surface-variant">
            © {currentYear} InternNexus. Built with ❤️ by asf0.
          </p>
          <p className="text-xs text-slate-400 dark:text-md-on-surface-variant">
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
