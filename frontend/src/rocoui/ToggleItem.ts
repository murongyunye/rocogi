import { computed, defineComponent, h, inject, useAttrs, type PropType } from 'vue'
import Material from './Material'
import RocoShape from './RocoShape.vue'
import RuneText from './RuneText'
import { ToggleGroupContextKey } from './context'
import { cx, toggleGroupModule, toggleItemPrefixCls, type MaterialName } from './rk'

/** Port of rocokingdom-ui ToggleItem (verbatim classes; text state via RuneText). */
export default defineComponent({
  name: 'RkToggleItem',
  inheritAttrs: false,
  props: {
    disabled: { type: Boolean, default: false },
    material: { type: String as PropType<MaterialName>, default: undefined },
    prefixCls: { type: String, default: toggleItemPrefixCls },
    rootClassName: { type: String, default: undefined },
    selectedMaterial: { type: String as PropType<MaterialName>, default: undefined },
    selectedShadow: { type: Boolean, default: undefined },
    selectedVariant: { type: String as PropType<'solid' | 'outline' | 'text'>, default: undefined },
    shadow: { type: Boolean, default: false },
    size: { type: String as PropType<'small' | 'middle' | 'large'>, default: undefined },
    unselectedMaterial: { type: String as PropType<MaterialName>, default: undefined },
    unselectedShadow: { type: Boolean, default: undefined },
    unselectedVariant: { type: String as PropType<'solid' | 'outline' | 'text'>, default: undefined },
    value: { type: [String, Number], required: true },
    variant: { type: String as PropType<'solid' | 'outline' | 'text'>, default: undefined },
  },
  emits: ['click'],
  setup(props, { attrs, slots, emit }) {
    const group = inject(ToggleGroupContextKey)
    if (!group) throw new Error('ToggleItem must be rendered inside ToggleGroup.')

    const isDisabled = computed(() => !!group.disabled || props.disabled)
    const isSelected = computed(() => (group.selectedValues ?? []).includes(props.value))

    const resolvedMaterial = computed<MaterialName>(() => {
      const explicit = isSelected.value ? props.selectedMaterial : props.unselectedMaterial
      if (explicit) return explicit
      if (props.material) return props.material
      return isSelected.value ? (group.selectedMaterial ?? 'paper') : (group.unselectedMaterial ?? 'stone')
    })
    const resolvedVariant = computed(() => {
      const explicit = isSelected.value ? props.selectedVariant : props.unselectedVariant
      return explicit ?? props.variant ?? (isSelected.value ? group.selectedVariant : group.unselectedVariant) ?? 'solid'
    })
    const resolvedShadow = computed(() => {
      if (resolvedVariant.value === 'text') return false
      const explicit = isSelected.value ? props.selectedShadow : props.unselectedShadow
      if (explicit !== undefined) return explicit
      return isSelected.value ? (group.selectedShadow ?? false) : (group.unselectedShadow ?? props.shadow)
    })
    const resolvedSize = computed(() => props.size ?? group.size ?? 'middle')

    const resolvedClassName = computed(() =>
      cx(
        props.prefixCls,
        toggleGroupModule.item,
        toggleGroupModule[resolvedSize.value],
        isSelected.value ? toggleGroupModule.selected : toggleGroupModule.unselected,
        props.rootClassName,
        attrs.class as string,
      ),
    )

    function handleClick(event: MouseEvent) {
      emit('click', event)
      if (event.defaultPrevented || isDisabled.value) return
      group.toggleValue?.(props.value)
    }

    return () => {
      const { class: _class, onClick: _onClick, ...rest } = attrs
      return h(Material, { asChild: true, material: resolvedMaterial.value }, () => [
        h(
          RocoShape,
          {
            ...rest,
            'aria-disabled': isDisabled.value || undefined,
            'aria-pressed': isSelected.value,
            as: 'button',
            class: resolvedClassName.value,
            'content-class-name': toggleGroupModule.itemContent,
            'data-rk-toggle-item': 'true',
            'data-state': isSelected.value ? 'selected' : 'unselected',
            disabled: isDisabled.value,
            onClick: handleClick,
            shadow: resolvedShadow.value,
            type: 'button',
            value: props.value,
            variant: resolvedVariant.value,
          },
          () => [h(RuneText, { class: toggleGroupModule.itemText }, slots.default)],
        ),
      ])
    }
  },
})
