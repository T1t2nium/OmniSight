import { useState, useRef, useEffect } from 'react';
import type { QuestionBankPayload, QuestionCategory, InterviewQuestion } from '../types';

interface QuestionBankProps {
  bank: QuestionBankPayload | null;
  visible: boolean;
}

/**
 * Dropdown-styled question bank for the Interview Agent.
 *
 * Shows a compact trigger button with question count. Click to open a
 * dropdown menu with collapsible categories. Click outside to close.
 * Uses absolute positioning so the layout is not pushed around.
 */
export function QuestionBank({ bank, visible }: QuestionBankProps) {
  const [open, setOpen] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(() => {
    return new Set(['icebreaker']);
  });
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  if (!visible || !bank || bank.categories.length === 0) return null;

  const toggleCategory = (type: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const difficultyClass = (d: string): string => {
    switch (d) {
      case 'easy': return 'qbank-diff--easy';
      case 'hard': return 'qbank-diff--hard';
      default: return 'qbank-diff--medium';
    }
  };

  const difficultyLabel = (d: string): string => {
    switch (d) {
      case 'easy': return '简单';
      case 'hard': return '困难';
      default: return '中等';
    }
  };

  return (
    <div className="qbank" ref={ref}>
      <button
        className="qbank__trigger"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="qbank__trigger-label">📋 面试题库</span>
        <span className="qbank__trigger-stats">{bank.total_questions} 题</span>
        <span className={`qbank__arrow${open ? ' qbank__arrow--open' : ''}`}>▾</span>
      </button>

      {open && (
        <div className="qbank__menu">
          {bank.categories.map((cat: QuestionCategory) => {
            const isExpanded = expandedCategories.has(cat.type);
            return (
              <div key={cat.type} className="qbank__cat">
                <button
                  className="qbank__cat-header"
                  onClick={() => toggleCategory(cat.type)}
                  aria-expanded={isExpanded}
                >
                  <span className="qbank__cat-label">
                    {cat.icon} {cat.name}
                    <span className="qbank__cat-count">({cat.questions.length})</span>
                  </span>
                  <span className={`qbank__chevron${isExpanded ? ' qbank__chevron--open' : ''}`}>▼</span>
                </button>

                {isExpanded && (
                  <div className="qbank__questions">
                    {cat.questions.map((q: InterviewQuestion) => (
                      <div key={q.id} className="qbank__card">
                        <div className="qbank__text">{q.text}</div>
                        <div className="qbank__meta">
                          <span className={`qbank__diff ${difficultyClass(q.difficulty)}`}>
                            {difficultyLabel(q.difficulty)}
                          </span>
                          {q.reference && (
                            <span className="qbank__ref">{q.reference}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
