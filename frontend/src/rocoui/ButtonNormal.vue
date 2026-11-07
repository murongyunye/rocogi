<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import { buttonNormalModule, buttonNormalPrefixCls, cx, type MaterialName } from './rk'

defineOptions({ name: 'RkButtonNormal', inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    material?: MaterialName
    prefixCls?: string
    rootClassName?: string
    size?: 'small' | 'middle' | 'large'
    type?: 'button' | 'submit' | 'reset'
    variant?: 'solid' | 'outline' | 'text'
  }>(),
  {
    material: 'default',
    prefixCls: buttonNormalPrefixCls,
    rootClassName: undefined,
    size: 'middle',
    type: 'button',
    variant: 'solid',
  },
)

const attrs = useAttrs()

const classes = computed(() =>
  cx(
    props.prefixCls,
    buttonNormalModule.button,
    buttonNormalModule[props.material],
    buttonNormalModule[props.size],
    buttonNormalModule[props.variant],
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
  <button v-bind="{ ...passthrough, type: props.type }" :class="classes">
    <slot />
  </button>
</template>
