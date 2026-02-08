'use client';

import '@/styles/team-matcher.css';
import { TeamBackground } from '@/components/team-matcher/TeamBackground';
import { TeamNav } from '@/components/team-matcher/TeamNav';
import { TeamRequestForm } from '@/components/team-matcher/TeamRequestForm';
import styles from './TeamRequestPage.module.css';

export function TeamRequestPageClient() {
  return (
    <div className="team-matcher-root">
      <TeamBackground />
      <TeamNav currentStep="request" />
      <main className={styles.main}>
        <TeamRequestForm />
      </main>
    </div>
  );
}
