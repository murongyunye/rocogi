<script setup lang="ts">
import { computed, ref, useAttrs } from 'vue'
import Material from './Material'
import {
  cx,
  textareaCornerPathByPart,
  textareaModule,
  textareaPrefixCls,
  type MaterialName,
} from './rk'

defineOptions({ name: 'RkTextarea', inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    countClassName?: string
    disabled?: boolean
    material?: MaterialName
    maxLength?: number
    prefixCls?: string
    readOnly?: boolean
    resize?: 'none' | 'vertical' | 'horizontal' | 'both'
    rootClassName?: string
    shadow?: boolean
    showCount?: boolean
    size?: 'small' | 'middle' | 'large'
    textareaClassName?: string
    variant?: 'solid' | 'outline' | 'text'
  }>(),
  {
    countClassName: undefined,
    disabled: false,
    material: 'stone',
    maxLength: undefined,
    prefixCls: textareaPrefixCls,
    readOnly: false,
    resize: 'vertical',
    rootClassName: undefined,
    shadow: false,
    showCount: false,
    size: 'middle',
    textareaClassName: undefined,
    variant: 'solid',
  },
)

const emit = defineEmits<{ (e: 'update:value', value: string): void }>()

const attrs = useAttrs()

const model = defineModel<string>('value')
const internalValue = ref('')
const currentValue = computed(() => model.value ?? internalValue.value)
const characterCount = computed(() => currentValue.value.length)

const textareaStyle = computed(() => ({
  ...((attrs.style ?? {}) as Record<string, string>),
  '--rk-textarea-resize': props.resize,
}))

const resolvedClassName = computed(() =>
  cx(
    props.prefixCls,
    textareaModule.textarea,
    textareaModule[props.size],
    textareaModule[props.variant],
    props.disabled && textareaModule.disabled,
    props.readOnly && textareaModule.readonly,
    props.rootClassName,
    attrs.class as string,
  ),
)

function handleChange(event: Event) {
  const value = (event.currentTarget as HTMLTextAreaElement).value
  internalValue.value = value
  model.value = value
  emit('update:value', value)
}

const passthrough = computed(() => {
  const { class: _class, style: _style, ...rest } = attrs
  return rest
})
</script>

<template>
  <Material as-child :material="props.material">
    <label
      :aria-disabled="props.disabled || undefined"
      :class="resolvedClassName"
      :data-disabled="props.disabled || undefined"
      :data-readonly="props.readOnly || undefined"
      :style="textareaStyle"
    >
      <!-- frame -->
      <span
        aria-hidden="true"
        :class="cx(textareaModule.frame, props.shadow && props.variant === 'solid' && textareaModule.withShadow)"
      >
        <span
          v-if="props.variant === 'solid' || props.variant === 'outline'"
          aria-hidden="true"
          :class="cx(textareaModule.frameLayer, props.variant === 'solid' ? textareaModule.fill : textareaModule.stroke)"
        >
          <span :class="cx(textareaModule.framePart, textareaModule.cornerTopLeft)">
            <svg :class="textareaModule.cornerSvg" focusable="false" preserveAspectRatio="none" viewBox="0 0 96 96">
              <path
                :class="textareaModule.cornerPath"
                :d="textareaCornerPathByPart[props.variant === 'solid' ? 'fill' : 'stroke']['top-left']"
                vector-effect="non-scaling-stroke"
              />
            </svg>
          </span>
          <span :class="cx(textareaModule.framePart, textareaModule.edgeTop)" />
          <span :class="cx(textareaModule.framePart, textareaModule.cornerTopRight)">
            <svg :class="textareaModule.cornerSvg" focusable="false" preserveAspectRatio="none" viewBox="0 0 96 96">
              <path
                :class="textareaModule.cornerPath"
                :d="textareaCornerPathByPart[props.variant === 'solid' ? 'fill' : 'stroke']['top-right']"
                vector-effect="non-scaling-stroke"
              />
            </svg>
          </span>
          <span :class="cx(textareaModule.framePart, textareaModule.edgeLeft)" />
          <span :class="cx(textareaModule.framePart, textareaModule.frameCenter)" />
          <span :class="cx(textareaModule.framePart, textareaModule.edgeRight)" />
          <span :class="cx(textareaModule.framePart, textareaModule.cornerBottomLeft)">
            <svg :class="textareaModule.cornerSvg" focusable="false" preserveAspectRatio="none" viewBox="0 0 96 96">
              <path
                :class="textareaModule.cornerPath"
                :d="textareaCornerPathByPart[props.variant === 'solid' ? 'fill' : 'stroke']['bottom-left']"
                vector-effect="non-scaling-stroke"
              />
            </svg>
          </span>
          <span :class="cx(textareaModule.framePart, textareaModule.edgeBottom)" />
          <span :class="cx(textareaModule.framePart, textareaModule.cornerBottomRight)">
            <svg :class="textareaModule.cornerSvg" focusable="false" preserveAspectRatio="none" viewBox="0 0 96 96">
              <path
                :class="textareaModule.cornerPath"
                :d="textareaCornerPathByPart[props.variant === 'solid' ? 'fill' : 'stroke']['bottom-right']"
                vector-effect="non-scaling-stroke"
              />
            </svg>
          </span>
        </span>
      </span>

      <span :class="textareaModule.content">
        <textarea
          v-bind="passthrough"
          :class="cx(`${props.prefixCls}-control`, textareaModule.control, props.textareaClassName)"
          :disabled="props.disabled"
          :maxlength="props.maxLength"
          :read-only="props.readOnly || undefined"
          :value="model"
          @input="handleChange"
        />
        <span
          v-if="props.showCount"
          :class="cx(`${props.prefixCls}-count`, textareaModule.count, props.countClassName)"
        >
          {{ typeof props.maxLength === 'number' ? `${characterCount} / ${props.maxLength}` : characterCount }}
        </span>
      </span>
    </label>
  </Material>
</template>
