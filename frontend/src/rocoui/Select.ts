import {
  computed,
  defineComponent,
  h,
  onBeforeUnmount,
  onMounted,
  provide,
  reactive,
  ref,
  Teleport,
  watch,
  watchEffect,
  type PropType,
  type VNode,
  type VNodeChild,
} from 'vue'
import Material from './Material'
import RocoShape from './RocoShape.vue'
import RocoTheme from './RocoTheme.vue'
import { IconCheck } from './icons'
import { SelectRootContextKey, type SelectRootContext } from './context'
import { cx, selectModule, selectPrefixCls, type MaterialName } from './rk'

/**
 * Simplified port of rocokingdom-ui Select (Radix upstream → dependency-free Vue).
 * Verbatim classes for trigger/content/item; keyboard navigation + outside close added.
 */
export default defineComponent({
  name: 'RkSelect',
  inheritAttrs: false,
  props: {
    disabled: { type: Boolean, default: false },
    material: { type: String as PropType<MaterialName>, default: 'stone' },
    modelValue: { type: [String, Number], default: undefined },
    options: { type: Array as PropType<Array<{ value: string | number; label: string; disabled?: boolean }>>, default: undefined },
    placeholder: { type: String, default: undefined },
    prefixCls: { type: String, default: selectPrefixCls },
    rootClassName: { type: String, default: undefined },
    shadow: { type: Boolean, default: true },
    size: { type: String as PropType<'small' | 'middle' | 'large'>, default: 'middle' },
    variant: { type: String as PropType<'solid' | 'outline'>, default: 'solid' },
  },
  emits: ['update:modelValue', 'change'],
  setup(props, { attrs, slots, emit }) {
    const open = ref(false)
    const triggerRef = ref<HTMLElement | null>(null)
    const contentRef = ref<HTMLElement | null>(null)
    const activeIndex = ref(-1)

    const context = reactive<SelectRootContext>({
      disabled: props.disabled,
      open: open.value,
      value: props.modelValue,
    })
    watchEffect(() => {
      context.disabled = props.disabled
      context.open = open.value
      context.value = props.modelValue
    })
    provide(SelectRootContextKey, context)

    const items = computed(() => {
      if (props.options) return props.options
      return []
    })

    const selectedLabel = computed(() => {
      const value = props.modelValue
      if (value === undefined || value === null) return undefined
      const item = items.value.find((entry) => entry.value === value)
      return item?.label ?? String(value)
    })

    watch(open, (next) => {
      if (next) activeIndex.value = items.value.findIndex((entry) => entry.value === props.modelValue)
    })

    function setOpen(next: boolean) {
      if (props.disabled) {
        open.value = false
        return
      }
      open.value = next
    }

    function commitValue(value: string | number) {
      if (props.modelValue === undefined) {
        // uncontrolled only updates local view state through model-free flow
      }
      emit('update:modelValue', value)
      emit('change', value)
      open.value = false
      triggerRef.value?.focus()
    }

    function onDocumentPointerDown(event: PointerEvent) {
      if (!open.value) return
      const target = event.target as Node
      if (triggerRef.value?.contains(target)) return
      if (contentRef.value?.contains(target)) return
      open.value = false
    }
    onMounted(() => document.addEventListener('pointerdown', onDocumentPointerDown, true))
    onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocumentPointerDown, true))

    function onTriggerKeydown(event: KeyboardEvent) {
      const onKeyDown = attrs.onKeydown as ((event: KeyboardEvent) => void) | undefined
      onKeyDown?.(event)
      if (event.defaultPrevented) return
      if (event.key === 'Escape') {
        if (open.value) event.stopPropagation()
        open.value = false
        return
      }
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        if (open.value && activeIndex.value >= 0) {
          const item = items.value[activeIndex.value]
          if (item && !item.disabled) commitValue(item.value)
          else open.value = false
        } else {
          setOpen(!open.value)
        }
        return
      }
      if (!open.value && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
        event.preventDefault()
        setOpen(true)
        return
      }
      if (open.value && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
        event.preventDefault()
        if (items.value.length === 0) return
        const delta = event.key === 'ArrowDown' ? 1 : -1
        let next = activeIndex.value
        for (let step = 0; step < items.value.length; step += 1) {
          next = (next + delta + items.value.length) % items.value.length
          if (!items.value[next].disabled) break
        }
        activeIndex.value = next
      }
    }

    return (): VNodeChild => {
      const { class: _class, onKeydown: _onKeydown, ...rest } = attrs
      const triggerChildren: VNode[] = [
        h(
          'span',
          { class: cx(`${props.prefixCls}-value`, selectModule.value) },
          slots.value
            ? slots.value({ value: props.modelValue, label: selectedLabel.value })
            : (selectedLabel.value ?? props.placeholder ?? ''),
        ),
        h('span', { class: cx(`${props.prefixCls}-trigger-icon`, selectModule.triggerIcon), 'aria-hidden': true }, '▾'),
      ]
      const trigger = h(
        Material,
        { asChild: true, material: props.material },
        () => [
          h(
            RocoShape,
            {
              ...rest,
              ref: triggerRef,
              'aria-disabled': props.disabled || undefined,
              'aria-expanded': open.value,
              'aria-haspopup': 'listbox',
              as: 'button',
              class: cx(props.prefixCls, selectModule.trigger, props.rootClassName, attrs.class as string),
              'content-class-name': selectModule.triggerContent,
              onClick: () => setOpen(!open.value),
              onKeydown: onTriggerKeydown,
              role: 'combobox',
              shadow: props.shadow,
              size: props.size,
              variant: props.variant,
            },
            () => triggerChildren,
          ),
        ],
      )

      const itemList =
        slots.default?.() ??
        items.value.map((item) =>
          h(
            'button',
            {
              'aria-disabled': item.disabled || undefined,
              'aria-selected': item.value === props.modelValue,
              class: cx(`${props.prefixCls}-item`, selectModule.item, item.disabled && 'disabled'),
              'data-rk-select-item': 'true',
              disabled: item.disabled,
              key: String(item.value),
              onMouseenter: () => {
                if (!item.disabled) activeIndex.value = items.value.indexOf(item)
              },
              onMouseleave: () => {
                if (!item.disabled && activeIndex.value === items.value.indexOf(item)) activeIndex.value = -1
              },
              role: 'option',
              type: 'button',
            },
            [
              h(
                'span',
                { class: cx(`${props.prefixCls}-item-label`) },
                item.label,
              ),
              item.value === props.modelValue
                ? h('span', { class: cx(`${props.prefixCls}-item-indicator`, selectModule.itemIndicator) }, [
                    h('span', { class: selectModule.itemCheck }, [h(IconCheck)]),
                  ])
                : null,
            ],
          ),
        )

      const content = open.value
        ? h(
            Teleport,
            { to: 'body' },
            () => [
              h(
                RocoTheme,
                () => [
                  h(
                    'div',
                    {
                      class: cx(`${props.prefixCls}-content`, selectModule.content),
                      'data-rk-select-content': 'true',
                      'data-state': 'open',
                      ref: contentRef,
                      role: 'listbox',
                    },
                    [
                      h('div', { class: selectModule.contentShell }, [
                        h('div', { class: selectModule.viewport }, itemList),
                      ]),
                    ],
                  ),
                ],
              ),
            ],
          )
        : null

      return [trigger, content]
    }
  },
})
