import { useEffect, useRef } from 'react'

import { levels, type ContentBlock, type Technique } from './catalog'
import { TechniqueIllustration } from './TechniqueIllustration'

function InlineText({ text }: { text: string }) {
  return text.split(/(\*\*[^*]+\*\*|\[[^\]]+\]\(https:\/\/[^\s)]+\))/g).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index}>{part.slice(2, -2)}</strong>
    }
    const link = /^\[([^\]]+)\]\((https:\/\/[^\s)]+)\)$/.exec(part)
    return link ? (
      <a key={index} href={link[2]} target="_blank" rel="noreferrer">
        {link[1]}
      </a>
    ) : (
      part
    )
  })
}

function Block({ block }: { block: ContentBlock }) {
  if (block.type === 'paragraph')
    return (
      <p>
        <InlineText text={block.text} />
      </p>
    )
  const List = block.type === 'ordered' ? 'ol' : 'ul'
  return (
    <List>
      {block.items.map((item, index) => (
        <li key={index}>
          <InlineText text={item} />
        </li>
      ))}
    </List>
  )
}

export function TechniqueDialog({
  technique,
  onClose,
}: {
  technique: Technique
  onClose: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const close = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const element = dialog.current!
    const opener = document.activeElement
    const previousOverflow = document.body.style.overflow
    element.showModal()
    document.body.style.overflow = 'hidden'
    close.current?.focus()
    return () => {
      element.close()
      document.body.style.overflow = previousOverflow
      if (opener instanceof HTMLElement) opener.focus()
    }
  }, [])

  return (
    <dialog
      ref={dialog}
      className="technique-dialog"
      aria-labelledby="technique-title"
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className="technique-dialog__surface">
        <header className="technique-dialog__header">
          <span className={`technique-level technique-level--${technique.difficulty}`}>
            {levels.find((level) => level.id === technique.difficulty)?.label}
          </span>
          <button
            ref={close}
            type="button"
            className="button button--ghost"
            aria-label="Cerrar técnica"
            onClick={onClose}
          >
            Cerrar <span aria-hidden="true">×</span>
          </button>
        </header>
        <div className="technique-dialog__intro">
          <TechniqueIllustration technique={technique} />
          <h2 id="technique-title">{technique.title}</h2>
        </div>
        <div className="technique-dialog__content">
          {technique.blocks.map((block, index) => (
            <Block key={index} block={block} />
          ))}
          <p className="technique-review">
            Manual de MiniPaint AI elaborado con asistencia de IA y fuentes enlazadas. Pendiente de
            revisión práctica por expertos.
          </p>
        </div>
      </div>
    </dialog>
  )
}
