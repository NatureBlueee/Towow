import styles from './NoiseTexture.module.css';

interface NoiseTextureProps {
  opacity?: number;
}

export function NoiseTexture({ opacity = 0.05 }: NoiseTextureProps) {
  return (
    <div
      className={styles.noiseTexture}
      style={{ opacity }}
    />
  );
}
