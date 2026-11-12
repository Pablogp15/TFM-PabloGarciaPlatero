import { useState, type KeyboardEvent, type PointerEvent } from 'react'

interface PaintColorSearchProps {
  value: string
  onSearch: (hex: string | undefined) => void
}

const WHEEL_CENTER = 110
const WHEEL_OUTER_RADIUS = 100
const WHEEL_INNER_RADIUS = 58
const WHEEL_SEGMENTS = 72

function normalizeHex(value: string): string | null {
  const match = /^#?([0-9a-f]{6})$/i.exec(value.trim())
  return match ? `#${match[1].toUpperCase()}` : null
}

function hexToHsl(hex: string): [number, number, number] {
  const normalized = normalizeHex(hex)
  if (!normalized) return [0, 85, 55]
  const channels = [1, 3, 5].map(
    (index) => Number.parseInt(normalized.slice(index, index + 2), 16) / 255,
  )
  const [red, green, blue] = channels
  const max = Math.max(red, green, blue)
  const min = Math.min(red, green, blue)
  const delta = max - min
  let hue = 0

  if (delta !== 0) {
    if (max === red) hue = 60 * (((green - blue) / delta) % 6)
    else if (max === green) hue = 60 * ((blue - red) / delta + 2)
    else hue = 60 * ((red - green) / delta + 4)
  }
  if (hue < 0) hue += 360

  const lightness = (max + min) / 2
  const saturation = delta === 0 ? 0 : (delta / (1 - Math.abs(2 * lightness - 1))) * 100
  return [hue, saturation, lightness * 100]
}

function hslToHex(hue: number, saturation: number, lightness: number): string {
  const s = saturation / 100
  const l = lightness / 100
  const chroma = (1 - Math.abs(2 * l - 1)) * s
  const x = chroma * (1 - Math.abs(((hue / 60) % 2) - 1))
  const match = l - chroma / 2
  const [red, green, blue] =
    hue < 60
      ? [chroma, x, 0]
      : hue < 120
        ? [x, chroma, 0]
        : hue < 180
          ? [0, chroma, x]
          : hue < 240
            ? [0, x, chroma]
            : hue < 300
              ? [x, 0, chroma]
              : [chroma, 0, x]
  return `#${[red, green, blue]
    .map((channel) =>
      Math.round((channel + match) * 255)
        .toString(16)
        .padStart(2, '0'),
    )
    .join('')
    .toUpperCase()}`
}

function wheelSlicePath(index: number): string {
  const start = (index / WHEEL_SEGMENTS) * 360 - 90
  const end = ((index + 1) / WHEEL_SEGMENTS) * 360 - 90
  const point = (radius: number, degrees: number) => {
    const radians = (degrees * Math.PI) / 180
    return [WHEEL_CENTER + radius * Math.cos(radians), WHEEL_CENTER + radius * Math.sin(radians)]
  }
  const [outerStartX, outerStartY] = point(WHEEL_OUTER_RADIUS, start)
  const [outerEndX, outerEndY] = point(WHEEL_OUTER_RADIUS, end)
  const [innerStartX, innerStartY] = point(WHEEL_INNER_RADIUS, start)
  const [innerEndX, innerEndY] = point(WHEEL_INNER_RADIUS, end)

  return [
    `M ${outerStartX} ${outerStartY}`,
    `A ${WHEEL_OUTER_RADIUS} ${WHEEL_OUTER_RADIUS} 0 0 1 ${outerEndX} ${outerEndY}`,
    `L ${innerEndX} ${innerEndY}`,
    `A ${WHEEL_INNER_RADIUS} ${WHEEL_INNER_RADIUS} 0 0 0 ${innerStartX} ${innerStartY}`,
    'Z',
  ].join(' ')
}

export function PaintColorSearch({ value, onSearch }: PaintColorSearchProps) {
  const initialHsl = value ? hexToHsl(value) : [0, 85, 55]
  const [hexInput, setHexInput] = useState(value)
  const [hue, setHue] = useState(initialHsl[0])
  const [saturation, setSaturation] = useState(initialHsl[1])
  const [lightness, setLightness] = useState(initialHsl[2])
  const [error, setError] = useState<string | null>(null)
  const markerAngle = ((hue - 90) * Math.PI) / 180
  const markerRadius = (WHEEL_OUTER_RADIUS + WHEEL_INNER_RADIUS) / 2
  const markerX = WHEEL_CENTER + markerRadius * Math.cos(markerAngle)
  const markerY = WHEEL_CENTER + markerRadius * Math.sin(markerAngle)

  function updateFromHue(nextHue: number) {
    const normalizedHue = (nextHue + 360) % 360
    const nextSaturation = saturation === 0 ? 85 : saturation
    setHue(normalizedHue)
    setSaturation(nextSaturation)
    setHexInput(hslToHex(normalizedHue, nextSaturation, lightness))
    setError(null)
  }

  function handleWheelPointer(event: PointerEvent<SVGSVGElement>) {
    const bounds = event.currentTarget.getBoundingClientRect()
    const scaleX = 220 / bounds.width
    const scaleY = 220 / bounds.height
    const x = (event.clientX - bounds.left) * scaleX - WHEEL_CENTER
    const y = (event.clientY - bounds.top) * scaleY - WHEEL_CENTER
    if (Math.hypot(x, y) < WHEEL_INNER_RADIUS - 4) return
    updateFromHue((Math.atan2(y, x) * 180) / Math.PI + 90)
  }

  function handleWheelKeyDown(event: KeyboardEvent<SVGSVGElement>) {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    event.preventDefault()
    updateFromHue(hue + (event.key === 'ArrowRight' ? 5 : -5))
  }

  function handleSearch() {
    const normalized = normalizeHex(hexInput)
    if (!normalized) {
      setError('Introduce un color hexadecimal válido, por ejemplo #A34F28.')
      return
    }
    setHexInput(normalized)
    setError(null)
    onSearch(normalized)
  }

  function handleHexChange(value: string) {
    setHexInput(value)
    setError(null)
    const normalized = normalizeHex(value)
    if (normalized) {
      const [nextHue, nextSaturation, nextLightness] = hexToHsl(normalized)
      setHue(nextHue)
      setSaturation(nextSaturation)
      setLightness(nextLightness)
    }
  }

  return (
    <section className="paint-color-search" aria-labelledby="paint-color-search-title">
      <div className="paint-color-search__intro">
        <div>
          <h2 id="paint-color-search-title">Buscar por color</h2>
          <p className="muted">
            Elige un matiz y ajusta el tono de oscuro a claro para encontrar pinturas similares.
          </p>
        </div>
        <span
          className="paint-color-search__preview"
          style={{ backgroundColor: hexInput }}
          role="img"
          aria-label={`Color seleccionado ${hexInput || 'ninguno'}`}
        />
      </div>

      <div className="paint-color-search__controls">
        <div className="paint-color-search__wheel-wrap">
          <svg
            className="paint-color-search__wheel"
            viewBox="0 0 220 220"
            role="slider"
            aria-label="Matiz del color"
            aria-valuemin={0}
            aria-valuemax={359}
            aria-valuenow={Math.round(hue)}
            aria-valuetext={`Matiz ${Math.round(hue)} grados`}
            tabIndex={0}
            onPointerDown={handleWheelPointer}
            onKeyDown={handleWheelKeyDown}
          >
            {Array.from({ length: WHEEL_SEGMENTS }, (_, index) => {
              const segmentHue = (index / WHEEL_SEGMENTS) * 360
              return (
                <path
                  key={index}
                  d={wheelSlicePath(index)}
                  fill={`hsl(${segmentHue} 90% 55%)`}
                  stroke="var(--color-surface)"
                  strokeWidth="0.5"
                />
              )
            })}
            <circle
              cx={WHEEL_CENTER}
              cy={WHEEL_CENTER}
              r={WHEEL_INNER_RADIUS - 3}
              fill={hexInput || '#ffffff'}
              stroke="var(--color-border)"
              strokeWidth="2"
            />
            <circle
              cx={markerX}
              cy={markerY}
              r="7"
              fill={hexInput || `hsl(${hue} 90% 55%)`}
              stroke="#ffffff"
              strokeWidth="3"
            />
          </svg>
          <span className="field-hint">Haz clic en el disco para elegir el matiz</span>
        </div>

        <div className="paint-color-search__settings">
          <label className="filter-field" htmlFor="paint-color-hex">
            Código hexadecimal
            <input
              id="paint-color-hex"
              type="text"
              value={hexInput}
              onChange={(event) => handleHexChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  handleSearch()
                }
              }}
              placeholder="#A34F28"
              maxLength={7}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? 'paint-color-error' : 'paint-color-hint'}
            />
          </label>

          <label className="filter-field" htmlFor="paint-color-lightness">
            Tono · {lightness}%
            <input
              id="paint-color-lightness"
              className="paint-color-search__lightness"
              type="range"
              min={0}
              max={100}
              value={lightness}
              onChange={(event) => {
                const nextLightness = Number(event.target.value)
                setLightness(nextLightness)
                setHexInput(hslToHex(hue, saturation, nextLightness))
                setError(null)
              }}
              aria-valuetext={`${lightness}% de luminosidad`}
            />
          </label>
          <div
            className="paint-color-search__lightness-preview"
            style={{
              background: `linear-gradient(to right, hsl(${hue} ${saturation}% 0%), hsl(${hue} ${saturation}% 50%), hsl(${hue} ${saturation}% 100%))`,
            }}
            aria-hidden="true"
          />
          <div className="paint-color-search__range-labels" aria-hidden="true">
            <span>Oscuro</span>
            <span>Claro</span>
          </div>
          <p id="paint-color-hint" className="field-hint">
            Puedes pegar un HEX con o sin #. La búsqueda compara los colores en CIELAB.
          </p>
          {error && (
            <p className="form-error" id="paint-color-error" role="alert">
              {error}
            </p>
          )}
          <button className="button" type="button" onClick={handleSearch}>
            Buscar este color
          </button>
          {value && (
            <button
              className="button button--ghost"
              type="button"
              onClick={() => onSearch(undefined)}
            >
              Quitar búsqueda por color
            </button>
          )}
        </div>
      </div>
    </section>
  )
}
