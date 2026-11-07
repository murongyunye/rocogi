import { defineComponent, h, Teleport, type PropType, type VNodeChild } from 'vue'
import RocoTheme from './RocoTheme.vue'
import RuneText from './RuneText'
import { IconCross } from './icons'
import { cx, modalModule, modalPrefixCls } from './rk'

/**
 * Simplified port of rocokingdom-ui Modal (Radix Dialog upstream → dependency-free Vue).
 * Verbatim classes; overlay click closes; enter animations via rk-modal-*-in keyframes.
 */
export default defineComponent({
  name: 'RkModal',
  inheritAttrs: false,
  props: {
    closable: { type: Boolean, default: true },
    closeLabel: { type: String, default: '关闭' },
    closePosition: { type: String as PropType<'inside' | 'outside' | 'floating'>, default: 'inside' },
    description: { type: String, default: undefined },
    headerRuneText: { type: Boolean, default: true },
    open: { type: Boolean, default: false },
    prefixCls: { type: String, default: modalPrefixCls },
    rootClassName: { type: String, default: undefined },
    title: { type: String, default: undefined },
    width: { type: [String, Number], default: undefined },
  },
  emits: ['update:open', 'openChange'],
  setup(props, { attrs, slots, emit }) {
    function close() {
      emit('update:open', false)
      emit('openChange', false)
    }

    function resolveWidth(width: string | number | undefined) {
      if (width === undefined) return undefined
      return typeof width === 'number' ? `${width}px` : width
    }

    function renderClose() {
      if (!props.closable) return null
      return h(
        'button',
        {
          'aria-label': props.closeLabel,
          class: cx(`${props.prefixCls}-close`, modalModule.close),
          onClick: close,
          type: 'button',
        },
        [h('span', { 'aria-hidden': true, class: cx(`${props.prefixCls}-close-icon`, modalModule.closeIcon) }, [h(IconCross)])],
      )
    }

    return (): VNodeChild | null => {
      if (!props.open) return null
      const { class: _class, ...rest } = attrs
      const hasVisibleHeader = !!slots.header || !!props.title
      return h(
        Teleport,
        { to: 'body' },
        () => [
          h(
            RocoTheme,
            () => [
              h('div', {
                'aria-hidden': true,
                class: cx(`${props.prefixCls}-overlay`, modalModule.overlay),
                'data-rk-modal-overlay': 'true',
                onClick: close,
              }),
              h(
                'div',
                {
                  ...rest,
                  'aria-modal': 'true',
                  class: cx(props.prefixCls, modalModule.content, props.rootClassName, attrs.class as string),
                  role: 'dialog',
                  style: props.width !== undefined ? { '--rk-modal-width': resolveWidth(props.width) } : undefined,
                },
                [
                  props.closePosition === 'outside' ? h('div', { class: cx(`${props.prefixCls}-outside-close`, modalModule.outsideClose) }, [renderClose()]) : null,
                  h('section', { class: cx(`${props.prefixCls}-panel`, modalModule.panel) }, [
                    hasVisibleHeader
                      ? h('header', { class: cx(`${props.prefixCls}-header`, modalModule.header) }, [
                          props.headerRuneText
                            ? h(RuneText, {
                                'aria-hidden': true,
                                class: cx(`${props.prefixCls}-header-rune-text`, modalModule.headerRuneText),
                                font: 'rune',
                              })
                            : null,
                          slots.header
                            ? slots.header()
                            : h(RuneText, { as: 'h2', class: cx(`${props.prefixCls}-title`, modalModule.title) }, () => props.title ?? ''),
                          props.closePosition === 'inside' ? renderClose() : null,
                        ])
                      : h('h2', { class: modalModule.visuallyHidden, id: 'rk-modal-title' }, props.title ?? ''),
                    !hasVisibleHeader && props.closePosition === 'floating'
                      ? h('div', { class: cx(`${props.prefixCls}-floating-close`, modalModule.floatingClose) }, [renderClose()])
                      : null,
                    h('div', { class: cx(`${props.prefixCls}-body`, modalModule.body) }, [
                      props.description ? h('p', { class: cx(`${props.prefixCls}-description`, modalModule.description) }, props.description) : null,
                      slots.default?.(),
                    ]),
                    slots.footer ? h('footer', { class: cx(`${props.prefixCls}-footer`, modalModule.footer) }, slots.footer()) : null,
                  ]),
                ],
              ),
            ],
          ),
        ],
      )
    }
  },
})
