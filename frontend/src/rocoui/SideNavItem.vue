<script setup lang="ts">
import { computed, useAttrs, useSlots } from 'vue'
import { cx, sideNavItemPrefixCls, sideNavModule } from './rk'

defineOptions({ name: 'RkSideNavItem', inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    active?: boolean
    badge?: boolean | string | number
    disabled?: boolean
    icon?: boolean
    prefixCls?: string
    rootClassName?: string
  }>(),
  {
    active: false,
    badge: undefined,
    disabled: false,
    icon: false,
    prefixCls: sideNavItemPrefixCls,
    rootClassName: undefined,
  },
)

const slots = useSlots()
const attrs = useAttrs()

const hasBadge = computed(() => props.badge !== undefined && props.badge !== null && props.badge !== false)

const classes = computed(() =>
  cx(
    props.prefixCls,
    sideNavModule.item,
    props.active && sideNavModule.active,
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
  <button
    v-bind="passthrough"
    :aria-current="props.active ? 'page' : undefined"
    :class="classes"
    :data-state="props.active ? 'active' : 'inactive'"
    :disabled="props.disabled"
    type="button"
  >
    <span v-if="props.icon" aria-hidden="true" :class="sideNavModule.itemIcon">
      <slot name="icon" />
    </span>
    <span v-if="slots.default" :class="sideNavModule.itemLabel"><slot /></span>
    <span
      v-if="hasBadge"
      :class="cx(sideNavModule.itemBadge, props.badge === true && sideNavModule.itemBadgeDot)"
    >
      <template v-if="props.badge !== true">{{ props.badge }}</template>
    </span>
  </button>
</template>
