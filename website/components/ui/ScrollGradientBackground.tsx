// components/ui/ScrollGradientBackground.tsx
'use client';

import { useEffect, useState } from 'react';
import styles from './ScrollGradientBackground.module.css';

// 渐变色停靠点 - 和现有配色协调的暖色系
const gradientStops = [
  { position: 0, colors: ['#F8F6F3', '#FFF9F5', '#F8F6F3'] },      // 米白
  { position: 0.15, colors: ['#FFF5EE', '#FFE8D6', '#FFF0E6'] },   // 暖桃
  { position: 0.3, colors: ['#F5E6F0', '#EED6E8', '#F8EBF4'] },    // 淡玫瑰紫
  { position: 0.45, colors: ['#E8F4EC', '#D4F4DD', '#E0F0E4'] },   // 薄荷绿
  { position: 0.6, colors: ['#FFF8E8', '#FFE4B5', '#FFF0D4'] },    // 蜜桃橙
  { position: 0.75, colors: ['#EDE8F5', '#D4B8D9', '#E8E0F0'] },   // 暖紫
  { position: 0.9, colors: ['#F0F8F4', '#D4F4DD', '#E8F4EC'] },    // 回到薄荷
  { position: 1, colors: ['#F8F6F3', '#FFF9F5', '#F8F6F3'] },      // 回到米白
];

function interpolateColor(color1: string, color2: string, factor: number): string {
  const hex = (c: string) => parseInt(c, 16);
  const r1 = hex(color1.slice(1, 3));
  const g1 = hex(color1.slice(3, 5));
  const b1 = hex(color1.slice(5, 7));
  const r2 = hex(color2.slice(1, 3));
  const g2 = hex(color2.slice(3, 5));
  const b2 = hex(color2.slice(5, 7));

  const r = Math.round(r1 + (r2 - r1) * factor);
  const g = Math.round(g1 + (g2 - g1) * factor);
  const b = Math.round(b1 + (b2 - b1) * factor);

  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

function getGradientAtPosition(scrollProgress: number): string {
  // 找到当前位置在哪两个停靠点之间
  let startStop = gradientStops[0];
  let endStop = gradientStops[1];

  for (let i = 0; i < gradientStops.length - 1; i++) {
    if (scrollProgress >= gradientStops[i].position &&
        scrollProgress <= gradientStops[i + 1].position) {
      startStop = gradientStops[i];
      endStop = gradientStops[i + 1];
      break;
    }
  }

  // 计算在两个停靠点之间的进度
  const range = endStop.position - startStop.position;
  const localProgress = range > 0
    ? (scrollProgress - startStop.position) / range
    : 0;

  // 插值计算当前颜色
  const colors = startStop.colors.map((startColor, i) =>
    interpolateColor(startColor, endStop.colors[i], localProgress)
  );

  return `linear-gradient(180deg, ${colors[0]} 0%, ${colors[1]} 50%, ${colors[2]} 100%)`;
}

export function ScrollGradientBackground() {
  const [gradient, setGradient] = useState(getGradientAtPosition(0));

  useEffect(() => {
    let ticking = false;

    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
          const scrollProgress = scrollHeight > 0
            ? window.scrollY / scrollHeight
            : 0;
          setGradient(getGradientAtPosition(scrollProgress));
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // 初始化

    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div
      className={styles.gradientBg}
      style={{ background: gradient }}
    />
  );
}
