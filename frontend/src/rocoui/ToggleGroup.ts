import { computed, defineComponent, h, provide, reactive, ref, watchEffect, type PropType } from 'vue'
import { ToggleGroupContextKey, type ToggleGroupContext } from './context'
import { cx, toggleGroupModule, toggleGroupPrefixCls, type MaterialName } from './rk'

function getToggleItems(root: HTMLElement): HTMLButtonElement[] {
  return Array.from(root.querySelectorAll<HTMLButtonElement>('[data-rk-toggle-item="true"]')).filter(
    (item) => !item.disabled && item.getAttribute('aria-disabled') !== 'true',
  )
}

/** Port of rocokingdom-ui ToggleGroup (verbatim classes, multi-select). */
export default defineComponent({
  name: 'RkToggleGroup',
  inheritAttrs: false,
  props: {
    defaultValue: { type: Array as PropType<Array<string | number>>, default: undefined },
    disabled: { type: Boolean, default: false },
    name: { type: String, default: undefined },
    orientation: { type: String as PropType<'horizontal' | 'vertical'>, default: 'vertical' },
    prefixCls: { type: String, default: toggleGroupPrefixCls },
    rootClassName: { type: String, default: undefined },
    selectedMaterial: { type: String as PropType<MaterialName>, default: 'paper' },
    selectedShadow: { type: Boolean, default: false },
    selectedVariant: { type: String as PropType<'solid' | 'outline' | 'text'>, default: 'solid' },
    size: { type: String as PropType<'small' | 'middle' | 'large'>, default: 'middle' },
    unselectedMaterial: { type: String as PropType<MaterialName>, default: 'stone' },
    unselectedShadow: { type: Boolean, default: false },
    unselectedVariant: { type: String as PropType<'solid' | 'outline' | 'text'>, default: 'solid' },
    value: { type: Array as PropType<Array<string | number>>, default: undefined },
  },
  emits: ['update:value', 'valueChange'],
  setup(props, { attrs, slots, emit }) {
    const uncontrolledValue = ref<Array<string | number> | undefined>(props.defaultValue)
    const selectedValues = computed(() => props.value ?? uncontrolledValue.value)

    function toggleValue(value: string | number) {
      const previous = selectedValues.value ?? []
      const next = previous.includes(value) ? previous.filter((item) => item !== value) : [...previous, value]
      if (props.value === undefined) uncontrolledValue.value = next
      emit('update:value', next)
      emit('valueChange', next)
    }

    const context = reactive<ToggleGroupContext>({
      disabled: props.disabled,
      selectedMaterial: props.selectedMaterial,
      selectedShadow: props.selectedShadow,
      selectedVariant: props.selectedVariant,
      selectedValues: props.value ?? props.defaultValue,
      size: props.size,
      toggleValue,
      unselectedMaterial: props.unselectedMaterial,
      unselectedShadow: props.unselectedShadow,
      unselectedVariant: props.unselectedVariant,
    })
    watchEffect(() => {
      context.disabled = props.disabled
      context.selectedMaterial = props.selectedMaterial
      context.selectedShadow = props.selectedShadow
      context.selectedVariant = props.selectedVariant
      context.selectedValues = selectedValues.value
      context.size = props.size
      context.unselectedMaterial = props.unselectedMaterial
      context.unselectedShadow = props.unselectedShadow
      context.unselectedVariant = props.unselectedVariant
    })
    provide(ToggleGroupContextKey, context)

    function handleKeyDown(event: KeyboardEvent) {
      const onKeyDown = attrs.onKeydown as ((event: KeyboardEvent) => void) | undefined
      onKeyDown?.(event)
      if (event.defaultPrevented) return
      const isPreviousKey = event.key === 'ArrowUp' || event.key === 'ArrowLeft'
      const isNextKey = event.key === 'ArrowDown' || event.key === 'ArrowRight'
      const isBoundaryKey = event.key === 'Home' || event.key === 'End'
      if (!isPreviousKey && !isNextKey && !isBoundaryKey) return
      const currentTarget = event.currentTarget as HTMLElement
      const items = getToggleItems(currentTarget)
      if (items.length === 0) return
      const focusedIndex = event.target instanceof HTMLButtonElement ? items.indexOf(event.target) : -1
      const currentIndex = focusedIndex >= 0 ? focusedIndex : 0
      let nextIndex = 0
      if (event.key === 'End') nextIndex = items.length - 1
      else if (isPreviousKey) nextIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1
      else if (isNextKey) nextIndex = currentIndex >= items.length - 1 ? 0 : currentIndex + 1
      event.preventDefault()
      items[nextIndex].focus()
    }

    return () => {
      const { class: _class, onKeydown: _onKeydown, ...rest } = attrs
      const children: ReturnType<typeof h>[] = []
      if (props.name && (selectedValues.value?.length ?? 0) > 0) {
        for (const value of selectedValues.value ?? []) {
          children.push(h('input', { type: 'hidden', name: props.name, value, disabled: props.disabled }))
        }
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
            toggleGroupModule.group,
            toggleGroupModule[props.orientation],
            props.rootClassName,
            attrs.class as string,
          ),
          onKeydown: handleKeyDown,
          role: 'group',
        },
        children,
      )
    }
  },
})
