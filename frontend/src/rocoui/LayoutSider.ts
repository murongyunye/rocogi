import { computed, defineComponent, h, useAttrs, type PropType } from 'vue'
import Material from './Material'
import { cx, layoutModule, layoutSiderPrefixCls, resolveSizePx, type MaterialName } from './rk'

/** Port of rocokingdom-ui LayoutSider (verbatim classes). */
export default defineComponent({
  name: 'RkLayoutSider',
  inheritAttrs: false,
  props: {
    as: { type: String, default: 'aside' },
    collapsed: { type: Boolean, default: false },
    collapsedWidth: { type: [Number, String] as PropType<number | string>, default: undefined },
    material: { type: String as PropType<MaterialName>, default: 'stoneSoft' },
    prefixCls: { type: String, default: layoutSiderPrefixCls },
    rootClassName: { type: String, default: undefined },
    width: { type: [Number, String] as PropType<number | string>, default: undefined },
  },
  setup(props, { attrs, slots }) {
    const siderStyle = computed(() => {
      const style: Record<string, string> = { ...((attrs.style ?? {}) as Record<string, string>) }
      const resolvedWidth = resolveSizePx(props.width)
      const resolvedCollapsedWidth = resolveSizePx(props.collapsedWidth)
      if (resolvedWidth) style['--rk-layout-sider-width'] = resolvedWidth
      if (resolvedCollapsedWidth) style['--rk-layout-sider-collapsed-width'] = resolvedCollapsedWidth
      return style
    })
    return () => {
      const { class: _class, style: _style, ...rest } = attrs
      return h(Material, { asChild: true, material: props.material }, () => [
        h(
          props.as ?? 'aside',
          {
            ...rest,
            'data-collapsed': props.collapsed || undefined,
            class: cx(
              props.prefixCls,
              layoutModule.sider,
              props.collapsed && layoutModule.siderCollapsed,
              props.rootClassName,
              attrs.class as string,
            ),
            style: siderStyle.value,
          },
          slots.default?.(),
        ),
      ])
    }
  },
})
