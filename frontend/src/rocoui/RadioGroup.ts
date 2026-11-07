import { computed, defineComponent, h, provide, reactive, ref, watchEffect, type PropType } from 'vue'
import { RadioGroupContextKey, type RadioGroupContext } from './context'
import { cx, radioGroupModule, radioGroupPrefixCls, type MaterialName } from './rk'

function getRadioItems(root: HTMLElement): HTMLButtonElement[] {
  return Array.from(root.querySelectorAll<HTMLButtonElement>('[data-rk-radio-item="true"]')).filter(
    (item) => !item.disabled && item.getAttribute('aria-disabled') !== 'true',
  )
}

/** Port of rocokingdom-ui RadioGroup (verbatim classes + hidden input + keyboard roving). */
export default defineComponent({
  name: 'RkRadioGroup',
  inheritAttrs: false,
  props: {
    activeMaterial: { type: String as PropType<MaterialName>, default: 'paper' },
    activeShadow: { type: Boolean, default: false },
    activeVariant: { type: String as PropType<'solid' | 'outline' | 'text'>, default: 'solid' },
    defaultValue: { type: [String, Number], default: undefined },
    disabled: { type: Boolean, default: false },
    inactiveMaterial: { type: String as PropType<MaterialName>, default: 'stone' },
    inactiveShadow: { type: Boolean, default: false },
    inactiveVariant: { type: String as PropType<'solid' | 'outline' | 'text'>, default: 'solid' },
    name: { type: String, default: undefined },
    orientation: { type: String as PropType<'horizontal' | 'vertical'>, default: 'vertical' },
    prefixCls: { type: String, default: radioGroupPrefixCls },
    rootClassName: { type: String, default: undefined },
    size: { type: String as PropType<'small' | 'middle' | 'large'>, default: 'middle' },
    value: { type: [String, Number], default: undefined },
  },
  emits: ['update:value', 'valueChange'],
  setup(props, { attrs, slots, emit }) {
    const uncontrolledValue = ref<string | number | undefined>(props.defaultValue)
    const selectedValue = computed(() => props.value ?? uncontrolledValue.value)

    function selectValue(nextValue: string | number) {
      if (nextValue === selectedValue.value) return
      if (props.value === undefined) uncontrolledValue.value = nextValue
      emit('update:value', nextValue)
      emit('valueChange', nextValue)
    }

    const context = reactive<RadioGroupContext>({
      activeMaterial: props.activeMaterial,
      activeShadow: props.activeShadow,
      activeVariant: props.activeVariant,
      disabled: props.disabled,
      inactiveMaterial: props.inactiveMaterial,
      inactiveShadow: props.inactiveShadow,
      inactiveVariant: props.inactiveVariant,
      onValueChange: selectValue,
      selectedValue: props.value ?? props.defaultValue,
      size: props.size,
    })
    watchEffect(() => {
      context.activeMaterial = props.activeMaterial
      context.activeShadow = props.activeShadow
      context.activeVariant = props.activeVariant
      context.disabled = props.disabled
      context.inactiveMaterial = props.inactiveMaterial
      context.inactiveShadow = props.inactiveShadow
      context.inactiveVariant = props.inactiveVariant
      context.selectedValue = selectedValue.value
      context.size = props.size
    })
    provide(RadioGroupContextKey, context)

    function handleKeyDown(event: KeyboardEvent) {
      const onKeyDown = attrs.onKeydown as ((event: KeyboardEvent) => void) | undefined
      onKeyDown?.(event)
      if (event.defaultPrevented) return
      const isPreviousKey = event.key === 'ArrowUp' || event.key === 'ArrowLeft'
      const isNextKey = event.key === 'ArrowDown' || event.key === 'ArrowRight'
      const isBoundaryKey = event.key === 'Home' || event.key === 'End'
      if (!isPreviousKey && !isNextKey && !isBoundaryKey) return
      const currentTarget = event.currentTarget as HTMLElement
      const items = getRadioItems(currentTarget)
      if (items.length === 0) return
      const selectedIndex = items.findIndex((item) => item.getAttribute('aria-checked') === 'true')
      const currentIndex = selectedIndex >= 0 ? selectedIndex : 0
      let nextIndex = 0
      if (event.key === 'End') nextIndex = items.length - 1
      else if (isPreviousKey) nextIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1
      else if (isNextKey) nextIndex = currentIndex >= items.length - 1 ? 0 : currentIndex + 1
      event.preventDefault()
      const nextItem = items[nextIndex]
      context.onValueChange?.(nextItem.value)
      nextItem.focus()
    }

    return () => {
      const { class: _class, onKeydown: _onKeydown, ...rest } = attrs
      const children: ReturnType<typeof h>[] = []
      if (props.name && selectedValue.value !== undefined && selectedValue.value !== null) {
        children.push(
          h('input', {
            type: 'hidden',
            name: props.name,
            value: selectedValue.value,
            disabled: props.disabled,
          }),
        )
      }
      const slotted = slots.default?.()
      if (slotted) children.push(...slotted)
      return h(
        'div',
        {
          ...rest,
          'aria-orientation': props.orientation,
          class: cx(
            props.prefixCls,
            radioGroupModule.group,
            radioGroupModule[props.orientation],
            props.rootClassName,
            attrs.class as string,
          ),
          onKeydown: handleKeyDown,
          role: 'radiogroup',
        },
        children,
      )
    }
  },
})
