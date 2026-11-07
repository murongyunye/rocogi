import { defineComponent, h, type PropType } from 'vue'
import { cx, runeTextModule, runeTextPrefixCls } from './rk'

export type RuneFont = 'base' | 'rune' | 'text'

/** Port of rocokingdom-ui RuneText (verbatim classes). */
export default defineComponent({
  name: 'RkRuneText',
  inheritAttrs: false,
  props: {
    as: { type: [String, Object], default: 'span' },
    font: { type: String as PropType<RuneFont>, default: 'base' },
    prefixCls: { type: String, default: runeTextPrefixCls },
    rootClassName: { type: String, default: undefined },
  },
  setup(props, { attrs, slots }) {
    return () =>
      h(
        props.as,
        {
          ...attrs,
          class: cx(props.prefixCls, runeTextModule.text, runeTextModule[props.font], props.rootClassName, attrs.class as string),
        },
        slots.default?.(),
      )
  },
})
