#ifndef ROCogi_MAPSTAT_H
#define ROCogi_MAPSTAT_H

/* 读取 data/map 下的点位数据，构建与 Python 版同结构的 map 统计 JSON */
int mapstat_init(const char *map_dir);
const char *mapstat_json(void);
int mapstat_point_count(void);

#endif
