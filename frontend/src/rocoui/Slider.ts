import { computed, defineComponent, h, type PropType, type VNodeChild } from 'vue'
import { cx } from './rk'

/**
 * Slider — documented on the docs site but not included in the beta npm package.
 * Native range input styled through --rk-* tokens (accent color + track/thumb in extras.css).
 */
export default defineComponent({
  name: 'RkSlider',
  props: {
    disabled: { type: Boolean, default: false },
    max: { type: Number, default: 100 },
    min: { type: Number, default: 0 },
    modelValue: { type: Number, default: 0 },
    step: { type: Number, default: 1 },
    variant: { type: String as PropType<'outline' | 'solid'>, default: 'solid' },
  },
  emits: ['update:modelValue', 'change'],
  setup(props, { attrs, emit }) {
    const percentage = computed(() => {
      if (props.max <= props.min) return 0
      return ((props.modelValue - props.min) / (props.max - props.min)) * 100
    })

    return (): VNodeChild => {
      const { class: _class, style: _style, ...rest } = attrs
      return h('span', { class: cx('rk-slider', `rk-slider-${props.variant}`), 'data-rk-slider': 'true' }, [
        h('input', {
          ...rest,
          'aria-valuemax': props.max,
          'aria-valuemin': props.min,
          'aria-valuenow': props.modelValue,
          disabled: props.disabled,
          max: props.max,
          min: props.min,
          onInput: (event: Event) => {
            const value = Number((event.target as HTMLInputElement).value)
            emit('update:modelValue', value)
            emit('change', value)
          },
          class: 'rk-slider-input',
          step: props.step,
          style: { '--rk-slider-fill-percent': `${percentage.value}%` },
          type: 'range',
          value: props.modelValue,
        }),
      ])
    }
  },
})
