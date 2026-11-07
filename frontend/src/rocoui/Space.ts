import { Comment, Fragment, defineComponent, h, isVNode, type PropType, type VNode, type VNodeChild } from 'vue'
import { cx, resolveGap, spaceModule, spacePrefixCls } from './rk'

const alignValueByName: Record<string, string> = {
  baseline: 'baseline',
  center: 'center',
  end: 'flex-end',
  start: 'flex-start',
  stretch: 'stretch',
}
const justifyValueByName: Record<string, string> = {
  around: 'space-around',
  between: 'space-between',
  center: 'center',
  end: 'flex-end',
  evenly: 'space-evenly',
  start: 'flex-start',
}

function flattenVNodes(nodes: VNodeChild): VNode[] {
  const out: VNode[] = []
  for (const node of Array.isArray(nodes) ? nodes : [nodes]) {
    if (!isVNode(node)) continue
    if (node.type === Comment) continue
    if (node.type === Fragment) {
      out.push(...flattenVNodes(node.children as VNodeChild))
      continue
    }
    out.push(node)
  }
  return out
}

/** Port of rocokingdom-ui Space (verbatim classes, gap vars always set). */
export default defineComponent({
  name: 'RkSpace',
  inheritAttrs: false,
  props: {
    align: { type: String as PropType<'start' | 'center' | 'end' | 'stretch' | 'baseline'>, default: undefined },
    as: { type: String, default: 'div' },
    block: { type: Boolean, default: false },
    direction: { type: String as PropType<'horizontal' | 'vertical'>, default: 'horizontal' },
    justify: { type: String as PropType<'start' | 'center' | 'end' | 'between' | 'around' | 'evenly'>, default: undefined },
    prefixCls: { type: String, default: spacePrefixCls },
    rootClassName: { type: String, default: undefined },
    size: { type: [String, Number, Array] as PropType<'compact' | 'small' | 'middle' | 'large' | number | string | [number | string, number | string]>, default: 'middle' },
    split: { type: null as unknown as PropType<VNodeChild | boolean>, default: undefined },
    wrap: { type: Boolean, default: false },
  },
  setup(props, { attrs, slots }) {
    return () => {
      const gap = resolveGap(props.size)
      const spaceStyle: Record<string, string> = {
        '--rk-space-column-gap': gap.columnGap,
        '--rk-space-row-gap': gap.rowGap,
        ...((attrs.style ?? {}) as Record<string, string>),
      }
      if (props.align) spaceStyle['--rk-space-align'] = alignValueByName[props.align]
      if (props.justify) spaceStyle['--rk-space-justify'] = justifyValueByName[props.justify]

      let items = flattenVNodes(slots.default?.() ?? [])
      if (props.split && items.length > 1) {
        const withSplits: VNode[] = []
        items.forEach((item, index) => {
          if (index > 0) {
            withSplits.push(
              h('span', { 'aria-hidden': 'true', class: spaceModule.split }, props.split === true ? null : props.split as VNodeChild),
            )
          }
          withSplits.push(item)
        })
        items = withSplits
      }

      const { class: _class, style: _style, ...rest } = attrs
      return h(
        props.as ?? 'div',
        {
          ...rest,
          'data-direction': props.direction,
          class: cx(
            props.prefixCls,
            spaceModule.space,
            spaceModule[props.direction],
            props.block && spaceModule.block,
            props.wrap && spaceModule.wrap,
            props.rootClassName,
            attrs.class as string,
          ),
          style: spaceStyle,
        },
        items,
      )
    }
  },
})
