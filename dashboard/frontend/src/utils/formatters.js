export const formatPrice = (value, currency = 'MDL') => {
  if (!value && value !== 0) return '-';
  
  const symbols = {
    MDL: 'MDL',
    EUR: '€',
    USD: '$',
  };
  
  const symbol = symbols[currency] || currency;
  return `${Math.round(value).toLocaleString()} ${symbol}`;
};

export const formatNumber = (value) => {
  if (!value && value !== 0) return '-';
  return value.toLocaleString();
};

export const formatDate = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleDateString('ro-RO', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export const getScoreColor = (score) => {
  if (score >= 80) return 'text-success';
  if (score >= 60) return 'text-warning';
  return 'text-danger';
};

export const getScoreBg = (score) => {
  if (score >= 80) return 'bg-success/20';
  if (score >= 60) return 'bg-warning/20';
  return 'bg-danger/20';
};
