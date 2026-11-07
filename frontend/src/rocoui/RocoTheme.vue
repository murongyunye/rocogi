<script setup lang="ts">
import { computed, inject, provide, unref } from 'vue'
import {
  mergeThemeRecord,
  rocoThemeColorNames,
  rocoThemePrefixCls,
  rocoThemeTokenNames,
  toThemeStyle,
} from './rk'
import { RocoThemeContextKey, type RocoThemeContext } from './context'

const props = withDefaults(
  defineProps<{
    colors?: Record<string, string | undefined>
    tokens?: Record<string, string | undefined>
    as?: string
  }>(),
  { colors: undefined, tokens: undefined, as: 'div' },
)

const parent = inject<RocoThemeContext | undefined>(RocoThemeContextKey, undefined)

const colors = computed(() => mergeThemeRecord(rocoThemeColorNames, parent?.colors.value, props.colors))
const tokens = computed(() => mergeThemeRecord(rocoThemeTokenNames, parent?.tokens.value, props.tokens))

provide(RocoThemeContextKey, { colors, tokens })

const themeStyle = computed(() => toThemeStyle(unref(colors), unref(tokens)))
</script>

<template>
  <component :is="props.as" :class="rocoThemePrefixCls" :style="themeStyle">
    <slot />
  </component>
</template>
