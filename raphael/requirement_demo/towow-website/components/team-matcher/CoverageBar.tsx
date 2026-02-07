'use client';

import styles from './CoverageBar.module.css';
import type { RoleCoverage } from '@/lib/team-matcher/types';

interface CoverageBarProps {
  coverage: RoleCoverage[];
  coverageScore: number;
  synergyScore: number;
}

/**
 * Visual representation of role coverage and scores.
 */
export function CoverageBar({ coverage, coverageScore, synergyScore }: CoverageBarProps) {
  return (
    <div className={styles.container}>
      {/* Scores */}
      <div className={styles.scores}>
        <div className={styles.scoreItem}>
          <span className={styles.scoreLabel}>覆盖度</span>
          <div className={styles.scoreBar}>
            <div
              className={styles.scoreFill}
              style={{
                width: `${coverageScore * 100}%`,
                background: 'linear-gradient(90deg, #6366F1, #8B5CF6)',
              }}
            />
          </div>
          <span className={styles.scoreValue}>{Math.round(coverageScore * 100)}%</span>
        </div>
        <div className={styles.scoreItem}>
          <span className={styles.scoreLabel}>协同度</span>
          <div className={styles.scoreBar}>
            <div
              className={styles.scoreFill}
              style={{
                width: `${synergyScore * 100}%`,
                background: 'linear-gradient(90deg, #F59E0B, #F97316)',
              }}
            />
          </div>
          <span className={styles.scoreValue}>{Math.round(synergyScore * 100)}%</span>
        </div>
      </div>

      {/* Role coverage chips */}
      <div className={styles.roles}>
        {coverage.map((item) => (
          <div key={item.role} className={styles.roleItem}>
            <span
              className={`${styles.roleStatus} ${
                item.status === 'covered'
                  ? styles.roleStatusCovered
                  : item.status === 'partial'
                  ? styles.roleStatusPartial
                  : styles.roleStatusMissing
              }`}
            >
              {item.status === 'covered' && <i className="ri-check-line" />}
              {item.status === 'partial' && <i className="ri-subtract-line" />}
              {item.status === 'missing' && <i className="ri-close-line" />}
            </span>
            <span className={styles.roleName}>{item.role}</span>
            {item.covered_by && (
              <span className={styles.roleCoveredBy}>{item.covered_by}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
