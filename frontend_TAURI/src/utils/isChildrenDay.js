export const isChildrenDay = (date = new Date()) => {
  const dateParts = new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: '2-digit',
    timeZone: 'Asia/Kolkata',
  }).formatToParts(date);

  const day = dateParts.find((part) => part.type === 'day')?.value;
  const month = dateParts.find((part) => part.type === 'month')?.value;
  return month === '11' && day === '14';
};
