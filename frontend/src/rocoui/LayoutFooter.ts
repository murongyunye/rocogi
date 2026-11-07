import { computed, defineComponent, h, useAttrs, type PropType } from 'vue'
import Material from './Material'
import { cx, layoutFooterPrefixCls, layoutModule, resolveSizePx, type MaterialName } from './rk'

/** Port of rocokingdom-ui LayoutFooter (verbatim classes). */
export default defineComponent({
  name: 'RkLayoutFooter',
  inheritAttrs: false,
  props: {
    as: { type: String, default: 'footer' },
    height: { type: [Number, String] as PropType<number | string>, default: undefined },
    material: { type: String as PropType<MaterialName>, default: 'paper' },
    prefixCls: { type: String, default: layoutFooterPrefixCls },
    rootClassName: { type: String, default: undefined },
  },
  setup(props, { attrs, slots }) {
    const footerStyle = computed(() => {
      const style: Record<string, string> = { ...((attrs.style ?? {}) as Record<string, string>) }
      const resolvedHeight = resolveSizePx(props.height)
      if (resolvedHeight) style['--rk-layout-footer-height'] = resolvedHeight
      return style
    })
    return () => {
      const { class: _class, style: _style, ...rest } = attrs
      return h(Material, { asChild: true, material: props.material }, () => [
        h(
          props.as ?? 'footer',
          {
            ...rest,
            class: cx(
              props.prefixCls,
              layoutModule.footer,
              props.rootClassName,
              attrs.class as string,
            ),
            style: footerStyle.value,
          },
          slots.default?.(),
        ),
      ])
    }
  },
})
