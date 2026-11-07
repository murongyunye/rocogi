<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import Material from './Material'
import RocoShape from './RocoShape.vue'
import { cx, inputModule, inputPrefixCls, type MaterialName } from './rk'

defineOptions({ name: 'RkInput', inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    disabled?: boolean
    inputClassName?: string
    material?: MaterialName
    prefix?: boolean
    prefixCls?: string
    readOnly?: boolean
    rootClassName?: string
    shadow?: boolean
    size?: 'small' | 'middle' | 'large'
    suffix?: boolean
    type?: string
    variant?: 'solid' | 'outline' | 'text'
  }>(),
  {
    disabled: false,
    inputClassName: undefined,
    material: 'stone',
    prefix: false,
    prefixCls: inputPrefixCls,
    readOnly: false,
    rootClassName: undefined,
    shadow: false,
    size: 'middle',
    suffix: false,
    type: 'text',
    variant: 'solid',
  },
)

const emit = defineEmits<{ (e: 'update:value', value: string): void }>()

const attrs = useAttrs()

const model = defineModel<string>('value')

const resolvedClassName = computed(() =>
  cx(
    props.prefixCls,
    inputModule.input,
    inputModule[props.size],
    inputModule[props.variant],
    props.rootClassName,
    attrs.class as string,
  ),
)

function handleInput(event: Event) {
  model.value = (event.currentTarget as HTMLInputElement).value
}

const passthrough = computed(() => {
  const { class: _class, ...rest } = attrs
  return rest
})
</script>

<template>
  <Material as-child :material="props.material">
    <RocoShape
      as="label"
      :aria-disabled="props.disabled || undefined"
      :class="resolvedClassName"
      :content-class-name="inputModule.content"
      :data-disabled="props.disabled || undefined"
      :data-readonly="props.readOnly || undefined"
      :shadow="props.shadow"
      :variant="props.variant"
    >
      <span v-if="props.prefix" :class="inputModule.affix"><slot name="prefix" /></span>
      <input
        v-bind="passthrough"
        :class="cx(`${props.prefixCls}-control`, inputModule.control, props.inputClassName)"
        :disabled="props.disabled"
        :read-only="props.readOnly || undefined"
        :type="props.type"
        :value="model"
        @input="handleInput"
      />
      <span v-if="props.suffix" :class="inputModule.affix"><slot name="suffix" /></span>
    </RocoShape>
  </Material>
</template>
