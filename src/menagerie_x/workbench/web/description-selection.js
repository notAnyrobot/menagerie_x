export const DESCRIPTION_FORMATS = ["mjcf", "urdf"];

export function availableDescriptionFormats(editions) {
  return DESCRIPTION_FORMATS.filter(format => editions.some(edition => Boolean(edition.formats?.[format])));
}

export function editionsForFormat(editions, format) {
  if (!format) return [];
  return editions.filter(edition => Boolean(edition.formats?.[format]));
}

export function editionForFormat(editions, format, currentEditionId = null) {
  const available = editionsForFormat(editions, format);
  return available.find(edition => edition.id === currentEditionId)
    || available.find(edition => edition.default)
    || available[0]
    || null;
}

export function initialDescriptionSelection(editions) {
  const defaultEdition = editions.find(edition => edition.default) || editions[0] || null;
  if (!defaultEdition) return { format: null, edition: null };
  const format = DESCRIPTION_FORMATS.find(candidate => defaultEdition.formats?.[candidate])
    || availableDescriptionFormats(editions)[0]
    || null;
  return { format, edition: editionForFormat(editions, format, defaultEdition.id) };
}
