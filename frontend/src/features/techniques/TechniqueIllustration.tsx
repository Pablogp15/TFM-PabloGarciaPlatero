import { useId } from 'react'

import type { Technique } from './catalog'

const descriptions: Record<string, string> = {
  '02': 'Lima retirando rebabas de una pieza antes de pintarla',
  '03': 'Piezas alineadas y unidas para comprobar el montaje',
  '04': 'Mano sujetando un mango de pintura sobre un apoyo estable',
  '05': 'Pincel con punta, vientre, virola y mango diferenciados',
  '06': 'Pincel que se limpia en agua junto a su funda de protección',
  '07': 'Gotas de agua junto a pintura para ajustar su dilución',
  '08': 'Paleta húmeda con esponja, membrana y mezclas de color',
  '09': 'Película de imprimación uniforme sobre una pieza',
  '10': 'Pincel cubriendo una pieza con una capa base de color',
  '11': 'Lavado oscuro concentrado en los recovecos de una pieza',
  '12': 'Pincel ancho rozando los salientes claros de una roca',
  '13': 'Aristas claras que definen una placa de armadura',
  '14': 'Transición progresiva desde sombra azul hasta luz turquesa',
  '15': 'Capas translúcidas que suavizan una transición de color',
  '16': 'Puntos de pintura con densidades diferentes para crear textura',
  '17': 'Reflejos pintados claros y oscuros simulando metal sin pigmentos metálicos',
  '18': 'Superficie metálica con brillo y reflejos',
  '19': 'Rostro con zonas de luz, medios tonos y sombra',
  '20': 'Tela con sombras en los pliegues y luces en las crestas',
  '21': 'Aerógrafo pulverizando una transición amplia de pintura',
  '22': 'Pincel corrigiendo una mancha sobre el color base',
  '23': 'Capa transparente de protección sobre una pieza terminada',
}

function Brush({ wide = false }: { wide?: boolean }) {
  return (
    <g transform="translate(146 30) rotate(38)">
      <rect x="0" width="12" height="58" rx="5" fill="#bc8053" />
      <path d="M0 51h12v19H0z" fill="#aebac3" />
      <path d={wide ? 'M-9 70h30l-3 24H-6z' : 'M0 70h12Q14 87 6 99Q-2 87 0 70'} fill="#e8d6b6" />
    </g>
  )
}

export function TechniqueIllustration({ technique }: { technique: Technique }) {
  const gradient = useId()
  const id = technique.id
  let scene
  if (id === '02') {
    scene = (
      <>
        <path d="M38 129l23-58 42-16 29 43-25 38z" fill="#a8b1ba" />
        <path d="M60 70l42-17 7 9-43 17" fill="#e4e8e9" />
        <g transform="translate(130 27) rotate(38)">
          <rect width="23" height="76" rx="3" fill="#c6cdd1" />
          <path d="M3 10h17M3 20h17M3 30h17M3 40h17M3 50h17" stroke="#67737b" />
          <rect y="76" width="23" height="35" rx="6" fill="#bd8358" />
        </g>
      </>
    )
  } else if (id === '03') {
    scene = (
      <>
        <path d="M48 119V75l25-19 25 19v44zM120 119V75l25-19 25 19v44z" fill="#98a8b3" />
        <path d="M99 88h20m-8-7 8 7-8 7" stroke="#efc47d" strokeWidth="3" fill="none" />
        <path d="M144 33c-14 18-14 24 0 24s14-6 0-24" fill="#b9dcd5" />
      </>
    )
  } else if (id === '04') {
    scene = (
      <>
        <path d="M40 151v-31q0-14 12-14l20 16 31-16q15-6 18 7l-20 23-5 15" fill="#c98c71" />
        <rect x="80" y="99" width="40" height="38" rx="12" fill="#897064" />
        <ellipse cx="100" cy="99" rx="30" ry="8" fill="#bdac96" />
        <path d="M85 90l4-28 11-14 11 14 4 28z" fill="#aabcc5" />
        <circle cx="100" cy="43" r="10" fill="#aabcc5" />
        <path d="M135 134h46" stroke="#e8d6b6" strokeWidth="6" strokeLinecap="round" />
      </>
    )
  } else if (id === '05') {
    scene = (
      <>
        <g transform="translate(26 83) rotate(-14)">
          <path d="M0 0q20-17 42-8v16Q20 17 0 0" fill="#e8d6b6" />
          <path d="M42-8h27V8H42z" fill="#b4c0c8" />
          <rect x="69" y="-7" width="110" height="14" rx="7" fill="#bc8053" />
        </g>
        <g fill="#f0d9b7" fontSize="10" textAnchor="middle">
          <text x="35" y="118">
            Punta
          </text>
          <text x="77" y="48">
            Vientre
          </text>
          <text x="113" y="108">
            Virola
          </text>
          <text x="167" y="36">
            Mango
          </text>
        </g>
      </>
    )
  } else if (id === '06') {
    scene = (
      <>
        <path d="M54 68h66l-7 76H61z" fill="#c1e2df" opacity=".8" />
        <path d="M59 94h57l-4 44H63z" fill="#6da5b8" />
        <path d="M82 38l10 72" stroke="#bd8358" strokeWidth="10" strokeLinecap="round" />
        <path d="M83 111l12-2-2 18-8 1z" fill="#dce3dd" />
        <rect
          x="153"
          y="48"
          width="18"
          height="93"
          rx="8"
          fill="none"
          stroke="#c7c9be"
          strokeWidth="3"
        />
      </>
    )
  } else if (id === '07') {
    scene = (
      <>
        <ellipse cx="100" cy="114" rx="62" ry="25" fill="#b98064" />
        <ellipse cx="101" cy="114" rx="39" ry="13" fill="#d9a08a" />
        <path
          d="M84 32c-23 29-22 44 0 44s23-15 0-44M135 48c-16 21-15 31 0 31s16-10 0-31"
          fill="#8ec8d7"
        />
        <path d="M149 90l24-22" stroke="#e8d6b6" strokeWidth="7" strokeLinecap="round" />
      </>
    )
  } else if (id === '08') {
    scene = (
      <>
        <rect x="30" y="42" width="160" height="100" rx="16" fill="#536b70" />
        <rect x="39" y="48" width="142" height="80" rx="10" fill="#a0bfba" />
        <rect x="45" y="49" width="130" height="68" rx="6" fill="#e6e1ce" />
        <g>
          <ellipse cx="72" cy="73" rx="14" ry="9" fill="#bb6c56" />
          <ellipse cx="112" cy="73" rx="14" ry="9" fill="#50858a" />
          <ellipse cx="151" cy="73" rx="12" ry="9" fill="#d7ae59" />
          <path d="M65 100q48-20 92 0" stroke="#a6b1a1" strokeWidth="9" fill="none" />
        </g>
      </>
    )
  } else if (id === '12') {
    scene = (
      <>
        <path d="M36 139l21-44 24 8 18-22 35 30 18 28z" fill="#607a84" />
        <path
          d="M43 124l14-29 24 8 18-22 24 20"
          fill="none"
          stroke="#c5dcd4"
          strokeWidth="6"
          strokeLinejoin="round"
        />
        <Brush wide />
      </>
    )
  } else if (id === '19') {
    scene = (
      <>
        <path d="M68 149v-16l17-14h51l17 14v16" fill="#536975" />
        <path d="M77 57q32-34 64 0v41l-19 25H98L77 98z" fill="#b47a63" />
        <path d="M109 44q28 0 32 15v36l-19 24h-13z" fill="#d9a285" />
        <path
          d="M86 75h14m20 0h13M108 80l-5 14h11m-12 14h16"
          stroke="#775345"
          strokeWidth="3"
          fill="none"
        />
      </>
    )
  } else if (id === '20') {
    scene = (
      <>
        <path d="M62 40h95l26 101q-22 10-42 0-26 13-49 0-22 8-52 0z" fill="#466b82" />
        <path
          d="M75 50l-9 87m34-87-4 91m28-90 10 90m9-90 17 88"
          stroke="#254150"
          strokeWidth="12"
        />
        <path d="M83 50l-3 82m29-81 6 83m31-78 15 75" stroke="#91b7bd" strokeWidth="5" />
      </>
    )
  } else if (id === '21') {
    scene = (
      <>
        <path d="M35 50h71v10H35zM43 42h22v8H43zM60 60l15 22-10 5-18-27" fill="#bcc8cd" />
        <path d="M101 55l64-21v87l-64-61" fill={`url(#${gradient})`} opacity=".7" />
        <path d="M167 34h18v99h-18z" fill="#65989d" />
        <path d="M35 60q-21 23-3 55" fill="none" stroke="#6d7882" strokeWidth="5" />
      </>
    )
  } else {
    const nmm = id === '17'
    const metallic = id === '18'
    scene = (
      <>
        <path
          d="M64 42h92v60l-46 40-46-40z"
          fill={
            ['14', '15', '17', '18'].includes(id)
              ? `url(#${gradient})`
              : id === '09'
                ? '#a7b1b9'
                : '#578494'
          }
          stroke="#a2c4c5"
          strokeWidth="2"
        />
        {id === '11' && (
          <path d="M73 51l37 51 37-51m-37 51v28" fill="none" stroke="#213d4c" strokeWidth="8" />
        )}
        {id === '13' && (
          <path d="M66 44h88v57l-44 38" fill="none" stroke="#edecd0" strokeWidth="5" />
        )}
        {id === '15' && (
          <>
            <path d="M64 68h92v16H64zM64 95h92l-46 40-46-40z" fill="#b1d1c3" opacity=".3" />
            <path d="M45 62l-7 33m-6-8 6 8 9-4" stroke="#c1d8c9" fill="none" strokeWidth="2" />
          </>
        )}
        {id === '16' &&
          Array.from({ length: 28 }, (_, i) => (
            <circle
              key={i}
              cx={75 + (i % 7) * 11}
              cy={53 + Math.floor(i / 7) * 15}
              r={1.4 + Math.floor(i / 7) * 0.6}
              fill="#d4e2cb"
            />
          ))}
        {nmm && (
          <>
            <path d="M64 42h92l-92 55z" fill="#e4e7da" />
            <path d="M64 99l92-32v22l-82 23z" fill="#283e4b" />
            <path d="M109 103l47-17v16l-46 40z" fill="#e6e8db" />
          </>
        )}
        {metallic && (
          <>
            <path d="M110 46v87" stroke="#f1e0ad" strokeWidth="3" />
            <path d="M161 42v19m-10-9h20M142 107v13m-7-6h14" stroke="#fff0c9" strokeWidth="2" />
          </>
        )}
        {id === '22' && (
          <>
            <path d="M90 84q18-16 33 5l-8 17-27-6z" fill="#b65b50" />
            <path d="M88 85h20v18H88z" fill="#578494" />
            <Brush />
          </>
        )}
        {id === '23' && (
          <>
            <path
              d="M58 36h104v69l-52 44-52-44z"
              fill="#d1e4d5"
              opacity=".2"
              stroke="#e6efe3"
              strokeWidth="3"
            />
            <path d="M78 53l-6 24M158 30v18m-9-9h18" stroke="#eff2de" strokeWidth="3" />
          </>
        )}
        {['09', '10'].includes(id) && <Brush />}
      </>
    )
  }

  return (
    <svg
      className="technique-illustration"
      viewBox="0 0 220 170"
      role="img"
      aria-label={descriptions[id]}
    >
      <defs>
        <linearGradient id={gradient} x1="0" x2="1" y1="1" y2="0">
          <stop stopColor={id === '18' ? '#665031' : '#233b50'} />
          <stop offset=".5" stopColor={id === '18' ? '#d0ad62' : '#568a9c'} />
          <stop offset="1" stopColor={id === '18' ? '#fff0c9' : '#d0e6d3'} />
        </linearGradient>
      </defs>
      <rect width="220" height="170" rx="12" fill="#263c46" />
      <circle cx="175" cy="24" r="63" fill="#37545d" opacity=".45" />
      <ellipse cx="110" cy="149" rx="78" ry="5" fill="#152c37" opacity=".7" />
      {scene}
    </svg>
  )
}
