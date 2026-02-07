import { NoiseTexture } from '@/components/layout/NoiseTexture';
import { GridLines } from '@/components/layout/GridLines';
import styles from './layout.module.css';

export default function ExperienceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className={styles.experienceLayout}>
      <NoiseTexture />
      <GridLines />
      <main className={styles.main}>{children}</main>
    </div>
  );
}
