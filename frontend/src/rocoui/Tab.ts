import { computed, defineComponent, h, inject, useAttrs, type PropType } from 'vue'
import Material from './Material'
import RocoShape from './RocoShape.vue'
import RuneText from './RuneText'
import { TabsContextKey } from './context'
import { cx, tabsModule, tabPrefixCls, type MaterialName } from './rk'

/** Port of rocokingdom-ui Tab (verbatim classes/material resolution). */
export default defineComponent({
  name: 'RkTab',
  inheritAttrs: false,
  props: {
    disabled: { type: Boolean, default: false },
    material: { type: String as PropType<MaterialName>, default: undefined },
    prefixCls: { type: String, default: tabPrefixCls },
    rootClassName: { type: String, default: undefined },
    selectedClassName: { type: String, default: undefined },
    selectedMaterial: { type: String as PropType<MaterialName>, default: undefined },
    size: { type: String as PropType<'small' | 'middle' | 'large'>, default: undefined },
    unselectedClassName: { type: String, default: undefined },
    unselectedMaterial: { type: String as PropType<MaterialName>, default: undefined },
    value: { type: [String, Number], required: true },
  },
  emits: ['click'],
  setup(props, { attrs, slots, emit }) {
    const tabs = inject(TabsContextKey)
    if (!tabs) throw new Error('Tab must be rendered inside Tabs.')

    const isDisabled = computed(() => !!tabs.disabled || props.disabled)
    const isSelected = computed(() => tabs.selectedValue === props.value)
    const isTabbable = computed(() => !isDisabled.value && (isSelected.value || tabs.selectedValue === undefined))

    const resolvedMaterial = computed<MaterialName>(() => {
      const explicit = isSelected.value ? props.selectedMaterial : props.unselectedMaterial
      if (explicit) return explicit
      if (props.material) return props.material
      return isSelected.value
        ? (tabs.selectedMaterial ?? 'default')
        : (tabs.unselectedMaterial ?? tabs.listMaterial ?? 'stoneSoft')
    })
    const resolvedSize = computed(() => props.size ?? tabs.size ?? 'middle')

    const resolvedClassName = computed(() =>
      cx(
        props.prefixCls,
        tabsModule.tab,
        tabsModule[resolvedSize.value],
        isSelected.value ? tabsModule.selected : tabsModule.unselected,
        props.rootClassName,
        attrs.class as string,
        isSelected.value ? props.selectedClassName : props.unselectedClassName,
      ),
    )

    function handleClick(event: MouseEvent) {
      emit('click', event)
      if (event.defaultPrevented || isDisabled.value) return
      tabs.onValueChange?.(props.value)
    }

    return () => {
      const { class: _class, onClick: _onClick, ...rest } = attrs
      return h(Material, { asChild: true, material: resolvedMaterial.value }, () => [
        h(
          RocoShape,
          {
            ...rest,
            'aria-controls': tabs.getPanelId?.(props.value),
            'aria-disabled': isDisabled.value || undefined,
            'aria-selected': isSelected.value,
            as: 'button',
            class: resolvedClassName.value,
            'content-class-name': tabsModule.tabContent,
            'data-rk-tab': 'true',
            'data-state': isSelected.value ? 'active' : 'inactive',
            disabled: isDisabled.value,
            id: tabs.getTabId?.(props.value),
            onClick: handleClick,
            role: 'tab',
            tabindex: isTabbable.value ? 0 : -1,
            type: 'button',
            value: props.value,
            variant: isSelected.value ? 'solid' : 'text',
            color: isSelected.value ? undefined : 'var(--rk-material-color)',
          },
          () => [h(RuneText, { class: tabsModule.tabText }, slots.default)],
        ),
      ])
    }
  },
})
