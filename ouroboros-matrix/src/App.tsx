import { startTransition, useDeferredValue, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Download,
  MoonStar,
  RefreshCcw,
  ShieldCheck,
  SunMedium,
} from 'lucide-react';
import './App.css';
import { AuditTimeline } from './components/AuditTimeline';
import { DecisionDetailCard } from './components/DecisionDetailCard';
import { DecisionTable } from './components/DecisionTable';
import { KpiStrip } from './components/KpiStrip';
import { ProofPackageCard } from './components/ProofPackageCard';
import { SidebarNav } from './components/SidebarNav';
import { TopbarActions } from './components/TopbarActions';
import { TrustFlowRail } from './components/TrustFlowRail';
import { VerificationTrendChart } from './components/VerificationTrendChart';
import {
  buildFlowSteps,
  buildProofPackage,
  buildTimeline,
  type KpiMetric,
  useDashboardData,
} from './data/dashboard';
import { decisionHref, proofHref, replaceHash, useHashRoute } from './hooks/useHashRoute';

type ThemeMode = 'dark' | 'light';

function getInitialTheme(): ThemeMode {
  if (typeof window === 'undefined') {
    return 'dark';
  }

  return window.localStorage.getItem('ouroboros-matrix-theme') === 'light' ? 'light' : 'dark';
}

function formatGeneratedAt(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(parsed);
}

function getRouteCopy(routeName: ReturnType<typeof useHashRoute>['name']) {
  if (routeName === 'decisions') {
    return {
      tag: 'Decisions route',
      title: 'High-signal decisions mapped to ledger evidence.',
      body:
        'Operators can filter by agent, inspect decision lineage, and see the audit timeline without reconstructing state from logs.',
    };
  }

  if (routeName === 'proof') {
    return {
      tag: 'Proof export route',
      title: 'A handoff package instead of audit archaeology.',
      body:
        'Proof exports bundle the decision payload, taint metadata, hash continuity, and timeline evidence into one package ready for review.',
    };
  }

  return {
    tag: 'Canonical dashboard',
    title: 'Operational trust visible at a glance.',
    body:
      'A product surface for teams who need to store decisions, verify ledger continuity, flag tamper events, audit the custody chain, and export proof on demand.',
  };
}

function downloadProofPackage(
  decision: Parameters<typeof buildProofPackage>[0],
  simulatedTamper: boolean,
) {
  const content = JSON.stringify(buildProofPackage(decision, simulatedTamper), null, 2);
  const blob = new Blob([content], { type: 'application/json' });
  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = `${decision.id}-proof-package.json`;
  anchor.click();
  window.URL.revokeObjectURL(objectUrl);
}

function App() {
  const route = useHashRoute();
  const { data, errorMessage, isLoading, sourceLabel } = useDashboardData();
  const [theme, setTheme] = useState<ThemeMode>(getInitialTheme);
  const [activeAgent, setActiveAgent] = useState('All agents');
  const [simulatedTamper, setSimulatedTamper] = useState(false);
  const effectiveActiveAgent = data.decisionRecords.some((record) => record.agent === activeAgent)
    ? activeAgent
    : 'All agents';
  const deferredAgent = useDeferredValue(effectiveActiveAgent);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem('ouroboros-matrix-theme', theme);
  }, [theme]);

  const agentOptions = ['All agents', ...new Set(data.decisionRecords.map((record) => record.agent))];

  const filteredDecisions =
    deferredAgent === 'All agents'
      ? data.decisionRecords
      : data.decisionRecords.filter((record) => record.agent === deferredAgent);

  const routeDecisionId = route.name === 'overview' ? undefined : route.decisionId;
  const selectedDecision =
    filteredDecisions.find((record) => record.id === routeDecisionId) ||
    data.decisionRecords.find((record) => record.id === routeDecisionId) ||
    filteredDecisions[0] ||
    data.decisionRecords[0];

  useEffect(() => {
    if (!selectedDecision || route.name === 'overview') {
      return;
    }

    const firstVisibleDecision = filteredDecisions[0];
    if (!firstVisibleDecision) {
      replaceHash('#/');
      return;
    }

    const selectedDecisionVisible = filteredDecisions.some(
      (record) => record.id === selectedDecision.id,
    );

    if (selectedDecisionVisible) {
      return;
    }

    replaceHash(
      route.name === 'proof'
        ? proofHref(firstVisibleDecision.id)
        : decisionHref(firstVisibleDecision.id),
    );
  }, [filteredDecisions, route.name, selectedDecision]);

  if (!selectedDecision) {
    return null;
  }

  const routeCopy = getRouteCopy(route.name);
  const flowSteps = buildFlowSteps(simulatedTamper);
  const timeline = buildTimeline(selectedDecision, simulatedTamper);
  const proofPackage = buildProofPackage(selectedDecision, simulatedTamper);
  const displayedMetrics: KpiMetric[] = data.kpiMetrics.map((metric) =>
    metric.id === 'tamper-alerts' && simulatedTamper
      ? {
          ...metric,
          value: '2',
          change: 'Incident drill running',
          tone: 'alert' as const,
        }
      : metric,
  );

  const sourceStatus = errorMessage
    ? `Failed to load ${sourceLabel}. Falling back to embedded demo data.`
    : isLoading
      ? `Loading ${sourceLabel}...`
      : sourceLabel === 'embedded mock data'
        ? 'Using embedded demo data.'
        : `Loaded external JSON from ${sourceLabel}.`;

  return (
    <div className="dashboard-shell">
      <SidebarNav activeDecisionId={selectedDecision.id} activeRoute={route.name} />

      <main className="dashboard-main">
        <section className="panel topbar">
          <div className="topbar__copy">
            <span className="eyebrow">{routeCopy.tag}</span>
            <h1>{routeCopy.title}</h1>
            <p>{routeCopy.body}</p>
          </div>

          <TopbarActions
            actions={[
              {
                label: simulatedTamper ? 'Stop tamper drill' : 'Simulate tamper',
                icon: AlertTriangle,
                onClick: () => setSimulatedTamper((value) => !value),
                tone: simulatedTamper ? 'alert' : 'ghost',
              },
              {
                label: 'Reset state',
                icon: RefreshCcw,
                onClick: () => {
                  setSimulatedTamper(false);
                  setActiveAgent('All agents');
                  replaceHash('#/');
                },
                tone: 'ghost',
              },
              {
                label: 'Download proof package',
                icon: Download,
                onClick: () => downloadProofPackage(selectedDecision, simulatedTamper),
                tone: 'accent',
              },
              {
                label: theme === 'dark' ? 'Light theme' : 'Dark theme',
                icon: theme === 'dark' ? SunMedium : MoonStar,
                onClick: () => setTheme((value) => (value === 'dark' ? 'light' : 'dark')),
                tone: 'ghost',
              },
            ]}
          />
        </section>

        {route.name === 'overview' ? (
          <>
            <section className="panel panel--metrics">
              <div className="section-head">
                <div>
                  <span className="eyebrow">KPI strip</span>
                  <h2>Trust posture</h2>
                </div>
                <span className="section-meta">{formatGeneratedAt(data.generatedAt)}</span>
              </div>

              <KpiStrip metrics={displayedMetrics} />
            </section>

            <div className="overview-grid">
              <section className="panel">
                <VerificationTrendChart points={data.trendSeries} />
              </section>

              <section className="panel">
                <TrustFlowRail steps={flowSteps} />
              </section>

              <DecisionDetailCard
                decision={selectedDecision}
                onOpenDecision={() => replaceHash(decisionHref(selectedDecision.id))}
                proofPackage={proofPackage}
              />
            </div>

            <section className="panel">
              <DecisionTable
                activeAgent={effectiveActiveAgent}
                agentOptions={agentOptions}
                decisions={filteredDecisions}
                onAgentChange={(agent) => {
                  startTransition(() => setActiveAgent(agent));
                }}
                onDecisionSelect={(decisionId) => replaceHash(decisionHref(decisionId))}
                selectedDecisionId={selectedDecision.id}
              />
            </section>

            <section className="panel">
              <AuditTimeline
                decision={selectedDecision}
                events={timeline}
                proofHref={proofHref(selectedDecision.id)}
              />
            </section>
          </>
        ) : null}

        {route.name === 'decisions' ? (
          <div className="focus-grid">
            <section className="panel panel--table">
              <DecisionTable
                activeAgent={effectiveActiveAgent}
                agentOptions={agentOptions}
                decisions={filteredDecisions}
                onAgentChange={(agent) => {
                  startTransition(() => setActiveAgent(agent));
                }}
                onDecisionSelect={(decisionId) => replaceHash(decisionHref(decisionId))}
                selectedDecisionId={selectedDecision.id}
              />
            </section>

            <div className="side-stack">
              <DecisionDetailCard
                decision={selectedDecision}
                onOpenDecision={() => replaceHash(proofHref(selectedDecision.id))}
                proofPackage={proofPackage}
              />

              <section className="panel">
                <AuditTimeline
                  decision={selectedDecision}
                  events={timeline}
                  proofHref={proofHref(selectedDecision.id)}
                />
              </section>
            </div>
          </div>
        ) : null}

        {route.name === 'proof' ? (
          <div className="focus-grid focus-grid--proof">
            <section className="panel">
              <ProofPackageCard
                decision={selectedDecision}
                onDownload={() => downloadProofPackage(selectedDecision, simulatedTamper)}
                onOpenDecision={() => replaceHash(decisionHref(selectedDecision.id))}
                proofPackage={proofPackage}
              />
            </section>

            <div className="side-stack">
              <DecisionDetailCard
                decision={selectedDecision}
                onOpenDecision={() => replaceHash(decisionHref(selectedDecision.id))}
                proofPackage={proofPackage}
              />

              <section className="panel">
                <AuditTimeline
                  decision={selectedDecision}
                  events={timeline}
                  proofHref={proofHref(selectedDecision.id)}
                />
              </section>
            </div>
          </div>
        ) : null}

        <footer className="dashboard-footer">
          <div className="footer-callout">
            <ShieldCheck size={18} />
            <span>{sourceStatus}</span>
          </div>
        </footer>
      </main>
    </div>
  );
}

export default App;
