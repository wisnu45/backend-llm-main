import React from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';
import { useTypingAnimation } from './useTypingAnimation';

interface TypingEffectProps {
  text: string;
  typingSpeed?: number;
  onComplete?: () => void;
}

export const TypingEffect = ({
  text,
  typingSpeed = 25,
  onComplete
}: TypingEffectProps) => {
  const { displayText, isComplete } = useTypingAnimation(text, typingSpeed);

  // Call onComplete callback when typing is finished
  React.useEffect(() => {
    if (isComplete && onComplete) {
      onComplete();
    }
    if (isComplete) {
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    }
  }, [isComplete, onComplete]);

  return (
    <div className="text-base">
      <MarkdownRenderer content={displayText} />
    </div>
  );
};
