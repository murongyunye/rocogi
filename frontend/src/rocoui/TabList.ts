import { defineComponent, h, inject, useAttrs, type PropType } from 'vue'
import Material from './Material'
import RocoShape from './RocoShape.vue'
import { TabsContextKey } from './context'
import { cx, tabsModule, tabListPrefixCls, type MaterialName } from './rk'

function getTabs(root: HTMLElement): HTMLButtonElement[] {
  return Array.from(root.querySelectorAll<HTMLButtonElement>('[data-rk-tab="true"]')).filter(
    (tab) => !tab.disabled && tab.getAttribute('aria-disabled') !== 'true',
  )
}

/** Port of rocokingdom-ui TabList (Material+RocoShape tablist with keyboard roving). */
export default defineComponent({
  name: 'RkTabList',
  inheritAttrs: false,
  props: {
    material: { type: String as PropType<MaterialName>, default: undefined },
    prefixCls: { type: String, default: tabListPrefixCls },
    rootClassName: { type: String, default: undefined },
  },
  setup(props, { attrs, slots }) {
    const tabs = inject(TabsContextKey)
    if (!tabs) throw new Error('TabList must be rendered inside Tabs.')

    const resolvedClassName = () => cx(props.prefixCls, tabsModule.list, props.rootClassName, attrs.class as string)

    function handleKeyDown(event: KeyboardEvent) {
      const onKeyDown = attrs.onKeydown as ((event: KeyboardEvent) => void) | undefined
      onKeyDown?.(event)
      if (event.defaultPrevented) return
      const isPreviousKey = event.key === 'ArrowLeft'
      const isNextKey = event.key === 'ArrowRight'
      const isBoundaryKey = event.key === 'Home' || event.key === 'End'
      if (!isPreviousKey && !isNextKey && !isBoundaryKey) return
      const currentTarget = event.currentTarget as HTMLElement
      const enabledTabs = getTabs(currentTarget)
      if (enabledTabs.length === 0) return
      const selectedIndex = enabledTabs.findIndex((tab) => tab.getAttribute('aria-selected') === 'true')
      const focusedIndex = event.target instanceof HTMLButtonElement ? enabledTabs.indexOf(event.target) : -1
      const currentIndex = selectedIndex >= 0 ? selectedIndex : focusedIndex
      let nextIndex = 0
      if (event.key === 'End') nextIndex = enabledTabs.length - 1
      else if (isPreviousKey) nextIndex = currentIndex <= 0 ? enabledTabs.length - 1 : currentIndex - 1
      else if (isNextKey) nextIndex = currentIndex >= enabledTabs.length - 1 ? 0 : currentIndex + 1
      event.preventDefault()
      const nextTab = enabledTabs[nextIndex]
      tabs.onValueChange?.(nextTab.value)
      nextTab.focus()
    }

    return () => {
      const { class: _class, style: _style, onKeydown: _onKeydown, ...rest } = attrs
      return h(Material, { asChild: true, material: props.material ?? tabs.listMaterial }, () => [
        h(
          RocoShape,
          {
            ...rest,
            'aria-disabled': tabs.disabled || undefined,
            as: 'div',
            class: resolvedClassName(),
            'content-class-name': tabsModule.listContent,
            role: 'tablist',
            variant: 'solid',
            onKeydown: handleKeyDown,
          },
          slots.default,
        ),
      ])
    }
  },
})
