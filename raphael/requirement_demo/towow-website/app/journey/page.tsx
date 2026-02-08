'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { getJourneyData } from '../../lib/journey-data';
import styles from './journey.module.css';

export default function JourneyPage() {
  const t = useTranslations('Journey');
  const locale = useLocale();
  const { stats, transformations, phases, sessions } = getJourneyData(locale);

  const [expandedPhases, setExpandedPhases] = useState<Set<number>>(new Set());
  const [expandedCompacts, setExpandedCompacts] = useState<Set<number>>(new Set());

  const togglePhase = useCallback((num: number) => {
    setExpandedPhases((prev) => {
      const next = new Set(prev);
      if (next.has(num)) next.delete(num);
      else next.add(num);
      return next;
    });
  }, []);

  const toggleCompact = useCallback((num: number) => {
    setExpandedCompacts((prev) => {
      const next = new Set(prev);
      if (next.has(num)) next.delete(num);
      else next.add(num);
      return next;
    });
  }, []);

  // Cmd+E to expand/collapse all compacts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'e' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setExpandedCompacts((prev) => {
          const allNums = sessions.flatMap((s) => s.compacts.map((c) => c.num));
          if (prev.size === allNums.length) return new Set();
          return new Set(allNums);
        });
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [sessions]);

  return (
    <div className={styles.page}>
      {/* Layer 0: Title + Stats */}
      <header className={styles.header}>
        <h1 className={styles.title}>{t('title')}</h1>
        <p className={styles.subtitle}>{t('subtitle')}</p>
      </header>

      <div className={styles.statsBar}>
        {stats.map((s) => (
          <div key={s.label} className={styles.statCard}>
            <div className={styles.statNum}>{s.num}</div>
            <div className={styles.statLabel}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Layer 1: Three Transformations */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          <span className={styles.dot} style={{ background: '#C47030' }} />
          {t('threeTransformations')}
        </h2>
        <div className={styles.transformGrid}>
          {transformations.map((tr) => (
            <div key={tr.label} className={styles.transformCard}>
              <div className={styles.transformTime}>{tr.time}</div>
              <h3 className={styles.transformLabel}>{tr.label}</h3>
              <p className={styles.transformOneLiner}>{tr.oneLiner}</p>
              <p className={styles.transformMeaning}>
                <span className={styles.fieldLabel}>{t('meaning')}</span>
                {tr.meaning}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Phase Flow */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          <span className={styles.dot} style={{ background: '#F9A87C' }} />
          {t('devPhases')}
        </h2>
        <div className={styles.flow}>
          {phases.map((p, i) => (
            <span key={p.num}>
              <span
                className={styles.flowNode}
                style={{
                  background:
                    i < 2
                      ? 'rgba(139,106,144,0.12)'
                      : i < 4
                        ? 'rgba(196,112,48,0.1)'
                        : 'rgba(90,138,100,0.1)',
                  color: i < 2 ? '#8B6A90' : i < 4 ? '#C47030' : '#5A8A64',
                }}
              >
                {p.name}
              </span>
              {i < phases.length - 1 && (
                <span className={styles.flowArrow}>&#8594;</span>
              )}
            </span>
          ))}
        </div>
      </section>

      {/* Layer 2: Phases */}
      <section className={styles.section}>
        <div className={styles.phaseGrid}>
          {phases.map((p) => {
            const isOpen = expandedPhases.has(p.num);
            return (
              <div
                key={p.num}
                className={`${styles.phaseCard} ${p.num === 7 ? styles.phaseCardFull : ''}`}
                onClick={() => togglePhase(p.num)}
              >
                <div className={styles.phaseTop}>
                  <span className={styles.phaseNum}>{t('phase', { num: p.num })}</span>
                  <span className={styles.phaseDates}>{p.dates}</span>
                </div>
                <h3 className={styles.phaseName}>{p.name}</h3>
                <p className={styles.phaseNarrative}>{p.narrative}</p>
                <div className={styles.phaseTags}>
                  {p.tags.map((tag) => (
                    <span
                      key={tag.label}
                      className={`${styles.tag} ${styles[`tag${tag.color.charAt(0).toUpperCase() + tag.color.slice(1)}`]}`}
                    >
                      {tag.label}
                    </span>
                  ))}
                </div>
                <div className={styles.phaseStats}>{p.stats}</div>

                {isOpen && (
                  <div className={styles.phaseDetail}>
                    {p.decisions.length > 0 && (
                      <div className={styles.detailBlock}>
                        <span className={styles.fieldLabel}>{t('keyDecisions')}</span>
                        <ul className={styles.detailList}>
                          {p.decisions.map((d, i) => (
                            <li key={i}>{d}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {p.corrections.length > 0 && (
                      <div className={styles.detailBlock}>
                        <span className={styles.fieldLabel}>{t('userCorrections')}</span>
                        <ul className={styles.detailList}>
                          {p.corrections.map((c, i) => (
                            <li key={i}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {p.surprise && (
                      <div className={styles.detailBlock}>
                        <span className={styles.fieldLabel}>{t('surprises')}</span>
                        <p className={styles.detailText}>{p.surprise}</p>
                      </div>
                    )}
                    {p.quote && (
                      <blockquote className={styles.quoteBox}>
                        <p>&ldquo;{p.quote}&rdquo;</p>
                        {p.quoteAuthor && (
                          <cite>-- {p.quoteAuthor}</cite>
                        )}
                      </blockquote>
                    )}
                  </div>
                )}

                <div className={styles.expandHint}>
                  {isOpen ? t('collapse') : t('expand')}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Layer 3: Compact List */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          <span className={styles.dot} style={{ background: '#5A8A64' }} />
          {t('compactTimeline', { count: 41 })}
        </h2>
        <p className={styles.sectionSubtitle}>
          {t('compactSubtitle')}
          <span className={styles.shortcutHint}>{t('shortcutHint')}</span>
        </p>

        {sessions.map((session) => (
          <div key={session.label} className={styles.sessionGroup}>
            <div
              className={styles.sessionLabel}
              style={{ color: session.color }}
            >
              {session.label} / {session.dateRange}
            </div>
            <div className={styles.compactList}>
              {session.compacts.map((c) => {
                const isOpen = expandedCompacts.has(c.num);
                return (
                  <div
                    key={c.num}
                    className={`${styles.compactItem} ${isOpen ? styles.compactOpen : ''}`}
                    onClick={() => toggleCompact(c.num)}
                  >
                    <div
                      className={styles.compactNum}
                      style={{ color: session.color }}
                    >
                      {c.num}
                    </div>
                    <div className={styles.compactContent}>
                      <div className={styles.compactTitle}>{c.title}</div>
                      <div className={styles.compactMeta}>{c.date}</div>
                      {isOpen && (
                        <div className={styles.compactDetail}>{c.detail}</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </section>

      {/* Layer 4: Links */}
      <section className={styles.footer}>
        <h2 className={styles.footerTitle}>{t('sourceMaterials')}</h2>
        <p className={styles.footerText}>{t('sourceMaterialsDesc')}</p>
        <ul className={styles.linkList}>
          <li>
            <a
              href="https://github.com/NatureBlueee/Towow/blob/main/raphael/docs/work_session_summaries.md"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.footerLink}
            >
              {t('linkWorkSummaries')} &#8594;
            </a>
          </li>
          <li>
            <a
              href="https://github.com/NatureBlueee/Towow/blob/main/raphael/docs/ARCHITECTURE_DESIGN.md"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.footerLink}
            >
              {t('linkArchDesign')} &#8594;
            </a>
          </li>
          <li>
            <a
              href="https://github.com/NatureBlueee/Towow/blob/main/raphael/docs/DESIGN_LOG_001_PROJECTION_AND_SELF.md"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.footerLink}
            >
              {t('linkDesignLog001')} &#8594;
            </a>
          </li>
        </ul>
      </section>
    </div>
  );
}
