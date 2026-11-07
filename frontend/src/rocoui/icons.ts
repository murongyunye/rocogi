import { defineComponent, h } from 'vue'

/**
 * Minimal Check / Cross icons (lucide-compatible paths). The upstream package
 * imports them from an external icon lib, so the Vue port ships its own.
 */
export const IconCheck = defineComponent({
  name: 'RkIconCheck',
  inheritAttrs: false,
  setup(_, { attrs }) {
    return () =>
      h('svg', {
        'aria-hidden': 'true',
        focusable: 'false',
        viewBox: '0 0 24 24',
        fill: 'none',
        stroke: 'currentColor',
        'stroke-width': 2.5,
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        ...attrs,
      }, [h('path', { d: 'M20 6 9 17l-5-5' })])
  },
})

export const IconCross = defineComponent({
  name: 'RkIconCross',
  inheritAttrs: false,
  setup(_, { attrs }) {
    return () =>
      h('svg', {
        'aria-hidden': 'true',
        focusable: 'false',
        viewBox: '0 0 24 24',
        fill: 'none',
        stroke: 'currentColor',
        'stroke-width': 2.5,
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        ...attrs,
      }, [h('path', { d: 'M18 6 6 18M6 6l12 12' })])
  },
})
