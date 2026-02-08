'use client';

import { Proposal, Agent } from '../shared/types';
import styles from './Stage4.module.css';

interface ProposalComparisonProps {
  requirement: string;
  originalCost: number;
  originalRisk: string;
  proposal: Proposal;
  onContinue: () => void;
}

export function ProposalComparison({
  requirement,
  originalCost,
  originalRisk,
  proposal,
  onContinue,
}: ProposalComparisonProps) {
  const savings = originalCost - proposal.totalCost;
  const savingsPercent = Math.round((savings / originalCost) * 100);

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>协商方案</h2>

      <div className={styles.comparisonGrid}>
        {/* Original Requirement */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <span className={styles.cardLabel}>原始需求</span>
          </div>
          <div className={styles.cardContent}>
            <p className={styles.requirementText}>{requirement}</p>

            <div className={styles.metricList}>
              <div className={styles.metric}>
                <span className={styles.metricLabel}>预期投入</span>
                <span className={styles.metricValue}>
                  {formatCurrency(originalCost)}
                </span>
              </div>
              <div className={styles.metric}>
                <span className={styles.metricLabel}>风险评估</span>
                <span className={`${styles.metricValue} ${styles.riskHigh}`}>
                  {originalRisk}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Arrow */}
        <div className={styles.arrow}>
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </div>

        {/* Proposed Solution */}
        <div className={`${styles.card} ${styles.cardProposal}`}>
          <div className={styles.cardHeader}>
            <span className={styles.cardLabel}>协商后方案</span>
            <span className={styles.savingsBadge}>
              节省 {savingsPercent}%
            </span>
          </div>
          <div className={styles.cardContent}>
            <div className={styles.stepList}>
              {proposal.steps.map((step, index) => (
                <div key={step.id} className={styles.stepItem}>
                  <div className={styles.stepNumber}>{index + 1}</div>
                  <div className={styles.stepContent}>
                    <div className={styles.stepHeader}>
                      <span className={styles.stepAgent}>{step.agentName}</span>
                      {step.price && (
                        <span className={styles.stepPrice}>
                          {formatCurrency(step.price)}
                        </span>
                      )}
                    </div>
                    <p className={styles.stepDesc}>{step.description}</p>
                    {step.duration && (
                      <span className={styles.stepDuration}>
                        {step.duration}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Cost Comparison */}
      <div className={styles.costComparison}>
        <div className={styles.costItem}>
          <span className={styles.costLabel}>原始成本</span>
          <span className={styles.costOriginal}>
            {formatCurrency(originalCost)}
          </span>
        </div>
        <div className={styles.costArrow}>
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </div>
        <div className={styles.costItem}>
          <span className={styles.costLabel}>新方案成本</span>
          <span className={styles.costNew}>
            {formatCurrency(proposal.totalCost)}
          </span>
        </div>
        <div className={styles.costSavings}>
          <span className={styles.savingsLabel}>节省</span>
          <span className={styles.savingsValue}>
            {formatCurrency(savings)}
          </span>
        </div>
      </div>

      {/* Participants */}
      <div className={styles.participants}>
        <h3 className={styles.participantsTitle}>参与方案的 Agent</h3>
        <div className={styles.participantList}>
          {proposal.participants.map((agent) => (
            <div key={agent.id} className={styles.participant}>
              <div className={styles.participantAvatar}>
                {agent.avatar ? (
                  <img src={agent.avatar} alt={agent.name} />
                ) : (
                  <span>{agent.name.charAt(0)}</span>
                )}
              </div>
              <div className={styles.participantInfo}>
                <span className={styles.participantName}>{agent.name}</span>
                <span className={styles.participantRole}>{agent.role}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Continue Button */}
      <div className={styles.actions}>
        <button className={styles.continueButton} onClick={onContinue}>
          查看完整汇总
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </button>
      </div>
    </div>
  );
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}
