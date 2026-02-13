/**
 * Parse offer content that may be wrapped in JSON or code fences.
 *
 * Backend sometimes returns offer text in these formats:
 *   - `{ "content": "actual text..." }`
 *   - ````json\n{ "content": "actual text..." }\n````
 *   - `{ "content": "actual text...", "metadata": {...} }`
 *   - Plain text (no wrapper)
 *
 * This function extracts the inner content string and returns it
 * ready for Markdown rendering.
 */
export function parseOfferContent(raw: string | null | undefined): string {
  if (!raw) return '';

  let text = raw.trim();

  // Strip code fence wrapper: ```json ... ``` or ``` ... ```
  const fenceMatch = text.match(/^```(?:json)?\s*\n?([\s\S]*?)\n?\s*```$/);
  if (fenceMatch) {
    text = fenceMatch[1].trim();
  }

  // Try to parse as JSON and extract "content" field
  if (text.startsWith('{')) {
    try {
      const parsed = JSON.parse(text);
      if (typeof parsed === 'object' && parsed !== null && typeof parsed.content === 'string') {
        return parsed.content;
      }
    } catch {
      // Not valid JSON — fall through to return as-is
    }
  }

  return text;
}
