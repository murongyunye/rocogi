<script setup lang="ts">
import { computed, useAttrs, useSlots } from 'vue'
import {
  cx,
  rocoShapeModule,
  rocoShapePrefixCls,
  rocoShapeEdgePath,
  rocoShapeEdgeFillPath,
  rocoShapeFixedPaths,
} from './rk'
import type { ShapeVariant } from './context'

defineOptions({ name: 'RkRocoShape', inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    as?: string
    ariaHidden?: boolean
    background?: string
    color?: string
    contentClassName?: string
    prefixCls?: string
    rootClassName?: string
    shadow?: boolean
    shape?: 'stretch' | 'circle' | 'square'
    variant?: ShapeVariant
  }>(),
  {
    as: 'span',
    ariaHidden: undefined,
    background: undefined,
    color: undefined,
    contentClassName: undefined,
    prefixCls: rocoShapePrefixCls,
    rootClassName: undefined,
    shadow: false,
    shape: 'stretch',
    variant: 'solid',
  },
)

const slots = useSlots()
const attrs = useAttrs()

const hasFill = computed(() => props.variant === 'solid')
const hasStroke = computed(() => props.variant === 'outline')
const hasContent = computed(() => !!slots.default)
const isStretch = computed(() => props.shape === 'stretch')

const classes = computed(() =>
  cx(
    props.prefixCls,
    rocoShapeModule.shape,
    rocoShapeModule[props.shape],
    rocoShapeModule[props.variant],
    hasContent.value && rocoShapeModule.withContent,
    props.shadow && hasFill.value && rocoShapeModule.withShadow,
    props.rootClassName,
    attrs.class as string,
  ),
)

const shapeStyle = computed(() => {
  const style: Record<string, string> = { ...((attrs.style ?? {}) as Record<string, string>) }
  if (props.background) style['--rk-roco-shape-background'] = props.background
  if (props.color) style['--rk-roco-shape-color'] = props.color
  return style
})

const passthrough = computed(() => {
  const { class: _class, style: _style, ...rest } = attrs
  return rest
})

const ariaHiddenValue = computed(() => props.ariaHidden ?? (hasContent.value ? undefined : true))
</script>

<template>
  <component
    :is="props.as"
    v-bind="passthrough"
    :aria-hidden="ariaHiddenValue"
    :class="classes"
    :style="shapeStyle"
  >
    <!-- stretch + solid: fill layer (cap path + span center + mirrored cap) -->
    <span
      v-if="hasFill && isStretch"
      aria-hidden="true"
      :class="cx(rocoShapeModule.layer, rocoShapeModule.fill)"
    >
      <svg
        :class="rocoShapeModule.edge"
        focusable="false"
        preserveAspectRatio="xMidYMid meet"
        viewBox="0 0 158 246"
        aria-hidden="true"
      >
        <g transform="translate(158 246) scale(-1 -1)">
          <path :class="rocoShapeModule.cap" :d="rocoShapeEdgeFillPath" />
        </g>
      </svg>
      <span :class="rocoShapeModule.center" />
      <svg
        :class="rocoShapeModule.edge"
        focusable="false"
        preserveAspectRatio="xMidYMid meet"
        viewBox="0 0 158 246"
        aria-hidden="true"
      >
        <path :class="rocoShapeModule.cap" :d="rocoShapeEdgeFillPath" />
      </svg>
    </span>

    <!-- stretch + outline: stroke layer (curve path + centerline + mirrored curve) -->
    <span
      v-if="hasStroke && isStretch"
      aria-hidden="true"
      :class="cx(rocoShapeModule.layer, rocoShapeModule.stroke)"
    >
      <svg
        :class="rocoShapeModule.edge"
        focusable="false"
        preserveAspectRatio="xMidYMid meet"
        viewBox="0 0 158 246"
        aria-hidden="true"
      >
        <g transform="translate(158 246) scale(-1 -1)">
          <path :class="rocoShapeModule.curve" :d="rocoShapeEdgePath" vector-effect="non-scaling-stroke" />
        </g>
      </svg>
      <svg
        :class="rocoShapeModule.center"
        focusable="false"
        preserveAspectRatio="none"
        viewBox="0 0 100 100"
        aria-hidden="true"
      >
        <path :class="rocoShapeModule.centerLine" d="M0 0.3H100M0 99.7H100" vector-effect="non-scaling-stroke" />
      </svg>
      <svg
        :class="rocoShapeModule.edge"
        focusable="false"
        preserveAspectRatio="xMidYMid meet"
        viewBox="0 0 158 246"
        aria-hidden="true"
      >
        <path :class="rocoShapeModule.curve" :d="rocoShapeEdgePath" vector-effect="non-scaling-stroke" />
      </svg>
    </span>

    <!-- fixed (circle/square) -->
    <svg
      v-if="!isStretch && (hasFill || hasStroke)"
      aria-hidden="true"
      :class="cx(rocoShapeModule.fixed, hasFill ? rocoShapeModule.fill : rocoShapeModule.stroke)"
      focusable="false"
      preserveAspectRatio="xMidYMid meet"
      viewBox="0 0 49 49"
    >
      <path
        :class="hasFill ? rocoShapeModule.fixedFill : rocoShapeModule.fixedStroke"
        :d="rocoShapeFixedPaths[props.shape]"
        vector-effect="non-scaling-stroke"
      />
    </svg>

    <!-- content layer -->
    <span v-if="hasContent" :class="cx(rocoShapeModule.content, props.contentClassName)">
      <slot />
    </span>
  </component>
</template>
