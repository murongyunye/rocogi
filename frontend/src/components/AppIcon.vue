<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    name: string
    size?: number
  }>(),
  { size: 18 },
)

const paths: Record<string, string[]> = {
  workflow: [
    'M4 4h5v5H4z',
    'M15 15h5v5h-5z',
    'M9 6.5h4a2 2 0 0 1 2 2v6.5',
  ],
  runs: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z', 'M10 8l6 4-6 4z'],
  resources: ['M12 3l9 5-9 5-9-5z', 'M3 13l9 5 9-5', 'M3 17l9 5 9-5'],
  map: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z', 'M15.5 8.5l-2 5-5 2 2-5z'],
  battle: ['M14.5 3.5l6 6-9 9-6-6z', 'M3 21l4-4', 'M9.5 3.5l6 6'],
  settings: [
    'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
    'M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17L4.9 19.1',
  ],
  plus: ['M12 5v14M5 12h14'],
  play: ['M7 4l13 8-13 8z'],
  stop: ['M6 6h12v12H6z'],
  save: [
    'M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z',
    'M17 21v-8H7v8M7 3v5h8',
  ],
  search: ['M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z', 'M20 20l-3.5-3.5'],
  chevron: ['M6 9l6 6 6-6'],
  check: ['M4 12l5 5L20 7'],
  close: ['M6 6l12 12M18 6L6 18'],
  trash: ['M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3'],
  copy: ['M9 9h12v12H9z', 'M5 15V5a2 2 0 0 1 2-2h10'],
  refresh: ['M20 11a8 8 0 1 0-2 6', 'M20 4v7h-7'],
  zoomIn: ['M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z', 'M20 20l-3.5-3.5M8 11h6M11 8v6'],
  zoomOut: ['M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z', 'M20 20l-3.5-3.5M8 11h6'],
  fit: ['M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5'],
  crosshair: ['M12 5a7 7 0 1 0 0 14 7 7 0 0 0 0-14z', 'M12 2v4M12 18v4M2 12h4M18 12h4'],
  route: ['M6 17a2 2 0 1 0 0 4 2 2 0 0 0 0-4z', 'M18 3a2 2 0 1 0 0 4 2 2 0 0 0 0-4z', 'M8 19h6a4 4 0 0 0 4-4V7'],
  target: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z', 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z', 'M12 2v3M12 19v3M2 12h3M19 12h3'],
  activity: ['M3 12h4l3-8 4 16 3-8h4'],
  arrowLeft: ['M19 12H5M11 18l-6-6 6-6'],
  spark: ['M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z'],
  warning: ['M12 3l10 18H2z', 'M12 9v5M12 17v.01'],
  filter: ['M4 5h16l-6 8v6l-4 2v-8z'],
  clock: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z', 'M12 7v5l3 3'],
  cpu: ['M5 5h14v14H5z', 'M9 9h6v6H9z', 'M12 2v3M12 19v3M2 12h3M19 12h3'],
  panel: ['M3 4h18v16H3z', 'M9 4v16'],
  dot: ['M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z'],
  external: ['M14 4h6v6M20 4l-9 9', 'M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4'],
  download: ['M12 4v11M7 11l5 5 5-5', 'M5 20h14'],
  upload: ['M12 20V9M7 13l5-5 5 5', 'M5 4h14'],
  image: ['M3 4h18v16H3z', 'M8.5 8a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z', 'M21 15l-5-5-9 9'],
  database: ['M12 2.5a8 3 0 1 0 0 6 8 3 0 0 0 0-6z', 'M4 5.5v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6M4 11.5v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6'],
  node: ['M4 4h7v7H4z', 'M13 13h7v7h-7z', 'M11 8h3a2 2 0 0 1 2 2v3'],
}
</script>

<template>
  <svg
    :width="props.size"
    :height="props.size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path v-for="(path, index) in paths[props.name] || paths.node" :key="index" :d="path" />
  </svg>
</template>
