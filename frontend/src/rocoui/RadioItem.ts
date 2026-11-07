import { computed, defineComponent, h, inject, useAttrs, type PropType } from 'vue'
import Material from './Material'
import RocoShape from './RocoShape.vue'
import { RadioGroupContextKey } from './context'
import { cx, radioGroupModule, radioItemPrefixCls, type MaterialName } from './rk'

/** Port of rocokingdom-ui RadioItem (verbatim classes/material resolution). */
export default defineComponent({
  name: 'RkRadioItem',
  inheritAttrs: false,
  props: {
    activeMaterial: { type: String as PropType<MaterialName>, default: undefined },
    activeShadow: { type: Boolean, default: undefined },
    activeVariant: { type: String as PropType<'solid' | 'outline' | 'text'>, default: undefined },
    disabled: { type: Boolean, default: false },
    inactiveMaterial: { type: String as PropType<MaterialName>, default: undefined },
    inactiveShadow: { type: Boolean, default: undefined },
    inactiveVariant: { type: String as PropType<'solid' | 'outline' | 'text'>, default: undefined },
    material: { type: String as PropType<MaterialName>, default: undefined },
    prefixCls: { type: String, default: radioItemPrefixCls },
    rootClassName: { type: String, default: undefined },
    shadow: { type: Boolean, default: false },
    size: { type: String as PropType<'small' | 'middle' | 'large'>, default: undefined },
    value: { type: [String, Number], required: true },
    variant: { type: String as PropType<'solid' | 'outline' | 'text'>, default: undefined },
  },
  emits: ['click'],
  setup(props, { attrs, slots, emit }) {
    const group = inject(RadioGroupContextKey)
    if (!group) throw new Error('RadioItem must be rendered inside RadioGroup.')

    const isDisabled = computed(() => !!group.disabled || props.disabled)
    const isChecked = computed(() => group.selectedValue === props.value)

    const resolvedMaterial = computed<MaterialName>(() => {
      const explicit = isChecked.value ? props.activeMaterial : props.inactiveMaterial
      if (explicit) return explicit
      if (props.material) return props.material
      return isChecked.value
        ? (group.activeMaterial ?? 'paper')
        : (group.inactiveMaterial ?? 'stone')
    })
    const resolvedVariant = computed(() => {
      const explicit = isChecked.value ? props.activeVariant : props.inactiveVariant
      return explicit ?? props.variant ?? (isChecked.value ? group.activeVariant : group.inactiveVariant) ?? 'solid'
    })
    const resolvedShadow = computed(() => {
      if (resolvedVariant.value === 'text') return false
      const explicit = isChecked.value ? props.activeShadow : props.inactiveShadow
      if (explicit !== undefined) return explicit
      return isChecked.value ? (group.activeShadow ?? false) : (group.inactiveShadow ?? props.shadow)
    })
    const resolvedSize = computed(() => props.size ?? group.size ?? 'middle')

    const resolvedClassName = computed(() =>
      cx(
        props.prefixCls,
        radioGroupModule.item,
        radioGroupModule[resolvedSize.value],
        radioGroupModule[resolvedVariant.value],
        isChecked.value ? radioGroupModule.active : radioGroupModule.inactive,
        props.rootClassName,
        attrs.class as string,
      ),
    )

    function handleClick(event: MouseEvent) {
      emit('click', event)
      if (event.defaultPrevented || isDisabled.value) return
      group.onValueChange?.(props.value)
    }

    return () => {
      const { class: _class, onClick: _onClick, ...rest } = attrs
      return h(Material, { asChild: true, material: resolvedMaterial.value }, () => [
        h(
          RocoShape,
          {
            ...rest,
            'aria-checked': isChecked.value,
            'aria-disabled': isDisabled.value || undefined,
            as: 'button',
            class: resolvedClassName.value,
            'content-class-name': radioGroupModule.itemContent,
            'data-rk-radio-item': 'true',
            'data-state': isChecked.value ? 'checked' : 'unchecked',
            disabled: isDisabled.value,
            onClick: handleClick,
            role: 'radio',
            shadow: resolvedShadow.value,
            tabindex: isChecked.value ? 0 : group.selectedValue == null ? 0 : -1,
            type: 'button',
            value: props.value,
            variant: resolvedVariant.value,
          },
          slots.default,
        ),
      ])
    }
  },
})
