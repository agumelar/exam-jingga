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
