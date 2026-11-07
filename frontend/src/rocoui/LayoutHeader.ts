import { computed, defineComponent, h, useAttrs, type PropType } from 'vue'
import Material from './Material'
import { cx, layoutModule, layoutHeaderPrefixCls, resolveSizePx, type MaterialName } from './rk'

/** Port of rocokingdom-ui LayoutHeader (verbatim classes). */
export default defineComponent({
  name: 'RkLayoutHeader',
  inheritAttrs: false,
  props: {
    as: { type: String, default: 'header' },
    height: { type: [Number, String] as PropType<number | string>, default: undefined },
    material: { type: String as PropType<MaterialName>, default: 'stone' },
    prefixCls: { type: String, default: layoutHeaderPrefixCls },
    rootClassName: { type: String, default: undefined },
  },
  setup(props, { attrs, slots }) {
    const headerStyle = computed(() => {
      const style: Record<string, string> = { ...((attrs.style ?? {}) as Record<string, string>) }
      const resolvedHeight = resolveSizePx(props.height)
      if (resolvedHeight) style['--rk-layout-header-height'] = resolvedHeight
      return style
    })
    return () => {
      const { class: _class, style: _style, ...rest } = attrs
      return h(Material, { asChild: true, material: props.material }, () => [
        h(
          props.as ?? 'header',
          {
            ...rest,
            class: cx(
              props.prefixCls,
              layoutModule.header,
              props.rootClassName,
              attrs.class as string,
            ),
            style: headerStyle.value,
          },
          slots.default?.(),
        ),
      ])
    }
  },
})
