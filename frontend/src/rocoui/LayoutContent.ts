import { defineComponent, h, type PropType } from 'vue'
import Material from './Material'
import { cx, layoutContentPrefixCls, layoutModule, type MaterialName } from './rk'

/** Port of rocokingdom-ui LayoutContent (verbatim classes). */
export default defineComponent({
  name: 'RkLayoutContent',
  inheritAttrs: false,
  props: {
    as: { type: String, default: 'main' },
    material: { type: String as PropType<MaterialName>, default: 'paperSoft' },
    padded: { type: Boolean, default: true },
    prefixCls: { type: String, default: layoutContentPrefixCls },
    rootClassName: { type: String, default: undefined },
  },
  setup(props, { attrs, slots }) {
    return () => {
      const { class: _class, ...rest } = attrs
      return h(Material, { asChild: true, material: props.material }, () => [
        h(
          props.as ?? 'main',
          {
            ...rest,
            'data-padded': props.padded,
            class: cx(
              props.prefixCls,
              layoutModule.content,
              !props.padded && layoutModule.unpadded,
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
