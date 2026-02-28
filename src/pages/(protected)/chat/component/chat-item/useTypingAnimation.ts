import { useState, useEffect, useCallback } from 'react';

export const useTypingAnimation = (text: string, baseTypingSpeed: number) => {
  const [displayText, setDisplayText] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  const getRandomSpeed = useCallback((baseSpeed: number) => {
    // Add some randomness to typing speed for realism (±30% variation)
    const variation = baseSpeed * 0.3;
    return baseSpeed + (Math.random() * variation * 2 - variation);
  }, []);

  useEffect(() => {
    if (!text) {
      setDisplayText('');
      setIsComplete(false);
      return;
    }

    setDisplayText('');
    setIsComplete(false);

    let currentIndex = 0;
    let timeoutId: NodeJS.Timeout;

    const typeNextCharacter = () => {
      if (currentIndex < text.length) {
        const nextChar = text[currentIndex];
        setDisplayText((prev) => prev + nextChar);
        currentIndex++;

        // Adjust speed based on character type for realism
        let speed = baseTypingSpeed;
        if (nextChar === ' ') {
          speed *= 0.5; // Spaces are typed faster
        } else if (nextChar === '\n') {
          speed *= 2; // Pause longer at line breaks
        } else if (['.', '!', '?', ',', ';', ':'].includes(nextChar)) {
          speed *= 1.5; // Pause slightly longer at punctuation
        }

        const randomSpeed = getRandomSpeed(speed);
        timeoutId = setTimeout(typeNextCharacter, randomSpeed);
      } else {
        setIsComplete(true);
      }
    };

    // Start typing after a small delay
    timeoutId = setTimeout(typeNextCharacter, 100);

    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [text, baseTypingSpeed, getRandomSpeed]);

  return { displayText, isComplete };
};
