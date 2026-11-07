#include "battle_damage.h"

#include <math.h>

/* 属性克制表：0 表示未声明（等价于 1.0），与上游 TYPE_CHART 逐项对齐。 */
static const double TYPE_CHART[RK_TYPE_COUNT][RK_TYPE_COUNT] = {
    [RK_TYPE_NORMAL][RK_TYPE_GROUND] = 0.5,
    [RK_TYPE_NORMAL][RK_TYPE_GHOST] = 0.5,
    [RK_TYPE_NORMAL][RK_TYPE_STEEL] = 0.5,

    [RK_TYPE_GRASS][RK_TYPE_FIRE] = 0.5,
    [RK_TYPE_GRASS][RK_TYPE_WATER] = 2.0,
    [RK_TYPE_GRASS][RK_TYPE_LIGHT] = 2.0,
    [RK_TYPE_GRASS][RK_TYPE_GROUND] = 2.0,
    [RK_TYPE_GRASS][RK_TYPE_DRAGON] = 0.5,
    [RK_TYPE_GRASS][RK_TYPE_POISON] = 0.5,
    [RK_TYPE_GRASS][RK_TYPE_BUG] = 0.5,
    [RK_TYPE_GRASS][RK_TYPE_FLYING] = 0.5,
    [RK_TYPE_GRASS][RK_TYPE_STEEL] = 0.5,

    [RK_TYPE_FIRE][RK_TYPE_GRASS] = 2.0,
    [RK_TYPE_FIRE][RK_TYPE_WATER] = 0.5,
    [RK_TYPE_FIRE][RK_TYPE_GROUND] = 0.5,
    [RK_TYPE_FIRE][RK_TYPE_ICE] = 2.0,
    [RK_TYPE_FIRE][RK_TYPE_DRAGON] = 0.5,
    [RK_TYPE_FIRE][RK_TYPE_BUG] = 2.0,
    [RK_TYPE_FIRE][RK_TYPE_STEEL] = 2.0,

    [RK_TYPE_WATER][RK_TYPE_GRASS] = 0.5,
    [RK_TYPE_WATER][RK_TYPE_FIRE] = 2.0,
    [RK_TYPE_WATER][RK_TYPE_GROUND] = 2.0,
    [RK_TYPE_WATER][RK_TYPE_ICE] = 0.5,
    [RK_TYPE_WATER][RK_TYPE_DRAGON] = 0.5,
    [RK_TYPE_WATER][RK_TYPE_STEEL] = 2.0,

    [RK_TYPE_LIGHT][RK_TYPE_GRASS] = 0.5,
    [RK_TYPE_LIGHT][RK_TYPE_ICE] = 0.5,
    [RK_TYPE_LIGHT][RK_TYPE_GHOST] = 2.0,
    [RK_TYPE_LIGHT][RK_TYPE_DARK] = 2.0,

    [RK_TYPE_GROUND][RK_TYPE_GRASS] = 0.5,
    [RK_TYPE_GROUND][RK_TYPE_FIRE] = 2.0,
    [RK_TYPE_GROUND][RK_TYPE_ICE] = 2.0,
    [RK_TYPE_GROUND][RK_TYPE_ELECTRIC] = 2.0,
    [RK_TYPE_GROUND][RK_TYPE_POISON] = 2.0,
    [RK_TYPE_GROUND][RK_TYPE_FIGHTING] = 0.5,

    [RK_TYPE_ICE][RK_TYPE_GRASS] = 2.0,
    [RK_TYPE_ICE][RK_TYPE_FIRE] = 0.5,
    [RK_TYPE_ICE][RK_TYPE_GROUND] = 2.0,
    [RK_TYPE_ICE][RK_TYPE_ICE] = 0.5,
    [RK_TYPE_ICE][RK_TYPE_DRAGON] = 2.0,
    [RK_TYPE_ICE][RK_TYPE_FLYING] = 2.0,
    [RK_TYPE_ICE][RK_TYPE_STEEL] = 0.5,

    [RK_TYPE_DRAGON][RK_TYPE_DRAGON] = 2.0,
    [RK_TYPE_DRAGON][RK_TYPE_STEEL] = 0.5,

    [RK_TYPE_ELECTRIC][RK_TYPE_GRASS] = 0.5,
    [RK_TYPE_ELECTRIC][RK_TYPE_WATER] = 2.0,
    [RK_TYPE_ELECTRIC][RK_TYPE_GROUND] = 0.5,
    [RK_TYPE_ELECTRIC][RK_TYPE_DRAGON] = 0.5,
    [RK_TYPE_ELECTRIC][RK_TYPE_ELECTRIC] = 0.5,
    [RK_TYPE_ELECTRIC][RK_TYPE_FLYING] = 2.0,

    [RK_TYPE_POISON][RK_TYPE_GRASS] = 2.0,
    [RK_TYPE_POISON][RK_TYPE_GROUND] = 0.5,
    [RK_TYPE_POISON][RK_TYPE_POISON] = 0.5,
    [RK_TYPE_POISON][RK_TYPE_FAIRY] = 2.0,
    [RK_TYPE_POISON][RK_TYPE_GHOST] = 0.5,
    [RK_TYPE_POISON][RK_TYPE_STEEL] = 0.5,

    [RK_TYPE_BUG][RK_TYPE_GRASS] = 2.0,
    [RK_TYPE_BUG][RK_TYPE_FIRE] = 0.5,
    [RK_TYPE_BUG][RK_TYPE_POISON] = 0.5,
    [RK_TYPE_BUG][RK_TYPE_FIGHTING] = 0.5,
    [RK_TYPE_BUG][RK_TYPE_FLYING] = 0.5,
    [RK_TYPE_BUG][RK_TYPE_FAIRY] = 0.5,
    [RK_TYPE_BUG][RK_TYPE_GHOST] = 0.5,
    [RK_TYPE_BUG][RK_TYPE_DARK] = 2.0,
    [RK_TYPE_BUG][RK_TYPE_STEEL] = 0.5,
    [RK_TYPE_BUG][RK_TYPE_PSYCHIC] = 2.0,

    [RK_TYPE_FIGHTING][RK_TYPE_NORMAL] = 2.0,
    [RK_TYPE_FIGHTING][RK_TYPE_GROUND] = 2.0,
    [RK_TYPE_FIGHTING][RK_TYPE_ICE] = 2.0,
    [RK_TYPE_FIGHTING][RK_TYPE_POISON] = 0.5,
    [RK_TYPE_FIGHTING][RK_TYPE_BUG] = 0.5,
    [RK_TYPE_FIGHTING][RK_TYPE_FLYING] = 0.5,
    [RK_TYPE_FIGHTING][RK_TYPE_FAIRY] = 0.5,
    [RK_TYPE_FIGHTING][RK_TYPE_GHOST] = 0.5,
    [RK_TYPE_FIGHTING][RK_TYPE_DARK] = 2.0,
    [RK_TYPE_FIGHTING][RK_TYPE_STEEL] = 2.0,
    [RK_TYPE_FIGHTING][RK_TYPE_PSYCHIC] = 0.5,

    [RK_TYPE_FLYING][RK_TYPE_GRASS] = 2.0,
    [RK_TYPE_FLYING][RK_TYPE_GROUND] = 0.5,
    [RK_TYPE_FLYING][RK_TYPE_DRAGON] = 0.5,
    [RK_TYPE_FLYING][RK_TYPE_ELECTRIC] = 0.5,
    [RK_TYPE_FLYING][RK_TYPE_BUG] = 2.0,
    [RK_TYPE_FLYING][RK_TYPE_FIGHTING] = 2.0,
    [RK_TYPE_FLYING][RK_TYPE_STEEL] = 0.5,

    [RK_TYPE_FAIRY][RK_TYPE_FIRE] = 0.5,
    [RK_TYPE_FAIRY][RK_TYPE_DRAGON] = 2.0,
    [RK_TYPE_FAIRY][RK_TYPE_POISON] = 0.5,
    [RK_TYPE_FAIRY][RK_TYPE_FIGHTING] = 2.0,
    [RK_TYPE_FAIRY][RK_TYPE_DARK] = 2.0,
    [RK_TYPE_FAIRY][RK_TYPE_STEEL] = 0.5,

    [RK_TYPE_GHOST][RK_TYPE_NORMAL] = 0.5,
    [RK_TYPE_GHOST][RK_TYPE_LIGHT] = 2.0,
    [RK_TYPE_GHOST][RK_TYPE_GHOST] = 2.0,
    [RK_TYPE_GHOST][RK_TYPE_DARK] = 0.5,
    [RK_TYPE_GHOST][RK_TYPE_PSYCHIC] = 2.0,

    [RK_TYPE_DARK][RK_TYPE_LIGHT] = 0.5,
    [RK_TYPE_DARK][RK_TYPE_POISON] = 2.0,
    [RK_TYPE_DARK][RK_TYPE_FIGHTING] = 0.5,
    [RK_TYPE_DARK][RK_TYPE_FAIRY] = 2.0,
    [RK_TYPE_DARK][RK_TYPE_GHOST] = 2.0,
    [RK_TYPE_DARK][RK_TYPE_DARK] = 0.5,

    [RK_TYPE_STEEL][RK_TYPE_FIRE] = 0.5,
    [RK_TYPE_STEEL][RK_TYPE_WATER] = 0.5,
    [RK_TYPE_STEEL][RK_TYPE_GROUND] = 2.0,
    [RK_TYPE_STEEL][RK_TYPE_ICE] = 2.0,
    [RK_TYPE_STEEL][RK_TYPE_ELECTRIC] = 0.5,
    [RK_TYPE_STEEL][RK_TYPE_FAIRY] = 2.0,
    [RK_TYPE_STEEL][RK_TYPE_STEEL] = 0.5,

    [RK_TYPE_PSYCHIC][RK_TYPE_LIGHT] = 0.5,
    [RK_TYPE_PSYCHIC][RK_TYPE_POISON] = 2.0,
    [RK_TYPE_PSYCHIC][RK_TYPE_FIGHTING] = 2.0,
    [RK_TYPE_PSYCHIC][RK_TYPE_STEEL] = 0.5,
    [RK_TYPE_PSYCHIC][RK_TYPE_PSYCHIC] = 0.5,
};

double rk_type_effectiveness(rk_type attack_type, rk_type defender_type) {
    if (attack_type < 0 || attack_type >= RK_TYPE_COUNT ||
        defender_type < 0 || defender_type >= RK_TYPE_COUNT) {
        return 1.0;
    }
    double value = TYPE_CHART[attack_type][defender_type];
    return value == 0.0 ? 1.0 : value;
}

int rk_calculate_damage(const rk_damage_input *input) {
    if (!input || input->power <= 0) {
        return 0;
    }

    double ability_level =
        (1.0 + input->attack_up + input->defense_down) /
        fmax(0.1, 1.0 + input->attack_down + input->defense_up);
    double attack = input->base_attack * ability_level;
    double defense = fmax(1.0, input->base_defense);

    double base = (attack / defense) * (double)input->power * 0.9;

    double effectiveness = rk_type_effectiveness(input->attack_type, input->defender_type);
    if (input->attacker_barrel || input->defender_barrel) {
        effectiveness = 1.0;
    }

    double stab = input->same_type_bonus ? 1.5 : 1.0;

    double weather_mult = 1.0;
    if (input->weather == RK_WEATHER_RAIN && input->attack_type == RK_TYPE_WATER) {
        weather_mult = 1.5;
    }

    int hits = input->hit_count;
    double power_multiplier = input->power_multiplier > 0.0 ? input->power_multiplier : 1.0;
    double damage = base * effectiveness * stab * weather_mult * (double)hits * power_multiplier;

    int result = (int)damage;
    return result < 1 ? 1 : result;
}
