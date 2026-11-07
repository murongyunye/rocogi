import { defineComponent, h, type PropType } from 'vue'
import Material from './Material'
import { cx, layoutModule, layoutPrefixCls, resolveSizePx, type MaterialName } from './rk'

/** Port of rocokingdom-ui Layout (verbatim classes). */
export default defineComponent({
  name: 'RkLayout',
  inheritAttrs: false,
  props: {
    as: { type: String, default: 'section' },
    direction: { type: String as PropType<'vertical' | 'horizontal'>, default: 'vertical' },
    fullHeight: { type: Boolean, default: false },
    material: { type: String as PropType<MaterialName>, default: 'paper' },
    prefixCls: { type: String, default: layoutPrefixCls },
    rootClassName: { type: String, default: undefined },
  },
  setup(props, { attrs, slots }) {
    return () => {
      const { class: _class, ...rest } = attrs
      return h(Material, { asChild: true, material: props.material }, () => [
        h(
          props.as ?? 'section',
          {
            ...rest,
            'data-direction': props.direction,
            class: cx(
              props.prefixCls,
              layoutModule.layout,
              layoutModule[props.direction],
              props.fullHeight && layoutModule.fullHeight,
              props.rootClassName,
              attrs.class as string,
            ),
          },
          slots.default?.(),
        ),
      ])
    }
  },
})
