<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import Material from './Material'
import RocoShape from './RocoShape.vue'
import RuneText from './RuneText'
import { buttonModule, buttonPrefixCls, cx, type MaterialName } from './rk'
import type { ShapeVariant } from './context'

defineOptions({ name: 'RkButton', inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    material?: MaterialName
    prefixCls?: string
    rootClassName?: string
    shadow?: boolean
    size?: 'small' | 'middle' | 'large'
    type?: 'button' | 'submit' | 'reset'
    variant?: ShapeVariant
    disabled?: boolean
  }>(),
  {
    material: 'default',
    prefixCls: buttonPrefixCls,
    rootClassName: undefined,
    shadow: false,
    size: 'middle',
    type: 'button',
    variant: 'solid',
    disabled: undefined,
  },
)

const attrs = useAttrs()

const shapeClasses = computed(() =>
  cx(
    props.prefixCls,
    buttonModule.button,
    buttonModule[props.size],
    buttonModule[props.variant],
    props.rootClassName,
    attrs.class as string,
  ),
)

const passthrough = computed(() => {
  const { class: _class, ...rest } = attrs
  return rest
})
</script>

<template>
  <Material as-child :material="props.material">
    <RocoShape
      as="button"
      v-bind="{ ...passthrough, type: props.type, disabled: props.disabled }"
      :class="shapeClasses"
      :shadow="props.variant === 'text' ? false : props.shadow"
      :variant="props.variant"
    >
      <RuneText :class="buttonModule.content"><slot /></RuneText>
    </RocoShape>
  </Material>
</template>
