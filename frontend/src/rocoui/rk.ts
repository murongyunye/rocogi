/**
 * rocokingdom-ui v0.0.1-beta.0 design tokens port (Vue 3, no runtime deps).
 * All class maps, SVG paths and material presets are copied verbatim from the
 * upstream npm package dist (MIT). CSS lives in ./style.css + ./font.css.
 */

export function cx(...parts: Array<string | number | false | null | undefined>): string {
  let out = '';
  for (const part of parts) {
    if (!part && part !== 0) continue;
    if (out) out += ' ';
    out += String(part);
  }
  return out;
}

/* ---------------- prefix constants (verbatim) ---------------- */

export const materialPrefixCls = 'rk-material';
export const rocoThemePrefixCls = 'rk-theme';
export const rocoShapePrefixCls = 'rk-roco-shape';
export const runeTextPrefixCls = 'rk-rune-text';
export const buttonPrefixCls = 'rk-button';
export const buttonNormalPrefixCls = 'rk-button-normal';
export const checkboxPrefixCls = 'rk-checkbox';
export const switchPrefixCls = 'rk-switch';
export const dividerPrefixCls = 'rk-divider';
export const panelPrefixCls = 'rk-panel';
export const sideNavPrefixCls = 'rk-side-nav';
export const sideNavHeaderPrefixCls = 'rk-side-nav-header';
export const sideNavListPrefixCls = 'rk-side-nav-list';
export const sideNavItemPrefixCls = 'rk-side-nav-item';
export const spacePrefixCls = 'rk-space';
export const stackPrefixCls = 'rk-stack';
export const layoutPrefixCls = 'rk-layout';
export const layoutHeaderPrefixCls = 'rk-layout-header';
export const layoutSiderPrefixCls = 'rk-layout-sider';
export const layoutContentPrefixCls = 'rk-layout-content';
export const layoutFooterPrefixCls = 'rk-layout-footer';
export const inputPrefixCls = 'rk-input';
export const textareaPrefixCls = 'rk-textarea';
export const selectPrefixCls = 'rk-select';
export const selectItemPrefixCls = 'rk-select-item';
export const tabsPrefixCls = 'rk-tabs';
export const tabListPrefixCls = 'rk-tab-list';
export const tabPrefixCls = 'rk-tab';
export const tabPanelPrefixCls = 'rk-tab-panel';
export const modalPrefixCls = 'rk-modal';
export const drawerPrefixCls = 'rk-drawer';
export const radioGroupPrefixCls = 'rk-radio-group';
export const radioItemPrefixCls = 'rk-radio-item';
export const toggleGroupPrefixCls = 'rk-toggle-group';
export const toggleItemPrefixCls = 'rk-toggle-item';

/* ---------------- CSS-module class maps (verbatim hashes) ---------------- */

export const materialModule: Record<string, string> = {
  material: 'ztMaoa_material',
};

export const rocoShapeModule: Record<string, string> = {
  cap: 'khU0fa_cap',
  center: 'khU0fa_center',
  centerLine: 'khU0fa_centerLine',
  circle: 'khU0fa_circle',
  content: 'khU0fa_content',
  curve: 'khU0fa_curve',
  edge: 'khU0fa_edge',
  fill: 'khU0fa_fill',
  fixed: 'khU0fa_fixed',
  fixedFill: 'khU0fa_fixedFill',
  fixedStroke: 'khU0fa_fixedStroke',
  layer: 'khU0fa_layer',
  outline: 'khU0fa_outline',
  shape: 'khU0fa_shape',
  square: 'khU0fa_square',
  stroke: 'khU0fa_stroke',
  text: 'khU0fa_text',
  withContent: 'khU0fa_withContent',
  withShadow: 'khU0fa_withShadow',
};

export const runeTextModule: Record<string, string> = {
  base: 'Jyxoua_base',
  rune: 'Jyxoua_rune',
  text: 'Jyxoua_text',
};

export const buttonModule: Record<string, string> = {
  button: 'Xwe9yG_button',
  content: 'Xwe9yG_content',
  large: 'Xwe9yG_large',
  middle: 'Xwe9yG_middle',
  small: 'Xwe9yG_small',
  text: 'Xwe9yG_text',
};

export const buttonNormalModule: Record<string, string> = {
  button: 'd5oCwa_button',
  danger: 'd5oCwa_danger',
  default: 'd5oCwa_default',
  large: 'd5oCwa_large',
  middle: 'd5oCwa_middle',
  outline: 'd5oCwa_outline',
  paper: 'd5oCwa_paper',
  paperMuted: 'd5oCwa_paperMuted',
  paperSoft: 'd5oCwa_paperSoft',
  paperStrong: 'd5oCwa_paperStrong',
  primary: 'd5oCwa_primary',
  primaryMuted: 'd5oCwa_primaryMuted',
  primarySoft: 'd5oCwa_primarySoft',
  primaryStrong: 'd5oCwa_primaryStrong',
  small: 'd5oCwa_small',
  solid: 'd5oCwa_solid',
  stone: 'd5oCwa_stone',
  stoneMuted: 'd5oCwa_stoneMuted',
  stoneSoft: 'd5oCwa_stoneSoft',
  stoneStrong: 'd5oCwa_stoneStrong',
  success: 'd5oCwa_success',
  text: 'd5oCwa_text',
};

export const checkboxModule: Record<string, string> = {
  check: 'TB3AjW_check',
  checkbox: 'TB3AjW_checkbox',
  checked: 'TB3AjW_checked',
  control: 'TB3AjW_control',
  disabled: 'TB3AjW_disabled',
  icon: 'TB3AjW_icon',
  input: 'TB3AjW_input',
  label: 'TB3AjW_label',
  large: 'TB3AjW_large',
  small: 'TB3AjW_small',
  unchecked: 'TB3AjW_unchecked',
};

export const switchModule: Record<string, string> = {
  checked: 'k1M-6a_checked',
  disabled: 'k1M-6a_disabled',
  input: 'k1M-6a_input',
  label: 'k1M-6a_label',
  large: 'k1M-6a_large',
  readonly: 'k1M-6a_readonly',
  small: 'k1M-6a_small',
  switch: 'k1M-6a_switch',
  thumb: 'k1M-6a_thumb',
  track: 'k1M-6a_track',
  trackContent: 'k1M-6a_trackContent',
  unchecked: 'k1M-6a_unchecked',
};

export const dividerModule: Record<string, string> = {
  dashed: 'oOidEa_dashed',
  divider: 'oOidEa_divider',
  dotted: 'oOidEa_dotted',
  end: 'oOidEa_end',
  horizontal: 'oOidEa_horizontal',
  label: 'oOidEa_label',
  labeled: 'oOidEa_labeled',
  solid: 'oOidEa_solid',
  start: 'oOidEa_start',
  vertical: 'oOidEa_vertical',
};

export const panelModule: Record<string, string> = {
  both: '_Urbza_both',
  bottom: '_Urbza_bottom',
  content: '_Urbza_content',
  curved: '_Urbza_curved',
  left: '_Urbza_left',
  panel: '_Urbza_panel',
  paper: '_Urbza_paper',
  paperMuted: '_Urbza_paperMuted',
  paperSoft: '_Urbza_paperSoft',
  paperStrong: '_Urbza_paperStrong',
  right: '_Urbza_right',
  shape: '_Urbza_shape',
  shapePath: '_Urbza_shapePath',
  stone: '_Urbza_stone',
  stoneMuted: '_Urbza_stoneMuted',
  stoneSoft: '_Urbza_stoneSoft',
  stoneStrong: '_Urbza_stoneStrong',
  top: '_Urbza_top',
};

export const layoutModule: Record<string, string> = {
  content: 'VduyCW_content',
  footer: 'VduyCW_footer',
  fullHeight: 'VduyCW_fullHeight',
  header: 'VduyCW_header',
  horizontal: 'VduyCW_horizontal',
  layout: 'VduyCW_layout',
  sider: 'VduyCW_sider',
  siderCollapsed: 'VduyCW_siderCollapsed',
  unpadded: 'VduyCW_unpadded',
  vertical: 'VduyCW_vertical',
};

export const sideNavModule: Record<string, string> = {
  active: '_tjnJG_active',
  header: '_tjnJG_header',
  headerContent: '_tjnJG_headerContent',
  headerEyebrow: '_tjnJG_headerEyebrow',
  headerIcon: '_tjnJG_headerIcon',
  headerText: '_tjnJG_headerText',
  headerTitle: '_tjnJG_headerTitle',
  item: '_tjnJG_item',
  itemBadge: '_tjnJG_itemBadge',
  itemBadgeDot: '_tjnJG_itemBadgeDot',
  itemIcon: '_tjnJG_itemIcon',
  itemLabel: '_tjnJG_itemLabel',
  list: '_tjnJG_list',
  nav: '_tjnJG_nav',
  rail: '_tjnJG_rail',
  stack: '_tjnJG_stack',
};

export const spaceModule: Record<string, string> = {
  block: 'fFUITG_block',
  horizontal: 'fFUITG_horizontal',
  space: 'fFUITG_space',
  split: 'fFUITG_split',
  stack: 'fFUITG_stack',
  vertical: 'fFUITG_vertical',
  wrap: 'fFUITG_wrap',
};

export const inputModule: Record<string, string> = {
  affix: 'g-B19a_affix',
  content: 'g-B19a_content',
  control: 'g-B19a_control',
  input: 'g-B19a_input',
  large: 'g-B19a_large',
  middle: 'g-B19a_middle',
  small: 'g-B19a_small',
};

export const textareaModule: Record<string, string> = {
  content: '-hBSFW_content',
  control: '-hBSFW_control',
  cornerBottomLeft: '-hBSFW_cornerBottomLeft',
  cornerBottomRight: '-hBSFW_cornerBottomRight',
  cornerPath: '-hBSFW_cornerPath',
  cornerSvg: '-hBSFW_cornerSvg',
  cornerTopLeft: '-hBSFW_cornerTopLeft',
  cornerTopRight: '-hBSFW_cornerTopRight',
  count: '-hBSFW_count',
  disabled: '-hBSFW_disabled',
  edgeBottom: '-hBSFW_edgeBottom',
  edgeLeft: '-hBSFW_edgeLeft',
  edgeRight: '-hBSFW_edgeRight',
  edgeTop: '-hBSFW_edgeTop',
  fill: '-hBSFW_fill',
  frame: '-hBSFW_frame',
  frameCenter: '-hBSFW_frameCenter',
  frameLayer: '-hBSFW_frameLayer',
  framePart: '-hBSFW_framePart',
  large: '-hBSFW_large',
  outline: '-hBSFW_outline',
  readonly: '-hBSFW_readonly',
  small: '-hBSFW_small',
  stroke: '-hBSFW_stroke',
  textarea: '-hBSFW_textarea',
  withShadow: '-hBSFW_withShadow',
};

export const selectModule: Record<string, string> = {
  content: '_2oBRua_content',
  contentShell: '_2oBRua_contentShell',
  item: '_2oBRua_item',
  itemCheck: '_2oBRua_itemCheck',
  itemIndicator: '_2oBRua_itemIndicator',
  trigger: '_2oBRua_trigger',
  triggerContent: '_2oBRua_triggerContent',
  triggerIcon: '_2oBRua_triggerIcon',
  value: '_2oBRua_value',
  viewport: '_2oBRua_viewport',
};

export const tabsModule: Record<string, string> = {
  large: 'r0-prq_large',
  list: 'r0-prq_list',
  listContent: 'r0-prq_listContent',
  middle: 'r0-prq_middle',
  panel: 'r0-prq_panel',
  panelActive: 'r0-prq_panelActive',
  panelInactive: 'r0-prq_panelInactive',
  selected: 'r0-prq_selected',
  small: 'r0-prq_small',
  tab: 'r0-prq_tab',
  tabContent: 'r0-prq_tabContent',
  tabText: 'r0-prq_tabText',
  tabs: 'r0-prq_tabs',
  unselected: 'r0-prq_unselected',
};

export const modalModule: Record<string, string> = {
  body: 'TnFApq_body',
  close: 'TnFApq_close',
  closeIcon: 'TnFApq_closeIcon',
  content: 'TnFApq_content',
  description: 'TnFApq_description',
  floatingClose: 'TnFApq_floatingClose',
  footer: 'TnFApq_footer',
  header: 'TnFApq_header',
  headerContent: 'TnFApq_headerContent',
  headerRuneText: 'TnFApq_headerRuneText',
  outsideClose: 'TnFApq_outsideClose',
  overlay: 'TnFApq_overlay',
  panel: 'TnFApq_panel',
  title: 'TnFApq_title',
  visuallyHidden: 'TnFApq_visuallyHidden',
};

export const drawerModule: Record<string, string> = {
  body: 'dMPmea_body',
  bottom: 'dMPmea_bottom',
  close: 'dMPmea_close',
  closeIcon: 'dMPmea_closeIcon',
  content: 'dMPmea_content',
  description: 'dMPmea_description',
  header: 'dMPmea_header',
  headerContent: 'dMPmea_headerContent',
  inner: 'dMPmea_inner',
  left: 'dMPmea_left',
  overlay: 'dMPmea_overlay',
  overlayVisible: 'dMPmea_overlayVisible',
  panel: 'dMPmea_panel',
  panelContent: 'dMPmea_panelContent',
  right: 'dMPmea_right',
  title: 'dMPmea_title',
  top: 'dMPmea_top',
  visuallyHidden: 'dMPmea_visuallyHidden',
};

export const radioGroupModule: Record<string, string> = {
  active: '_cWOfG_active',
  group: '_cWOfG_group',
  horizontal: '_cWOfG_horizontal',
  inactive: '_cWOfG_inactive',
  item: '_cWOfG_item',
  itemContent: '_cWOfG_itemContent',
  large: '_cWOfG_large',
  middle: '_cWOfG_middle',
  small: '_cWOfG_small',
  text: '_cWOfG_text',
  vertical: '_cWOfG_vertical',
};

/** Upstream beta bug: toggle-group CSS-module hash never made it into dist/style.css. */
export const toggleGroupModule: Record<string, string> = {
  group: '',
  horizontal: '',
  item: '',
  itemContent: '',
  itemText: '',
  large: '',
  middle: '',
  selected: '',
  small: '',
  unselected: '',
  vertical: '',
};

/* ---------------- SVG paths (verbatim) ---------------- */

export const rocoShapeEdgePath =
  'M0.0332642 244.999C15.0333 243.999 50.5333 241.499 66.5333 235.999C82.5333 230.499 148.533 220.499 156.033 141.999C163.533 63.4993 129.033 31.9993 88.0333 16.4993C47.0333 0.999313 9.53326 0.999313 0.0332642 0.499313';
export const rocoShapeEdgeFillPath =
  'M0.0332642 0.499313C9.53326 0.999313 47.0333 0.999313 88.0333 16.4993C129.033 31.9993 163.533 63.4993 156.033 141.999C148.533 220.499 82.5333 230.499 66.5333 235.999C50.5333 241.499 15.0333 243.999 0.0332642 244.999Z';
export const rocoShapeFixedPaths: Record<string, string> = {
  circle:
    'M0.858625 19.4179C2.67797 6.54462 15.0197 1.42301 22.3759 0.557875C34.7876 -0.134235 37.0705 5.57567 41.0941 7.30594C45.1176 9.03622 47.7417 15.7843 48.2665 18.7257C49.3161 29.9725 46.5171 33.9522 45.9923 35.8555C45.5808 37.348 41.7737 40.7359 39.9757 42.336L39.8695 42.4305C33.9217 46.4101 31.2976 48.2322 24.9999 48.4865C16.428 48.8325 8.55585 42.4305 8.20597 41.9114C7.8561 41.3923 -1.41555 35.5094 0.858625 19.4179Z',
  square:
    'M3.51624 2.91328C8.64261 -0.229054 37.6484 -0.353567 45.3019 2.83925C45.4231 2.88982 45.5194 2.93806 45.6124 3.03086C48.9809 6.39315 49.9675 44.1041 45.4742 46.1197C38.7272 49.5925 6.57349 48.9796 3.51625 46.1197C-0.305347 42.5447 -0.700629 6.28398 3.51624 2.91328Z',
};
export const panelCurvePathBySide: Record<string, string> = {
  bottom: 'M0 0H1000V880C754 958 246 958 0 880Z',
  both: 'M120 0C42 246 42 754 120 1000H880C958 754 958 246 880 0Z',
  left: 'M120 0C42 246 42 754 120 1000H1000V0Z',
  right: 'M0 0H880C958 246 958 754 880 1000H0Z',
  top: 'M0 120C246 42 754 42 1000 120V1000H0Z',
};
export const textareaCornerStrokePathByCorner: Record<string, string> = {
  'bottom-left': 'M0 0V47.8C0 75.6 22.4 96 53.6 96H96',
  'bottom-right': 'M0 96H51.8C78.4 96 96 73.5 96 44.2V0',
  'top-left': 'M0 96V54.2C0 24.5 22.6 0 55.8 0H96',
  'top-right': 'M0 0H51.2C79.2 0 96 22.2 96 52.8V96',
};
export const textareaCornerPathByPart: Record<string, Record<string, string>> = {
  fill: {
    'bottom-left': textareaCornerStrokePathByCorner['bottom-left'] + 'V0Z',
    'bottom-right': textareaCornerStrokePathByCorner['bottom-right'] + 'H0V96Z',
    'top-left': textareaCornerStrokePathByCorner['top-left'] + 'V96Z',
    'top-right': textareaCornerStrokePathByCorner['top-right'] + 'H0Z',
  },
  stroke: textareaCornerStrokePathByCorner,
};

/* ---------------- material presets (verbatim) ---------------- */

export type MaterialName =
  | 'default'
  | 'paper'
  | 'paperSoft'
  | 'paperMuted'
  | 'paperStrong'
  | 'primary'
  | 'primarySoft'
  | 'primaryMuted'
  | 'primaryStrong'
  | 'stone'
  | 'stoneSoft'
  | 'stoneMuted'
  | 'stoneStrong'
  | 'success'
  | 'danger';

export const materialValueByPreset: Record<MaterialName, { background: string; color: string }> = {
  danger: { background: 'var(--rk-danger)', color: 'var(--rk-on-danger)' },
  default: { background: 'var(--rk-primary)', color: 'var(--rk-on-primary)' },
  paper: { background: 'var(--rk-paper)', color: 'var(--rk-on-paper)' },
  paperMuted: { background: 'var(--rk-paper-muted)', color: 'var(--rk-on-paper-muted)' },
  paperSoft: { background: 'var(--rk-paper-soft)', color: 'var(--rk-on-paper-soft)' },
  paperStrong: { background: 'var(--rk-paper-strong)', color: 'var(--rk-on-paper-strong)' },
  primary: { background: 'var(--rk-primary)', color: 'var(--rk-on-primary)' },
  primaryMuted: { background: 'var(--rk-primary-muted)', color: 'var(--rk-on-primary-muted)' },
  primarySoft: { background: 'var(--rk-primary-soft)', color: 'var(--rk-on-primary-soft)' },
  primaryStrong: { background: 'var(--rk-primary-strong)', color: 'var(--rk-on-primary-strong)' },
  stone: { background: 'var(--rk-stone)', color: 'var(--rk-on-stone)' },
  stoneMuted: { background: 'var(--rk-stone-muted)', color: 'var(--rk-on-stone-muted)' },
  stoneSoft: { background: 'var(--rk-stone-soft)', color: 'var(--rk-on-stone-soft)' },
  stoneStrong: { background: 'var(--rk-stone-strong)', color: 'var(--rk-on-stone-strong)' },
  success: { background: 'var(--rk-success)', color: 'var(--rk-on-success)' },
};

export function resolveMaterial({
  background,
  color,
  material = 'paper',
}: { background?: string; color?: string; material?: MaterialName } = {}): {
  background: string;
  color: string;
  style: Record<string, string>;
} {
  const presetValue = materialValueByPreset[material];
  const resolvedBackground = background ?? presetValue.background;
  const resolvedColor = color ?? presetValue.color;
  return {
    background: resolvedBackground,
    color: resolvedColor,
    style: {
      '--rk-material-background': resolvedBackground,
      '--rk-material-color': resolvedColor,
    },
  };
}

/** Material asChild 语义：把 material 类与 --rk-material-* 变量合并到子元素。 */
export function materialAsChildProps({
  background,
  color,
  material = 'paper',
}: { background?: string; color?: string; material?: MaterialName } = {}): {
  class: string;
  style: Record<string, string>;
} {
  const value = resolveMaterial({ background, color, material });
  return { class: cx(materialPrefixCls, materialModule.material), style: value.style };
}

/* ---------------- size helpers ---------------- */

export function resolveSizePx(size?: number | string | null): string | undefined {
  if (size === undefined || size === null) return undefined;
  return typeof size === 'number' ? `${size}px` : size;
}

export const spaceSizeMap: Record<string, string> = {
  compact: '4px',
  small: '8px',
  middle: '16px',
  large: '24px',
};

export function resolveSpaceSize(size: number | string): string {
  if (typeof size === 'number') return `${size}px`;
  return size in spaceSizeMap ? spaceSizeMap[size] : size;
}

export function resolveGap(
  size?: 'compact' | 'small' | 'middle' | 'large' | number | string | [number | string, number | string],
): { columnGap?: string; rowGap?: string } {
  if (Array.isArray(size)) {
    const [columnGap, rowGap] = size as [number | string, number | string];
    return { columnGap: resolveSpaceSize(columnGap), rowGap: resolveSpaceSize(rowGap) };
  }
  if (size === undefined || size === null) return {};
  const gap = resolveSpaceSize(size as number | string);
  return { columnGap: gap, rowGap: gap };
}

/* ---------------- theme helpers (verbatim names) ---------------- */

export const rocoThemeColorNames = [
  'paper', 'paperSoft', 'paperMuted', 'paperStrong',
  'stone', 'stoneSoft', 'stoneMuted', 'stoneStrong',
  'primary', 'primarySoft', 'primaryMuted', 'primaryStrong',
  'success', 'danger',
  'onPaper', 'onPaperSoft', 'onPaperMuted', 'onPaperStrong',
  'onStone', 'onStoneSoft', 'onStoneMuted', 'onStoneStrong',
  'onPrimary', 'onPrimarySoft', 'onPrimaryMuted', 'onPrimaryStrong',
  'onSuccess', 'onDanger',
  'shadowSoftColor', 'shadowColor', 'shadowStrongColor',
] as const;

export const rocoThemeTokenNames = [
  'fontSizeBase', 'radius',
  'controlHeightSmall', 'controlHeightMiddle', 'controlHeightLarge',
  'controlPaddingInlineSmall', 'controlPaddingInlineMiddle', 'controlPaddingInlineLarge',
] as const;

const kebab = (name: string): string => name.replace(/[A-Z]/g, (ch) => '-' + ch.toLowerCase());

export function colorVariableName(name: string): string {
  return `--rk-${kebab(name)}`;
}

export function tokenVariableName(name: string): string {
  return `--rk-${kebab(name)}`;
}

export function mergeThemeRecord(
  keys: readonly string[],
  parentRecord: Record<string, string | undefined> | undefined,
  record: Record<string, string | undefined> | undefined,
): Record<string, string | undefined> | undefined {
  if (!record) return parentRecord;
  let mergedRecord: Record<string, string | undefined> | undefined;
  for (const key of keys) {
    const value = record[key];
    if (value === undefined) continue;
    mergedRecord ??= { ...parentRecord };
    mergedRecord[key] = value;
  }
  return mergedRecord ?? parentRecord;
}

export function toThemeStyle(
  colors: Record<string, string | undefined> | undefined,
  tokens: Record<string, string | undefined> | undefined,
): Record<string, string> {
  const themeStyle: Record<string, string> = {};
  for (const [name, value] of Object.entries(colors ?? {})) {
    if (value === undefined) continue;
    themeStyle[colorVariableName(name)] = value;
  }
  for (const [name, value] of Object.entries(tokens ?? {})) {
    if (value === undefined) continue;
    themeStyle[tokenVariableName(name)] = value;
  }
  return themeStyle;
}
