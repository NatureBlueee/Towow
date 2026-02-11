// components/ui/Button.tsx
import Link from 'next/link';
import styles from './Button.module.css';

interface ButtonProps {
  variant: 'primary' | 'outline' | 'secondary';
  children: React.ReactNode;
  href?: string;
  onClick?: () => void;
  className?: string;
  type?: 'button' | 'submit' | 'reset';
  disabled?: boolean;
}

export function Button({ variant, children, href, onClick, className, type = 'button', disabled = false }: ButtonProps) {
  const buttonClass = `${styles.btn} ${styles[variant]} ${disabled ? styles.disabled : ''} ${className || ''}`.trim();

  if (href) {
    // External/API URLs use <a> to avoid Next.js RSC prefetch;
    // internal routes use <Link> for client-side navigation.
    const isExternal = href.startsWith('/api/') || href.startsWith('http');
    if (isExternal) {
      return (
        <a href={href} className={buttonClass}>
          {children}
        </a>
      );
    }
    return (
      <Link href={href} className={buttonClass}>
        {children}
      </Link>
    );
  }

  return (
    <button type={type} className={buttonClass} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}
