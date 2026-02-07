// app/contribute/layout.tsx
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import styles from './contribute.module.css';

export default function ContributeLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className={styles.layoutBg}>
      <Header />
      <main>{children}</main>
      <Footer />
    </div>
  );
}
