import { useState } from 'react';
import { RadarChart } from './RadarChart';
import type { RadarScore } from './RadarChart';
import type { InterviewReportPayload } from '../types';

interface ReportViewerProps {
  report: InterviewReportPayload | null;
  visible: boolean;
  loading?: boolean;
}

/** Color map for recommendation levels. */
const RECOMMENDATION_STYLE: Record<string, { bg: string; text: string }> = {
  '强烈推荐': { bg: 'rgba(16,185,129,0.15)', text: '#10b981' },
  '推荐': { bg: 'rgba(16,185,129,0.12)', text: '#34d399' },
  '保留意见': { bg: 'rgba(251,191,36,0.12)', text: '#fbbf24' },
  '不推荐': { bg: 'rgba(239,68,68,0.12)', text: '#ef4444' },
};

/** Dimension label translations. */
const SCORE_LABELS: Record<string, string> = {
  technical: '技术能力',
  experience: '项目经验',
  communication: '沟通表达',
  role_fit: '岗位匹配',
  stress: '抗压应变',
};

export function ReportViewer({ report, visible, loading = false }: ReportViewerProps) {
  const [expanded, setExpanded] = useState(false);

  if (!visible) return null;

  // Show loading skeleton while AI is scoring
  if (loading && !report) {
    return (
      <div className="report-viewer report-viewer--loading">
        <div className="report-viewer__header">
          <span className="report-viewer__title">📊 AI 正在生成评估报告...</span>
          <span className="report-viewer__spinner" />
        </div>
        <div className="report-viewer__skeleton">
          <div className="report-viewer__skel-bar" />
          <div className="report-viewer__skel-bar" />
          <div className="report-viewer__skel-bar report-viewer__skel-bar--short" />
        </div>
      </div>
    );
  }

  if (!report) return null;

  const scores = report.scores;
  const radarScores: RadarScore[] = Object.entries(scores).map(([key, val]) => ({
    label: SCORE_LABELS[key] || key,
    value: val as number,
  }));

  const recStyle = RECOMMENDATION_STYLE[report.recommendation] || RECOMMENDATION_STYLE['保留意见'];

  const scoreBars = Object.entries(scores).map(([key, val]) => ({
    key,
    label: SCORE_LABELS[key] || key,
    value: val as number,
  }));

  return (
    <div className={`report-viewer${expanded ? ' report-viewer--expanded' : ''}`}>
      {/* Always-visible compact header */}
      <button
        className="report-viewer__header"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <span className="report-viewer__title">
          📊 面试评估报告 · {report.overall_score.toFixed(0)} 分
        </span>
        <span className="report-viewer__header-right">
          <span
            className="report-viewer__badge"
            style={{ background: recStyle.bg, color: recStyle.text }}
          >
            {report.recommendation}
          </span>
          <span className={`report-viewer__chevron${expanded ? ' report-viewer__chevron--open' : ''}`}>
            ▼
          </span>
        </span>
      </button>

      {/* Collapsible detail section */}
      {expanded && (
        <div className="report-viewer__body">
          <div className="report-viewer__radar">
            <RadarChart scores={radarScores} size={200} color="#10b981" />
          </div>

          <div className="report-viewer__details">
            {scoreBars.map((bar) => (
              <div key={bar.key} className="report-viewer__score-item">
                <span className="report-viewer__score-label">{bar.label}</span>
                <div className="report-viewer__score-bar-track">
                  <div
                    className="report-viewer__score-bar-fill"
                    style={{ width: `${Math.min(bar.value, 100)}%` }}
                  />
                </div>
                <span className="report-viewer__score-value">{bar.value.toFixed(0)}</span>
              </div>
            ))}
            <p className="report-viewer__summary">{report.summary}</p>

            <div className="report-viewer__lists">
              <div className="report-viewer__list report-viewer__list--strength">
                <h4 className="report-viewer__list-title">✅ 优势</h4>
                <ul>
                  {report.strengths.map((s, i) => (
                    <li key={`s-${i}`}>{s}</li>
                  ))}
                </ul>
              </div>
              <div className="report-viewer__list report-viewer__list--weakness">
                <h4 className="report-viewer__list-title">⚠️ 待改进</h4>
                <ul>
                  {report.weaknesses.map((w, i) => (
                    <li key={`w-${i}`}>{w}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
