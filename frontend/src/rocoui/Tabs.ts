import { computed, defineComponent, h, provide, reactive, ref, useAttrs, useId, watchEffect, type PropType } from 'vue'
import Material from './Material'
import RocoShape from './RocoShape.vue'
import { TabsContextKey, type TabsContext } from './context'
import { cx, tabsModule, tabsPrefixCls, type MaterialName } from './rk'

/** Port of rocokingdom-ui Tabs (verbatim classes + hidden input + keyboard roving). */
export default defineComponent({
  name: 'RkTabs',
  inheritAttrs: false,
  props: {
    defaultValue: { type: [String, Number], default: undefined },
    disabled: { type: Boolean, default: false },
    id: { type: String, default: undefined },
    listMaterial: { type: String as PropType<MaterialName>, default: 'stoneSoft' },
    name: { type: String, default: undefined },
    prefixCls: { type: String, default: tabsPrefixCls },
    rootClassName: { type: String, default: undefined },
    selectedMaterial: { type: String as PropType<MaterialName>, default: 'default' },
    size: { type: String as PropType<'small' | 'middle' | 'large'>, default: 'middle' },
    unselectedMaterial: { type: String as PropType<MaterialName>, default: undefined },
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

    const generatedId = useId()
    const tabsId = computed(() => props.id ?? `rk-tabs-${generatedId}`)
    function getTabId(valueId: string | number) {
      return `${tabsId.value}-tab-${String(valueId).trim().replace(/\s+/g, '-')}`
    }
    function getPanelId(valueId: string | number) {
      return `${tabsId.value}-panel-${String(valueId).trim().replace(/\s+/g, '-')}`
    }

    const context = reactive<TabsContext>({
      disabled: props.disabled,
      getTabId,
      getPanelId,
      onValueChange: selectValue,
      listMaterial: props.listMaterial,
      selectedMaterial: props.selectedMaterial,
      selectedValue: props.value ?? props.defaultValue,
      size: props.size,
      unselectedMaterial: props.unselectedMaterial,
    })
    watchEffect(() => {
      context.disabled = props.disabled
      context.listMaterial = props.listMaterial
      context.selectedMaterial = props.selectedMaterial
      context.selectedValue = selectedValue.value
      context.size = props.size
      context.unselectedMaterial = props.unselectedMaterial
    })
    provide(TabsContextKey, context)

    return () => {
      const { class: _class, ...rest } = attrs
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
          class: cx(props.prefixCls, tabsModule.tabs, props.rootClassName, attrs.class as string),
          id: props.id,
        },
        children,
      )
    }
  },
})
