<script setup lang="ts">
import { computed, useAttrs, useSlots } from 'vue'
import Material from './Material'
import RocoShape from './RocoShape.vue'
import { cx, sideNavModule, sideNavHeaderPrefixCls } from './rk'

defineOptions({ name: 'RkSideNavHeader', inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    as?: string
    eyebrow?: boolean
    icon?: boolean
    prefixCls?: string
    rootClassName?: string
    title?: boolean
  }>(),
  {
    as: 'header',
    eyebrow: false,
    icon: false,
    prefixCls: sideNavHeaderPrefixCls,
    rootClassName: undefined,
    title: false,
  },
)

const slots = useSlots()
const attrs = useAttrs()

const hasStructuredContent = computed(() => props.icon || props.eyebrow || props.title)

const classes = computed(() =>
  cx(props.prefixCls, sideNavModule.header, props.rootClassName, attrs.class as string),
)

const passthrough = computed(() => {
  const { class: _class, ...rest } = attrs
  return rest
})
</script>

<template>
  <Material as-child material="stone">
    <RocoShape
      v-bind="passthrough"
      :as="props.as ?? 'header'"
      :class="classes"
      :content-class-name="sideNavModule.headerContent"
    >
      <template v-if="hasStructuredContent">
        <span v-if="props.icon" aria-hidden="true" :class="sideNavModule.headerIcon">
          <slot name="icon" />
        </span>
        <span :class="sideNavModule.headerText">
          <span v-if="props.eyebrow" :class="sideNavModule.headerEyebrow"><slot name="eyebrow" /></span>
          <span v-if="props.title" :class="sideNavModule.headerTitle"><slot name="title" /></span>
        </span>
      </template>
      <template v-else><slot /></template>
    </RocoShape>
  </Material>
</template>
