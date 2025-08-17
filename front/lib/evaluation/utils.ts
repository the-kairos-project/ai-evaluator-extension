/**
 * Ensure text fits within Airtable's character limits
 *
 * @param text Text to potentially truncate
 * @param maxLength Maximum allowed length (default: 95000)
 * @returns Truncated text with notice if needed
 */
export const truncateForAirtable = (text: string, maxLength = 95000): string => {
  if (text.length <= maxLength) return text;

  const truncationNote = "\n\n[CONTENT TRUNCATED: This text was too long for Airtable's limits]";
  return text.substring(0, maxLength - truncationNote.length) + truncationNote;
};

export default {};


