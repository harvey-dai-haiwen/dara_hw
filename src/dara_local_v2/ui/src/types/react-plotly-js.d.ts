declare module 'react-plotly.js' {
  import type { ComponentType } from 'react'

  // Minimal typings to satisfy TypeScript without pulling full plotly type surface.
  type PlotProps = {
    data?: Array<Record<string, unknown>>
    layout?: Record<string, unknown>
    frames?: Array<Record<string, unknown>>
    config?: Record<string, unknown>
    style?: Record<string, unknown>
  }

  const Plot: ComponentType<PlotProps>
  export default Plot
}
