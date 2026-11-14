const INDIA_TIME_ZONE = 'Asia/Kolkata';
const INDIA_OFFSET = '+05:30';
const HAS_TIME_ZONE = /(?:z|[+-]\d{2}:?\d{2})$/i;

export const parseIndiaDateTime = (value) => {
  if (value instanceof Date) return value.getTime();
  if (typeof value === 'number') return value;
  if (typeof value !== 'string' || !value.trim()) return Number.NaN;

  const normalized = value.trim()
    .replace(' ', 'T')
    .replace(/([+-]\d{2})(\d{2})$/, '$1:$2');
  if (HAS_TIME_ZONE.test(normalized)) return Date.parse(normalized);

  const indiaLocal = /^\d{4}-\d{2}-\d{2}$/.test(normalized)
    ? `${normalized}T00:00:00${INDIA_OFFSET}`
    : `${normalized}${INDIA_OFFSET}`;
  return Date.parse(indiaLocal);
};

export const formatIndiaDateTime = (value) => {
  const timestamp = parseIndiaDateTime(value);
  if (!Number.isFinite(timestamp)) return 'Not scheduled';

  return new Date(timestamp).toLocaleString('en-IN', {
    timeZone: INDIA_TIME_ZONE,
  });
};
