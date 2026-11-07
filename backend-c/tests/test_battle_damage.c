#include <math.h>
#include <stdio.h>
#include <string.h>

#include "../src/integrations/battle_damage.h"

static int failures = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        if (!(cond)) {                                          \
            printf("FAIL: %s (line %d)\n", msg, __LINE__);       \
            failures++;                                         \
        }                                                       \
    } while (0)

#define CHECK_NEAR(a, b, eps, msg)                              \
    do {                                                        \
        double _a = (a);                                        \
        double _b = (b);                                        \
        if (fabs(_a - _b) > (eps)) {                            \
            printf("FAIL: %s (line %d): %.4f != %.4f\n",         \
                   msg, __LINE__, _a, _b);                      \
            failures++;                                         \
        }                                                       \
    } while (0)

static rk_damage_input base_input(void) {
    rk_damage_input in;
    memset(&in, 0, sizeof(in));
    in.category = RK_CATEGORY_PHYSICAL;
    in.power = 60;
    in.base_attack = 100.0;
    in.base_defense = 50.0;
    in.attack_type = RK_TYPE_NORMAL;
    in.defender_type = RK_TYPE_NORMAL;
    in.hit_count = 1;
    in.power_multiplier = 1.0;
    return in;
}

static void test_effectiveness(void) {
    CHECK_NEAR(rk_type_effectiveness(RK_TYPE_GRASS, RK_TYPE_WATER), 2.0, 1e-9, "草打水");
    CHECK_NEAR(rk_type_effectiveness(RK_TYPE_WATER, RK_TYPE_STEEL), 2.0, 1e-9, "水打钢");
    CHECK_NEAR(rk_type_effectiveness(RK_TYPE_FIRE, RK_TYPE_WATER), 0.5, 1e-9, "火打水");
    CHECK_NEAR(rk_type_effectiveness(RK_TYPE_LIGHT, RK_TYPE_DARK), 2.0, 1e-9, "光打暗");
    CHECK_NEAR(rk_type_effectiveness(RK_TYPE_GROUND, RK_TYPE_FLYING), 1.0, 1e-9, "地打飞");
    CHECK_NEAR(rk_type_effectiveness(RK_TYPE_NORMAL, RK_TYPE_GHOST), 0.5, 1e-9, "普打鬼");
    CHECK_NEAR(rk_type_effectiveness(RK_TYPE_COUNT, RK_TYPE_NORMAL), 1.0, 1e-9, "非法类型");
}

static void test_damage(void) {
    rk_damage_input in = base_input();
    CHECK(rk_calculate_damage(&in) == 108, "基础伤害 100/50*60*0.9");

    in.same_type_bonus = 1;
    CHECK(rk_calculate_damage(&in) == 162, "本系加成 1.5x");

    in = base_input();
    in.attack_up = 0.5;
    in.defense_up = 0.2;
    CHECK(rk_calculate_damage(&in) == 135, "攻防等级 1.25x");

    in = base_input();
    in.attack_type = RK_TYPE_WATER;
    in.weather = RK_WEATHER_RAIN;
    CHECK(rk_calculate_damage(&in) == 162, "雨天水属性 1.5x");

    in = base_input();
    in.attack_type = RK_TYPE_GRASS;
    in.defender_type = RK_TYPE_WATER;
    CHECK(rk_calculate_damage(&in) == 216, "克制 2x");

    in.attacker_barrel = 1;
    CHECK(rk_calculate_damage(&in) == 108, "木桶抹平克制");

    in = base_input();
    in.hit_count = 2;
    CHECK(rk_calculate_damage(&in) == 216, "多段伤害");

    in = base_input();
    in.power = 0;
    CHECK(rk_calculate_damage(&in) == 0, "威力为 0");

    in = base_input();
    in.base_defense = 0.0;
    CHECK(rk_calculate_damage(&in) == 5400, "防御下限按 1 处理");

    CHECK(rk_calculate_damage(NULL) == 0, "空输入");
}

int main(void) {
    test_effectiveness();
    test_damage();
    if (failures == 0) {
        printf("battle_damage: all tests passed\n");
        return 0;
    }
    printf("battle_damage: %d failure(s)\n", failures);
    return 1;
}
