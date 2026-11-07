<script setup lang="ts">
import { computed, useAttrs, useSlots } from 'vue'
import { dividerModule, dividerPrefixCls, cx, resolveSizePx } from './rk'

defineOptions({ name: 'RkDivider', inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    align?: 'start' | 'center' | 'end'
    as?: string
    color?: string
    dashed?: boolean
    orientation?: 'horizontal' | 'vertical'
    prefixCls?: string
    role?: string
    rootClassName?: string
    thickness?: number | string
    variant?: 'solid' | 'dotted'
  }>(),
  {
    align: 'center',
    as: 'div',
    color: undefined,
    dashed: false,
    orientation: 'horizontal',
    prefixCls: dividerPrefixCls,
    role: 'separator',
    rootClassName: undefined,
    thickness: undefined,
    variant: 'solid',
  },
)

const slots = useSlots()
const attrs = useAttrs()

const isLabeled = computed(() => props.orientation === 'horizontal' && !!slots.default)
const resolvedVariant = computed(() => (props.dashed ? 'dashed' : props.variant))

const dividerStyle = computed(() => {
  const style: Record<string, string> = { ...((attrs.style ?? {}) as Record<string, string>) }
  if (props.color) style['--rk-divider-color'] = props.color
  const resolvedThickness = resolveSizePx(props.thickness)
  if (resolvedThickness) style['--rk-divider-thickness'] = resolvedThickness
  return style
})

const classes = computed(() =>
  cx(
    props.prefixCls,
    dividerModule.divider,
    dividerModule[props.orientation],
    dividerModule[resolvedVariant.value],
    isLabeled.value && dividerModule.labeled,
    isLabeled.value && dividerModule[props.align],
    props.rootClassName,
    attrs.class as string,
  ),
)

const passthrough = computed(() => {
  const { class: _class, style: _style, ...rest } = attrs
  return rest
})
</script>

<template>
  <component
    :is="props.as"
    v-bind="passthrough"
    :aria-orientation="props.orientation"
    :class="classes"
    :data-orientation="props.orientation"
    :role="props.role"
    :style="dividerStyle"
  >
    <span v-if="isLabeled" :class="cx(`${props.prefixCls}-label`, dividerModule.label)">
      <slot />
    </span>
  </component>
</template>
