const LIST_MARKER = /^\s*(?:[-•*]\s*|\d+[.)]\s+)/;
const TRAILING_SEPARATOR = /[,;]+\s*$/;
const SENTENCE_START = /([\p{L}\d]*)([.!?]\s+)(\p{Ll})/gu;
const MIN_SENTENCE_END_WORD = 4;

function capitalize(text) {
  return text
    .replace(SENTENCE_START, (match, word, end, letter) =>
      word.length >= MIN_SENTENCE_END_WORD
        ? `${word}${end}${letter.toUpperCase()}`
        : match,
    )
    .replace(/^\p{Ll}/u, (letter) => letter.toUpperCase());
}

function cleanItem(item) {
  return item.replace(LIST_MARKER, '').replace(TRAILING_SEPARATOR, '').trim();
}

function splitLines(text) {
  return text.split('\n').map(cleanItem).filter(Boolean);
}

function splitByTopLevelSeparators(text) {
  const items = [];
  let current = '';
  let depth = 0;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];

    if (char === '(') depth += 1;
    if (char === ')') depth = Math.max(0, depth - 1);

    const isSeparator = char === ';' || char === ',';
    const isDecimalComma =
      char === ',' &&
      /\d/.test(text[index - 1] ?? '') &&
      /\d/.test(text[index + 1] ?? '');

    if (isSeparator && depth === 0 && !isDecimalComma) {
      items.push(current);
      current = '';
    } else {
      current += char;
    }
  }

  items.push(current);
  return items.map(cleanItem).filter(Boolean);
}

function splitByStepNumbers(text) {
  const start = text.match(/^\s*1[.)]\s*/);
  if (!start) return [text.trim()];

  const steps = [];
  let rest = text.slice(start[0].length);
  let next = 2;

  while (true) {
    const marker = rest.match(new RegExp(`\\s${next}[.)]\\s`));

    if (!marker) {
      steps.push(rest.trim());
      return steps;
    }

    steps.push(rest.slice(0, marker.index).trim());
    rest = rest.slice(marker.index + marker[0].length);
    next += 1;
  }
}

export function splitIngredients(text) {
  const lines = splitLines(text);
  const items = lines.length > 1 ? lines : splitByTopLevelSeparators(text);
  return items.map(capitalize);
}

export function splitSteps(text) {
  const lines = splitLines(text);
  const steps =
    lines.length > 1 ? lines : splitByStepNumbers(text).filter(Boolean);
  return steps.map(capitalize);
}
