const PLACEHOLDER = 'https://placehold.co/150?text=No+Image';

export function getProxiedImageUrl(pictureUrl) {
  if (!pictureUrl || typeof pictureUrl !== 'string') return PLACEHOLDER;
  return `https://wsrv.nl/?url=${encodeURIComponent(pictureUrl.split('?')[0])}&output=webp&default=${PLACEHOLDER}`;
}

export function getProxiedImageSrcset(pictureUrl) {
  if (!pictureUrl || typeof pictureUrl !== 'string') return '';
  const encodedUrl = encodeURIComponent(pictureUrl.split('?')[0]);
  return [
    `https://wsrv.nl/?url=${encodedUrl}&output=webp&w=150&default=${PLACEHOLDER} 150w`,
    `https://wsrv.nl/?url=${encodedUrl}&output=webp&w=300&default=${PLACEHOLDER} 300w`,
    `https://wsrv.nl/?url=${encodedUrl}&output=webp&w=600&default=${PLACEHOLDER} 600w`,
  ].join(', ');
}

export function getLocalImageUrl(cardId) {
  return `${process.env.PUBLIC_URL}/images/cards/${cardId}`;
}
