import { defineComponent, h, type PropType, type VNodeChild } from 'vue'
import Material from './Material'
import { cx, type MaterialName } from './rk'

/**
 * Tag — documented on the docs site but not included in the beta npm package.
 * Material-backed chip with optional close button.
 */
export default defineComponent({
  name: 'RkTag',
  props: {
    closable: { type: Boolean, default: false },
    closeLabel: { type: String, default: '移除' },
    material: { type: String as PropType<MaterialName>, default: 'stone' },
    size: { type: String as PropType<'middle' | 'small'>, default: 'middle' },
  },
  emits: ['close'],
  setup(props, { slots, emit }) {
    return (): VNodeChild =>
      h(
        Material,
        {
          as: 'span',
          class: cx('rk-tag', `rk-tag-${props.size}`),
          'data-rk-tag': 'true',
          material: props.material,
        },
        {
          default: () => [
            h('span', { class: 'rk-tag-label' }, slots.default?.()),
            props.closable
              ? h(
                  'button',
                  {
                    'aria-label': props.closeLabel,
                    class: 'rk-tag-close',
                    onClick: (event: MouseEvent) => {
                      event.stopPropagation()
                      emit('close', event)
                    },
                    type: 'button',
                  },
                  '×',
                )
              : null,
          ],
        },
      )
  },
})
