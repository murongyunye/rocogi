import { computed, defineComponent, h, inject, useAttrs, type PropType, type VNodeChild } from 'vue'
import { TabsContextKey } from './context'
import { cx, tabsModule, tabPanelPrefixCls } from './rk'

/** Port of rocokingdom-ui TabPanel (verbatim classes, forceMount default true). */
export default defineComponent({
  name: 'RkTabPanel',
  inheritAttrs: false,
  props: {
    forceMount: { type: Boolean, default: true },
    prefixCls: { type: String, default: tabPanelPrefixCls },
    rootClassName: { type: String, default: undefined },
    value: { type: [String, Number], required: true },
  },
  setup(props, { attrs, slots }) {
    const tabs = inject(TabsContextKey)
    if (!tabs) throw new Error('TabPanel must be rendered inside Tabs.')

    const isSelected = computed(() => tabs.selectedValue === props.value)

    return (): VNodeChild | null => {
      if (!props.forceMount && !isSelected.value) return null
      const { class: _class, ...rest } = attrs
      return h(
        'div',
        {
          ...rest,
          'aria-labelledby': tabs.getTabId?.(props.value),
          class: cx(
            props.prefixCls,
            tabsModule.panel,
            isSelected.value ? tabsModule.panelActive : tabsModule.panelInactive,
            props.rootClassName,
            attrs.class as string,
          ),
          'data-state': isSelected.value ? 'active' : 'inactive',
          hidden: !isSelected.value,
          id: tabs.getPanelId?.(props.value),
          role: 'tabpanel',
          tabindex: 0,
        },
        slots.default?.(),
      )
    }
  },
})
