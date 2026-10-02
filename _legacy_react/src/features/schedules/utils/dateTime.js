const MONTHS_ID = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'Mei',
  'Jun',
  'Jul',
  'Agu',
  'Sep',
  'Okt',
  'Nov',
  'Des',
];

function pad(value) {
  return String(value).padStart(2, '0');
}

function parseParts(value) {
  const match = String(value || '').match(
    /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?/
  );
  if (!match) return null;
  const [, year, month, day, hour, minute, second] = match;
  return {
    year: Number(year),
    month: Number(month),
    day: Number(day),
    hour: Number(hour),
    minute: Number(minute),
    second: Number(second || '0'),
  };
}

export function formatWIB(value) {
  if (!value) return '-';

  const parts = String(value).split(/[- :T]/);
  const [year, month, day, hour, minute] = parts;

  if (!year || !month || !day || !hour || !minute) {
    return '-';
  }

  const monthName = MONTHS_ID[Number(month) - 1];
  if (!monthName) return '-';

  return `${day} ${monthName} ${year}, ${hour}:${minute}`;
}

export function toSQLDateTime(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate()
  )} ${pad(date.getHours())}:${pad(date.getMinutes())}:00`;
}

export function parseLocalDateTime(value) {
  const parts = parseParts(value);
  if (!parts) return null;
  return new Date(
    parts.year,
    parts.month - 1,
    parts.day,
    parts.hour,
    parts.minute,
    parts.second
  );
}

export function normalizeLocalDateTime(value) {
  const parsed = parseLocalDateTime(value);
  if (!parsed) return null;
  return toSQLDateTime(parsed);
}

export function addMinutesToLocalDateTime(value, minutes) {
  const parsed = parseLocalDateTime(value);
  if (!parsed) return null;
  parsed.setMinutes(parsed.getMinutes() + Number(minutes));
  return toSQLDateTime(parsed);
}

export function toLocalDateKey(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate()
  )}`;
}

export function isWithinLocalRange({ now, startTime, endTime, durationMinutes }) {
  const start = parseLocalDateTime(startTime);
  if (!start) return false;
  const end = endTime
    ? parseLocalDateTime(endTime)
    : durationMinutes
      ? new Date(start.getTime() + Number(durationMinutes) * 60000)
      : null;
  if (!end) return false;

  return now >= start && now <= end;
}
