import type { SVGProps } from "react";

type LogoProps = SVGProps<SVGSVGElement>;

export function GoogleLogo(props: LogoProps) {
  return <svg viewBox="0 0 48 48" role="img" aria-label="Google" {...props}>
    <path fill="#4285F4" d="M43.6 24.5c0-1.4-.1-2.8-.4-4.1H24v7.8h11a9.4 9.4 0 0 1-4.1 6.2v5.1h6.6c3.9-3.6 6.1-8.8 6.1-15Z"/>
    <path fill="#34A853" d="M24 44c5.5 0 10.1-1.8 13.5-4.8l-6.6-5.1c-1.8 1.2-4.1 2-6.9 2-5.3 0-9.8-3.6-11.4-8.4H5.8v5.3A20 20 0 0 0 24 44Z"/>
    <path fill="#FBBC05" d="M12.6 27.7a12 12 0 0 1 0-7.4V15H5.8a20 20 0 0 0 0 18Z"/>
    <path fill="#EA4335" d="M24 11.9c3 0 5.7 1 7.8 3.1l5.9-5.9C34.1 5.8 29.5 4 24 4A20 20 0 0 0 5.8 15l6.8 5.3c1.6-4.8 6.1-8.4 11.4-8.4Z"/>
  </svg>;
}

export function GitHubLogo(props: LogoProps) {
  return <svg viewBox="0 0 24 24" role="img" aria-label="GitHub" fill="currentColor" {...props}>
    <path d="M12 .8a11.2 11.2 0 0 0-3.54 21.83c.56.1.76-.24.76-.54v-2.1c-3.1.67-3.75-1.32-3.75-1.32-.5-1.28-1.25-1.62-1.25-1.62-1.02-.7.08-.68.08-.68 1.12.08 1.72 1.16 1.72 1.16 1 1.71 2.62 1.22 3.26.93.1-.72.39-1.22.71-1.5-2.48-.28-5.08-1.24-5.08-5.52 0-1.22.44-2.22 1.16-3-.12-.28-.5-1.42.1-2.96 0 0 .95-.3 3.1 1.15a10.8 10.8 0 0 1 5.64 0c2.15-1.45 3.1-1.15 3.1-1.15.61 1.54.23 2.68.12 2.96.72.78 1.15 1.78 1.15 3 0 4.29-2.6 5.24-5.1 5.52.4.34.75 1.01.75 2.04v3.09c0 .3.2.65.77.54A11.2 11.2 0 0 0 12 .8Z"/>
  </svg>;
}

export function GitLabLogo(props: LogoProps) {
  return <svg viewBox="0 0 24 24" role="img" aria-label="GitLab" {...props}>
    <path fill="#E24329" d="m12 22 4.42-13.6H7.58L12 22Z"/>
    <path fill="#FC6D26" d="m12 22-4.42-13.6H1.38L12 22Z"/>
    <path fill="#FCA326" d="M1.38 8.4.04 12.53a1.4 1.4 0 0 0 .51 1.57L12 22 1.38 8.4Z"/>
    <path fill="#E24329" d="M1.38 8.4h6.2L4.91.66c-.14-.43-.75-.43-.9 0L1.38 8.4Z"/>
    <path fill="#FC6D26" d="m12 22 4.42-13.6h6.2L12 22Z"/>
    <path fill="#FCA326" d="m22.62 8.4 1.34 4.13a1.4 1.4 0 0 1-.51 1.57L12 22 22.62 8.4Z"/>
    <path fill="#E24329" d="M22.62 8.4h-6.2l2.67-7.74c.14-.43.75-.43.9 0l2.63 7.74Z"/>
  </svg>;
}

export function SsoLogo(props: LogoProps) {
  return <svg viewBox="0 0 24 24" role="img" aria-label="Single sign-on" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <rect x="3" y="3" width="18" height="18" rx="3"/>
    <path d="M8 8h3v3H8zM13 8h3v3h-3zM8 13h3v3H8zM13 13h3v3h-3z"/>
  </svg>;
}
