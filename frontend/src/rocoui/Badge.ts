import { defineComponent, h, type PropType, type VNodeChild } from 'vue'
import { cx } from './rk'

/**
 * Badge — documented on the docs site but not included in the beta npm package.
 * Dependency-free approximation styled with the --rk-* token set.
 */
export default defineComponent({
  name: 'RkBadge',
  props: {
    color: { type: String as PropType<'danger' | 'paper' | 'primary' | 'stone' | 'success'>, default: 'primary' },
    dot: { type: Boolean, default: false },
    variant: { type: String as PropType<'outline' | 'solid' | 'text'>, default: 'solid' },
  },
  setup(props, { slots }) {
    return (): VNodeChild =>
      h(
        'span',
        {
          class: cx('rk-badge', `rk-badge-${props.color}`, `rk-badge-${props.variant}`),
          'data-rk-badge': 'true',
        },
        [props.dot ? h('span', { 'aria-hidden': true, class: 'rk-badge-dot' }) : null, slots.default?.()],
      )
  },
})
