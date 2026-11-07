import { cloneVNode, Comment, defineComponent, h, isVNode, type PropType, type VNode, type VNodeChild } from 'vue'
import { cx, materialModule, materialPrefixCls, resolveMaterial, type MaterialName } from './rk'

export interface MaterialValue {
  background: string
  color: string
  style: Record<string, string>
}

/**
 * Port of rocokingdom-ui Material (verbatim behavior):
 * resolves a material preset into --rk-material-background/--rk-material-color
 * and renders either a Tag, merges into a child (asChild) or calls render().
 */
export default defineComponent({
  name: 'RkMaterial',
  inheritAttrs: false,
  props: {
    as: { type: String, default: undefined },
    asChild: { type: Boolean, default: false },
    background: { type: String, default: undefined },
    color: { type: String, default: undefined },
    material: { type: String as PropType<MaterialName>, default: 'paper' },
    render: { type: Function as PropType<(value: MaterialValue) => VNodeChild>, default: undefined },
  },
  setup(props, { attrs, slots }) {
    return () => {
      const value = resolveMaterial({
        background: props.background,
        color: props.color,
        material: props.material,
      })
      if (typeof props.render === 'function') {
        const rendered = props.render(value)
        return rendered ?? null
      }
      const materialClass = cx(materialPrefixCls, materialModule.material, attrs.class as string)
      const materialStyle: Record<string, string> = {
        ...value.style,
        ...((attrs.style ?? {}) as Record<string, string>),
      }
      if (props.background) materialStyle['--rk-material-background'] = value.background
      if (props.color) materialStyle['--rk-material-color'] = value.color
      if (props.asChild) {
        const children = slots.default?.() ?? []
        const child = children.find((node): node is VNode => isVNode(node) && node.type !== Comment)
        if (!child) return null
        return cloneVNode(child, { class: materialClass, style: materialStyle })
      }
      return h(props.as ?? 'div', { ...attrs, class: materialClass, style: materialStyle }, slots.default?.())
    }
  },
})
