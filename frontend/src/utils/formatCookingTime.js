export function formatCookingTime(totalMinutes) {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours === 0) return `${minutes} хв`;
  return minutes === 0 ? `${hours} год` : `${hours} год ${minutes} хв`;
}
