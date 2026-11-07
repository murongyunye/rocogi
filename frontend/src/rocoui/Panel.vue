<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import { panelCurvePathBySide, panelModule, panelPrefixCls, cx, resolveSizePx, type MaterialName } from './rk'

defineOptions({ name: 'RkPanel', inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    as?: string
    contentClassName?: string
    curve?: 'none' | 'both' | 'bottom' | 'left' | 'right' | 'top'
    curveInset?: number | string
    material?: MaterialName
    prefixCls?: string
    rootClassName?: string
  }>(),
  {
    as: 'section',
    contentClassName: undefined,
    curve: 'none',
    curveInset: undefined,
    material: 'paper',
    prefixCls: panelPrefixCls,
    rootClassName: undefined,
  },
)

const attrs = useAttrs()

const isCurved = computed(() => props.curve !== 'none')

const panelStyle = computed(() => {
  const style: Record<string, string> = { ...((attrs.style ?? {}) as Record<string, string>) }
  const resolvedCurveInset = resolveSizePx(props.curveInset)
  if (resolvedCurveInset) style['--rk-panel-curve-inset'] = resolvedCurveInset
  return style
})

const classes = computed(() =>
  cx(
    props.prefixCls,
    panelModule.panel,
    panelModule[props.material],
    panelModule[props.curve],
    isCurved.value && panelModule.curved,
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
  <component :is="props.as" v-bind="passthrough" :class="classes" :style="panelStyle">
    <svg
      v-if="isCurved"
      aria-hidden="true"
      :class="panelModule.shape"
      focusable="false"
      preserveAspectRatio="none"
      viewBox="0 0 1000 1000"
    >
      <path :class="panelModule.shapePath" :d="panelCurvePathBySide[props.curve]" />
    </svg>
    <div :class="cx(`${props.prefixCls}-content`, panelModule.content, props.contentClassName)">
      <slot />
    </div>
  </component>
</template>
