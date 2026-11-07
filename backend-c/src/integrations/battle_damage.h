#ifndef ROCogi_BATTLE_DAMAGE_H
#define ROCogi_BATTLE_DAMAGE_H

/* 对战伤害结算：按 NRC_AI（ColinHong10/NRC_AI）src/battle.py 的 DamageCalculator
 * 与 src/models.py 的属性克制表重写，不引入 Python 运行时。 */

typedef enum {
    RK_TYPE_NORMAL = 0,
    RK_TYPE_FIRE,
    RK_TYPE_WATER,
    RK_TYPE_ELECTRIC,
    RK_TYPE_GRASS,
    RK_TYPE_ICE,
    RK_TYPE_FIGHTING,
    RK_TYPE_POISON,
    RK_TYPE_GROUND,
    RK_TYPE_FLYING,
    RK_TYPE_PSYCHIC,
    RK_TYPE_BUG,
    RK_TYPE_GHOST,
    RK_TYPE_DRAGON,
    RK_TYPE_DARK,
    RK_TYPE_STEEL,
    RK_TYPE_FAIRY,
    RK_TYPE_LIGHT,
    RK_TYPE_COUNT
} rk_type;

typedef enum {
    RK_CATEGORY_PHYSICAL = 0,
    RK_CATEGORY_MAGICAL,
    RK_CATEGORY_DEFENSE,
    RK_CATEGORY_STATUS
} rk_category;

typedef enum {
    RK_WEATHER_NONE = 0,
    RK_WEATHER_RAIN,
    RK_WEATHER_SANDSTORM,
    RK_WEATHER_SNOW
} rk_weather;

typedef struct {
    rk_category category;
    int power;
    double base_attack;
    double base_defense;
    double attack_up;    /* 我方攻击提升等级 */
    double attack_down;  /* 我方攻击下降等级 */
    double defense_up;   /* 对方防御提升等级 */
    double defense_down; /* 对方防御下降等级 */
    rk_type attack_type;
    rk_type defender_type;
    int same_type_bonus; /* 本系加成 1.5x */
    rk_weather weather;
    int hit_count;
    double power_multiplier; /* 威力提升 buff，独立乘法层 */
    int attacker_barrel;     /* 木桶状态：克制/抵抗失效 */
    int defender_barrel;
} rk_damage_input;

double rk_type_effectiveness(rk_type attack_type, rk_type defender_type);

int rk_calculate_damage(const rk_damage_input *input);

#endif
