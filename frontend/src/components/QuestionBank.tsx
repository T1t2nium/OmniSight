import { useState } from 'react';
import type { QuestionBankPayload, QuestionCategory, InterviewQuestion } from '../types';

interface QuestionBankProps {
  bank: QuestionBankPayload | null;
  visible: boolean;
}

/**
 * Collapsible question bank display for the Interview Agent.
 *
 * Renders AI-generated interview questions organized by category.
 * Categories are collapsible — only one expanded at a time (accordion).
 * Each question shows text, difficulty badge, and reference skill tag.
 */
export function QuestionBank({ bank, visible }: QuestionBankProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(() => {
    // Default: expand "icebreaker"
    return new Set(['icebreaker']);
  });

  if (!visible || !bank || bank.categories.length === 0) return null;

  const toggleCategory = (type: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  const difficultyClass = (d: string): string => {
    switch (d) {
      case 'easy': return 'question-bank__difficulty--easy';
      case 'hard': return 'question-bank__difficulty--hard';
      default: return 'question-bank__difficulty--medium';
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
    <div className="question-bank">
      <div className="question-bank__header">
        <span className="question-bank__title">📋 面试题库</span>
        <span className="question-bank__stats">{bank.total_questions} 题</span>
      </div>

      <div className="question-bank__body">
      {bank.categories.map((cat: QuestionCategory) => {
        const isExpanded = expandedCategories.has(cat.type);
        return (
          <div key={cat.type} className="question-bank__category">
            <button
              className="question-bank__category-header"
              onClick={() => toggleCategory(cat.type)}
              aria-expanded={isExpanded}
            >
              <span className="question-bank__category-label">
                {cat.icon} {cat.name}
                <span className="question-bank__category-count">({cat.questions.length})</span>
              </span>
              <span className={`question-bank__chevron ${isExpanded ? 'question-bank__chevron--open' : ''}`}>
                ▼
              </span>
            </button>

            {isExpanded && (
              <div className="question-bank__questions">
                {cat.questions.map((q: InterviewQuestion) => (
                  <div key={q.id} className="question-bank__question-card">
                    <div className="question-bank__question-text">{q.text}</div>
                    <div className="question-bank__question-meta">
                      <span className={`question-bank__difficulty ${difficultyClass(q.difficulty)}`}>
                        {difficultyLabel(q.difficulty)}
                      </span>
                      {q.reference && (
                        <span className="question-bank__reference">{q.reference}</span>
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
    </div>
  );
}
