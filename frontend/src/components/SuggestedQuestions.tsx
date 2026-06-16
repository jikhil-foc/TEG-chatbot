interface SuggestedQuestionsProps {
  questions: string[];
  disabled?: boolean;
  onSelect: (question: string) => void;
}

export function SuggestedQuestions({
  questions,
  disabled = false,
  onSelect,
}: SuggestedQuestionsProps) {
  if (questions.length === 0) {
    return null;
  }

  return (
    <div className="teg-suggestions" aria-label="Suggested follow-up questions">
      <p className="teg-suggestions__label">Related questions</p>
      <div className="teg-suggestions__list" role="group">
        {questions.map((question) => (
          <button
            key={question}
            type="button"
            className="teg-suggestions__chip"
            disabled={disabled}
            onClick={() => onSelect(question)}
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
