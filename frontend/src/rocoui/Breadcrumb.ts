import { defineComponent, h, type PropType, type VNodeChild } from 'vue'
import { cx } from './rk'

/**
 * Breadcrumb — documented on the docs site but not included in the beta npm package.
 * nav > ol with chevron separators; items via `items` prop or default slot.
 */
export default defineComponent({
  name: 'RkBreadcrumb',
  props: {
    items: { type: Array as PropType<Array<{ label: string; href?: string; onClick?: (event: MouseEvent) => void }>>, default: undefined },
  },
  setup(props, { slots }) {
    return (): VNodeChild => {
      const slotted = slots.default?.()
      if (slotted) {
        return h('nav', { 'aria-label': 'Breadcrumb', class: 'rk-breadcrumb', 'data-rk-breadcrumb': 'true' }, slotted)
      }
      const items = props.items ?? []
      return h(
        'nav',
        { 'aria-label': 'Breadcrumb', class: 'rk-breadcrumb', 'data-rk-breadcrumb': 'true' },
        h(
          'ol',
          { class: 'rk-breadcrumb-list' },
          items.map((item, index) =>
            h('li', { class: 'rk-breadcrumb-item', key: `${item.label}-${index}` }, [
              item.href
                ? h('a', { class: 'rk-breadcrumb-link', href: item.href }, item.label)
                : h(
                    'button',
                    {
                      class: 'rk-breadcrumb-link',
                      onClick: item.onClick,
                      type: 'button',
                    },
                    item.label,
                  ),
              index < items.length - 1
                ? h('span', { 'aria-hidden': true, class: 'rk-breadcrumb-separator' }, '›')
                : null,
            ]),
          ),
        ),
      )
    }
  },
})
