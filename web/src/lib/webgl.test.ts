import { describe, expect, it } from 'vitest'

import { hasWebGLSupport } from './webgl'

describe('hasWebGLSupport', () => {
  it('rejects a canvas-capable browser when WebGL contexts are unavailable', () => {
    const documentRef = { createElement: () => ({ getContext: () => null }) } as unknown as Document
    expect(hasWebGLSupport(documentRef)).toBe(false)
  })

  it('accepts an available WebGL context', () => {
    const documentRef = { createElement: () => ({ getContext: (kind: string) => kind === 'webgl' ? {} : null }) } as unknown as Document
    expect(hasWebGLSupport(documentRef)).toBe(true)
  })
})
