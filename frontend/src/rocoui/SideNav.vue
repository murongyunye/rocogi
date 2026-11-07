<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import { cx, sideNavModule, sideNavPrefixCls } from './rk'

defineOptions({ name: 'RkSideNav', inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    as?: string
    prefixCls?: string
    rootClassName?: string
    variant?: 'stack' | 'rail'
  }>(),
  { as: 'nav', prefixCls: sideNavPrefixCls, rootClassName: undefined, variant: 'stack' },
)

const attrs = useAttrs()

const classes = computed(() =>
  cx(
    props.prefixCls,
    sideNavModule.nav,
    sideNavModule[props.variant],
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
  <component :is="props.as" v-bind="passthrough" :class="classes" :data-variant="props.variant">
    <slot />
  </component>
</template>
