import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import './globals.css'

export const metadata: Metadata = {
  title: 'Nereid — Evidence-First Ocean Intelligence',
  description: 'Reproducible QC-aware ARGO investigations with TEOS-10 analytics and scientific evidence.',
}

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
