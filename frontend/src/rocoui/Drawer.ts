import { defineComponent, h, Teleport, type PropType, type VNodeChild } from 'vue'
import RocoTheme from './RocoTheme.vue'
import Panel from './Panel.vue'
import RuneText from './RuneText'
import { IconCross } from './icons'
import { cx, drawerModule, drawerPrefixCls } from './rk'

function getDefaultCurve(side: 'bottom' | 'left' | 'right' | 'top'): 'bottom' | 'left' | 'right' | 'top' {
  if (side === 'right') return 'left'
  if (side === 'left') return 'right'
  if (side === 'top') return 'bottom'
  return 'top'
}

function resolveDrawerSize(
  size: 'full' | number,
  curve: boolean,
  side: 'bottom' | 'left' | 'right' | 'top',
): Record<string, string> {
  const viewport = side === 'left' || side === 'right' ? '100vw' : '100svh'
  const trimmed = side === 'left' || side === 'right' ? '12vw' : '12svh'
  if (size === 'full') {
    return { '--rk-drawer-size': curve ? `calc(${viewport} - ${trimmed})` : viewport }
  }
  const value = `${size}px`
  const extension = `${Math.round((size * 120) / 880)}px`
  return { '--rk-drawer-size': value, '--rk-drawer-curve-extension': extension }
}

/**
 * Simplified port of rocokingdom-ui Drawer (Radix Dialog upstream → dependency-free Vue).
 * Verbatim classes; Panel with default opposite-side curve; overlay optional.
 */
export default defineComponent({
  name: 'RkDrawer',
  inheritAttrs: false,
  props: {
    closable: { type: Boolean, default: true },
    closeLabel: { type: String, default: '关闭' },
    curve: { type: String as PropType<'bottom' | 'left' | 'right' | 'top'>, default: undefined },
    description: { type: String, default: undefined },
    material: { type: String as PropType<string>, default: 'stone' },
    open: { type: Boolean, default: false },
    overlay: { type: Boolean, default: true },
    panelMaterial: { type: String as PropType<string>, default: undefined },
    prefixCls: { type: String, default: drawerPrefixCls },
    rootClassName: { type: String, default: undefined },
    side: { type: String as PropType<'bottom' | 'left' | 'right' | 'top'>, default: 'right' },
    size: { type: [String, Number] as PropType<'full' | number>, default: 'full' },
    title: { type: String, default: undefined },
  },
  emits: ['update:open', 'openChange'],
  setup(props, { attrs, slots, emit }) {
    function close() {
      emit('update:open', false)
      emit('openChange', false)
    }

    return (): VNodeChild | null => {
      if (!props.open) return null
      const { class: _class, ...rest } = attrs
      const curve = props.curve ?? getDefaultCurve(props.side)
      const isCurved = curve !== 'none'
      const style = resolveDrawerSize(props.size as 'full' | number, isCurved, props.side)
      const resolvedPanelMaterial = (props.panelMaterial ?? props.material) as never
      return h(
        Teleport,
        { to: 'body' },
        () => [
          h(
            RocoTheme,
            () => [
              props.overlay
                ? h('div', {
                    'aria-hidden': true,
                    class: cx(`${props.prefixCls}-overlay`, drawerModule.overlay, drawerModule.overlayVisible),
                    'data-rk-drawer-overlay': 'true',
                    onClick: close,
                  })
                : null,
              h(
                'div',
                {
                  ...rest,
                  'aria-modal': 'true',
                  class: cx(
                    props.prefixCls,
                    drawerModule.content,
                    drawerModule[props.side],
                    props.rootClassName,
                    attrs.class as string,
                  ),
                  role: 'dialog',
                  style,
                },
                [
                  h(
                    Panel,
                    {
                      'content-class-name': cx(`${props.prefixCls}-panel-content`, drawerModule.panelContent),
                      curve: curve as never,
                      material: resolvedPanelMaterial,
                    },
                    {
                      default: () => [
                        h('div', { class: cx(`${props.prefixCls}-inner`, drawerModule.inner) }, [
                          h('header', { class: cx(`${props.prefixCls}-header`, drawerModule.header) }, [
                            h('div', { class: cx(`${props.prefixCls}-header-content`, drawerModule.headerContent) }, [
                              slots.title
                                ? slots.title()
                                : props.title
                                  ? h(RuneText, { as: 'h2', class: cx(`${props.prefixCls}-title`, drawerModule.title) }, () => props.title ?? '')
                                  : h('h2', { class: drawerModule.visuallyHidden }, props.title ?? 'Drawer'),
                              props.description
                                ? h('p', { class: cx(`${props.prefixCls}-description`, drawerModule.description) }, props.description)
                                : null,
                              props.closable
                                ? h(
                                    'button',
                                    {
                                      'aria-label': props.closeLabel,
                                      class: cx(`${props.prefixCls}-close`, drawerModule.close),
                                      onClick: close,
                                      type: 'button',
                                    },
                                    [
                                      h('span', { 'aria-hidden': true, class: cx(`${props.prefixCls}-close-icon`, drawerModule.closeIcon) }, [
                                        h(IconCross),
                                      ]),
                                    ],
                                  )
                                : null,
                            ]),
                          ]),
                          h('div', { class: cx(`${props.prefixCls}-content`, drawerModule.body) }, slots.default?.()),
                        ]),
                      ],
                    },
                  ),
                ],
              ),
            ],
          ),
        ],
      )
    }
  },
})
