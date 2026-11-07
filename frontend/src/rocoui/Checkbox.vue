<script setup lang="ts">
import { computed, ref, useAttrs } from 'vue'
import Material from './Material'
import RocoShape from './RocoShape.vue'
import { IconCheck } from './icons'
import { checkboxModule, checkboxPrefixCls, cx, resolveMaterial, type MaterialName } from './rk'
import type { ShapeVariant } from './context'

defineOptions({ name: 'RkCheckbox', inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    boxMaterial?: MaterialName
    checkMaterial?: MaterialName
    checked?: boolean
    checkedClassName?: string
    defaultChecked?: boolean
    disabled?: boolean
    material?: MaterialName
    prefixCls?: string
    rootClassName?: string
    shadow?: boolean
    size?: 'small' | 'middle' | 'large'
    uncheckedClassName?: string
    uncheckedVariant?: ShapeVariant
    variant?: ShapeVariant
  }>(),
  {
    boxMaterial: undefined,
    checkMaterial: 'success',
    checked: undefined,
    checkedClassName: undefined,
    defaultChecked: false,
    disabled: false,
    material: undefined,
    prefixCls: checkboxPrefixCls,
    rootClassName: undefined,
    shadow: false,
    size: 'middle',
    uncheckedClassName: undefined,
    uncheckedVariant: 'outline',
    variant: 'solid',
  },
)

const emit = defineEmits<{ (e: 'change', event: Event): void; (e: 'update:checked', value: boolean): void }>()

const attrs = useAttrs()

/** controlled when `checked` prop is bound, otherwise internal state */
const model = defineModel<boolean>('checked')
const internalChecked = ref(Boolean(props.defaultChecked))
const isChecked = computed(() => model.value ?? internalChecked.value)

const shapeVariant = computed(() => (isChecked.value ? props.variant : props.uncheckedVariant))
const resolvedBoxMaterial = computed(() => props.boxMaterial ?? props.material ?? 'stone')
const checkMaterialStyle = resolveMaterial({ material: props.checkMaterial }).style

const resolvedClassName = computed(() =>
  cx(
    props.prefixCls,
    checkboxModule.checkbox,
    checkboxModule[props.size],
    checkboxModule[shapeVariant.value],
    isChecked.value ? checkboxModule.checked : checkboxModule.unchecked,
    props.disabled && checkboxModule.disabled,
    props.rootClassName,
    attrs.class as string,
    isChecked.value ? props.checkedClassName : props.uncheckedClassName,
  ),
)

function handleChange(event: Event) {
  const target = event.currentTarget as HTMLInputElement
  emit('change', event)
  const nextChecked = target.checked
  internalChecked.value = nextChecked
  model.value = nextChecked
}

const passthrough = computed(() => {
  const { class: _class, ...rest } = attrs
  return rest
})
</script>

<template>
  <label :aria-disabled="props.disabled || undefined" :class="resolvedClassName" :data-state="isChecked ? 'checked' : 'unchecked'">
    <input
      v-bind="passthrough"
      type="checkbox"
      :class="checkboxModule.input"
      :checked="isChecked"
      :disabled="props.disabled"
      @change="handleChange"
    />
    <Material as-child :material="resolvedBoxMaterial">
      <RocoShape
        aria-hidden="true"
        :class="checkboxModule.control"
        :content-class-name="checkboxModule.icon"
        :shadow="isChecked && props.shadow"
        shape="square"
        :variant="shapeVariant"
      >
        <template v-if="isChecked">
          <span :class="checkboxModule.check" :style="checkMaterialStyle">
            <slot name="icon"><IconCheck /></slot>
          </span>
        </template>
      </RocoShape>
    </Material>
    <span v-if="$slots.default" :class="checkboxModule.label"><slot /></span>
  </label>
</template>
