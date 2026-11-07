import { defineComponent, h, type PropType } from 'vue'
import Space from './Space'
import { cx, spaceModule, stackPrefixCls } from './rk'

/** Port of rocokingdom-ui Stack: vertical block Space with rk-stack prefix. */
export default defineComponent({
  name: 'RkStack',
  inheritAttrs: false,
  props: {
    align: { type: String as PropType<'start' | 'center' | 'end' | 'stretch' | 'baseline'>, default: undefined },
    as: { type: String, default: 'div' },
    block: { type: Boolean, default: true },
    justify: { type: String as PropType<'start' | 'center' | 'end' | 'between' | 'around' | 'evenly'>, default: undefined },
    rootClassName: { type: String, default: undefined },
    size: { type: [String, Number, Array] as PropType<'compact' | 'small' | 'middle' | 'large' | number | string | [number | string, number | string]>, default: 'middle' },
    wrap: { type: Boolean, default: false },
  },
  setup(props, { attrs, slots }) {
    return () => {
      const { class: _class, ...rest } = attrs
      return h(
        Space,
        {
          ...rest,
          align: props.align,
          as: props.as,
          block: props.block,
          justify: props.justify,
          prefixCls: stackPrefixCls,
          rootClassName: cx(spaceModule.stack, props.rootClassName),
          size: props.size,
          wrap: props.wrap,
          class: attrs.class as string,
        },
        { default: slots.default },
      )
    }
  },
})
