import type { ComputedRef, InjectionKey } from 'vue'
import type { MaterialName } from './rk'

export type ControlSize = 'small' | 'middle' | 'large'
export type ShapeVariant = 'solid' | 'outline' | 'text'

export interface RocoThemeContext {
  colors: ComputedRef<Record<string, string | undefined> | undefined>
  tokens: ComputedRef<Record<string, string | undefined> | undefined>
}
export const RocoThemeContextKey: InjectionKey<RocoThemeContext> = Symbol('RocoThemeContext')

export interface TabsContext {
  disabled?: boolean
  getTabId?: (value: string | number) => string
  getPanelId?: (value: string | number) => string
  onValueChange?: (value: string | number) => void
  listMaterial?: MaterialName
  selectedMaterial?: MaterialName
  unselectedMaterial?: MaterialName
  selectedValue?: string | number | null
  size?: ControlSize
}
export const TabsContextKey: InjectionKey<TabsContext> = Symbol('TabsContext')

export interface RadioGroupContext {
  activeMaterial?: MaterialName
  activeShadow?: boolean
  activeVariant?: ShapeVariant
  inactiveMaterial?: MaterialName
  inactiveShadow?: boolean
  inactiveVariant?: ShapeVariant
  size?: ControlSize
  disabled?: boolean
  selectedValue?: string | number | null
  onValueChange?: (value: string | number) => void
}
export const RadioGroupContextKey: InjectionKey<RadioGroupContext> = Symbol('RadioGroupContext')

export interface ToggleGroupContext {
  selectedMaterial?: MaterialName
  selectedShadow?: boolean
  selectedVariant?: ShapeVariant
  unselectedMaterial?: MaterialName
  unselectedShadow?: boolean
  unselectedVariant?: ShapeVariant
  size?: ControlSize
  disabled?: boolean
  selectedValues?: Array<string | number>
  toggleValue?: (value: string | number) => void
}
export const ToggleGroupContextKey: InjectionKey<ToggleGroupContext> = Symbol('ToggleGroupContext')

export interface SelectRootContext {
  disabled?: boolean
  open?: boolean
  value?: string | number | null
}
export const SelectRootContextKey: InjectionKey<SelectRootContext> = Symbol('SelectRootContext')
