<script setup lang="ts">
import { computed, ref, useAttrs } from 'vue'
import Material from './Material'
import RocoShape from './RocoShape.vue'
import { switchModule, switchPrefixCls, cx, type MaterialName } from './rk'

defineOptions({ name: 'RkSwitch', inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    checked?: boolean
    checkedMaterial?: MaterialName
    checkedShadow?: boolean
    defaultChecked?: boolean
    disabled?: boolean
    inputClassName?: string
    prefixCls?: string
    readOnly?: boolean
    rootClassName?: string
    size?: 'small' | 'middle' | 'large'
    thumbMaterial?: MaterialName
    uncheckedMaterial?: MaterialName
  }>(),
  {
    checked: undefined,
    checkedMaterial: 'success',
    checkedShadow: true,
    defaultChecked: false,
    disabled: false,
    inputClassName: undefined,
    prefixCls: switchPrefixCls,
    readOnly: false,
    rootClassName: undefined,
    size: 'middle',
    thumbMaterial: 'paper',
    uncheckedMaterial: 'stone',
  },
)

const emit = defineEmits<{
  (e: 'change', event: Event): void
  (e: 'update:checked', value: boolean): void
  (e: 'checkedChange', value: boolean): void
}>()

const attrs = useAttrs()

const model = defineModel<boolean>('checked')
const internalChecked = ref(Boolean(props.defaultChecked))
const isChecked = computed(() => model.value ?? internalChecked.value)

const resolvedTrackMaterial = computed(() => (isChecked.value ? props.checkedMaterial : props.uncheckedMaterial))

const resolvedClassName = computed(() =>
  cx(
    props.prefixCls,
    switchModule.switch,
    switchModule[props.size],
    isChecked.value ? switchModule.checked : switchModule.unchecked,
    props.disabled && switchModule.disabled,
    props.readOnly && switchModule.readonly,
    props.rootClassName,
    attrs.class as string,
  ),
)

function handleChange(event: Event) {
  const target = event.currentTarget as HTMLInputElement
  emit('change', event)
  if (props.readOnly) return
  const nextChecked = target.checked
  internalChecked.value = nextChecked
  model.value = nextChecked
  emit('checkedChange', nextChecked)
}

const passthrough = computed(() => {
  const { class: _class, ...rest } = attrs
  return rest
})
</script>

<template>
  <label
    :aria-disabled="props.disabled || undefined"
    :class="resolvedClassName"
    :data-readonly="props.readOnly || undefined"
    :data-state="isChecked ? 'checked' : 'unchecked'"
  >
    <input
      v-bind="passthrough"
      type="checkbox"
      role="switch"
      :aria-checked="isChecked"
      :class="cx(`${props.prefixCls}-control`, switchModule.input, props.inputClassName)"
      :checked="isChecked"
      :disabled="props.disabled"
      :read-only="props.readOnly || undefined"
      @change="handleChange"
    />
    <Material as-child :material="resolvedTrackMaterial">
      <RocoShape
        aria-hidden="true"
        :class="switchModule.track"
        :content-class-name="switchModule.trackContent"
        :shadow="isChecked && props.checkedShadow"
        variant="solid"
      >
        <Material as-child :material="props.thumbMaterial">
          <RocoShape :class="switchModule.thumb" shape="circle" variant="solid" />
        </Material>
      </RocoShape>
    </Material>
    <span v-if="$slots.default" :class="switchModule.label"><slot /></span>
  </label>
</template>
