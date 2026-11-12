import { describeError } from '../../lib/http'
import { useToggleWishlist, useWishlistIds } from './useWishlist'

export function WishlistButton({ paintId, name }: { paintId: string; name: string }) {
  const ids = useWishlistIds()
  const toggle = useToggleWishlist()
  const wished = ids.data?.includes(paintId) ?? false
  const error = ids.error ?? toggle.error

  return (
    <div>
      <button
        className="button button--ghost wishlist-heart"
        type="button"
        aria-pressed={wished}
        aria-label={`${wished ? 'Quitar' : 'Añadir'} ${name} ${wished ? 'de' : 'a'} deseados`}
        title={wished ? 'Quitar de deseados' : 'Añadir a deseados'}
        disabled={!ids.data || toggle.isPending || ids.isFetching}
        onClick={() => toggle.mutate({ paintId, wished })}
      >
        <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M12 21 3.4 12.4C-2 7 5.8-1 12 6c6.2-7 14 1 8.6 6.4Z"
            fill={wished ? 'currentColor' : 'none'}
            stroke="currentColor"
            strokeWidth="1.7"
          />
        </svg>
      </button>
      {error && (
        <p className="form-error" role="alert">
          {describeError(error)}
        </p>
      )}
    </div>
  )
}
