<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import { cx, sideNavListPrefixCls, sideNavModule } from './rk'

defineOptions({ name: 'RkSideNavList', inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    prefixCls?: string
    rootClassName?: string
  }>(),
  { prefixCls: sideNavListPrefixCls, rootClassName: undefined },
)

const attrs = useAttrs()

const classes = computed(() =>
  cx(props.prefixCls, sideNavModule.list, props.rootClassName, attrs.class as string),
)

const passthrough = computed(() => {
  const { class: _class, ...rest } = attrs
  return rest
})
</script>

<template>
  <div v-bind="passthrough" :class="classes">
    <slot />
  </div>
</template>
