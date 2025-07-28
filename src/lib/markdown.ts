export const formatMarkdownToPlainText = (markdown: string): string => {
  // Remove horizontal rules
  let plainText = markdown.replace(/---/g, '');

  // Remove images
  plainText = plainText.replace(/!\[.*?\]\(.*?\)/g, '');

  // Remove links but keep the text
  plainText = plainText.replace(/\[(.*?)\]\(.*?\)/g, '$1');

  // Remove blockquotes
  plainText = plainText.replace(/^> (.*$)/gm, '$1');

  // Remove code blocks
  plainText = plainText.replace(/```[\s\S]*?```/g, '');

  // Remove inline code
  plainText = plainText.replace(/`([^`]+)`/g, '$1');

  // Handle headings
  plainText = plainText.replace(/^#+\s+(.*$)/gm, '$1');

  // Handle lists
  plainText = plainText.replace(/^\s*[-*+]\s+(.*$)/gm, '$1');
  plainText = plainText.replace(/^\s*\d+\.\s+(.*$)/gm, '$1');

  // Remove bold and italics
  plainText = plainText.replace(/(\*\*|__)(.*?)\1/g, '$2');
  plainText = plainText.replace(/(\*|_)(.*?)\1/g, '$2');

  // Remove extra newlines
  plainText = plainText.replace(/\n{2,}/g, '\n');

  return plainText.trim();
};
