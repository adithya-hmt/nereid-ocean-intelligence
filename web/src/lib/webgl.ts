export function hasWebGLSupport(documentRef: Document = document): boolean {
  const canvas = documentRef.createElement('canvas')
  return Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'))
}
